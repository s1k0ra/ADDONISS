import time
import RPi.GPIO as GPIO
import board
import adafruit_max31865
import threading
from Logger.Logger import Logger
from simple_pid import PID
from ShiftRegister.shiftRegister import ShiftRegister
from GPIO.gpio import GPIOMapping
from GPIO.digitalInOut import DigitalInOut
from Telemetry.Telemetry import TelemetryDataSource,TeleDatatypes
from GPIO.gpio import SingleGPIO

MIN_TEMP = -10 # C°
MAX_TEMP = 100 # C°

EMERGENCY_TEMP_UPPER = 39 # C°
EMERGENCY_TEMP_LOWER = 35 # C°
EMERGENCY_HEATPAD_OUTPUT = 0 # %

MAX_TEMP_DIVERGENCE = 2 # C°

CRITICAL_NUMBER_VALID_TEMPERATURES = 2

MIN_OUTPUT = 0 # %
MAX_OUTPUT = 100 # %

MIN_SIMPLE_CONTROLLER_OUTPUT = 0 #%
MAX_SIMPLE_CONTROLLER_OUTPUT = 65 #%

TEMP_SETPOINT = 36.8 #C°

class DataGrouping():
    def __init__(self,h1_1:int,h1_2:int,h1_3:int, h2_1:int, h2_2:int, h2_3:int, h3_1:int, h3_2:int, h3_3:int, h4_1:int, h4_2:int, h4_3:int, h5_1:int, h5_2:int, h5_3:int, h6_1:int, h6_2:int, h6_3:int):
        self.logger = Logger("DataGrouping")
        self.heatpads = [[h1_1,h1_2,h1_3],
                         [h2_1,h2_2,h2_3],
                         [h3_1,h3_2,h3_3],
                         [h4_1,h4_2,h4_3],
                         [h5_1,h5_2,h5_3],
                         [h6_1,h6_2,h6_3]]

        
    def getValidInputs(self, pos : int):
        inputs = []

        if (pos >= 0 and pos <= 2):
            for row in self.heatpads:
                inputs.append(row[pos])
        else:
            self.logger.logErr("Argument Error : pos = {} out of valid range(0,2)".format(pos))

        return inputs

    def getSortedTemperatures(self, board1_temps, board2_temps, board3_temps):
        h_temps = []
        for x in range(len(self.heatpads)):
            temp1 = board1_temps[self.heatpads[x][0]]
            temp2 = board2_temps[self.heatpads[x][1]]
            temp3 = board3_temps[self.heatpads[x][2]]
            h_temps.append([temp1,temp2,temp3])
        return h_temps
    
    def getFilteredTemperatures(self,board1_temps, board2_temps, board3_temps):
        h_temps = self.getSortedTemperatures(board1_temps,board2_temps,board3_temps)
        ts = []
        for temps in h_temps:
            ts.append(DataGrouping._filter(temps[0],temps[1],temps[2]))
        return ts


    def _filter(t1,t2,t3):
        temps = []

        if(t1 > MIN_TEMP and t1 < MAX_TEMP):
            temps.append(t1)
        if(t2 > MIN_TEMP and t2 < MAX_TEMP):
            temps.append(t2) 
        if(t3 > MIN_TEMP and t3 < MAX_TEMP):
            temps.append(t3)

        if(len(temps) >= CRITICAL_NUMBER_VALID_TEMPERATURES):
            
            if(len(temps) == 1):
                return sum(temps)/len(temps)

            if(len(temps) >= 2):
                t1_t2 = abs(temps[0]-temps[1])

                if(len(temps) == 2):
                    if(t1_t2 <= MAX_TEMP_DIVERGENCE):
                        return sum(temps)/len(temps)

                if(len(temps) == 3):
                    t1_t3 = abs(temps[0]-temps[2])
                    t2_t3 = abs(temps[1]-temps[2])

                    if(t1_t2 <= MAX_TEMP_DIVERGENCE and min(t1_t3, t2_t3) > MAX_TEMP_DIVERGENCE):
                        return sum([temps[0], temps[1]]) / 2
                    
                    if(t1_t3 <= MAX_TEMP_DIVERGENCE and min(t1_t2, t2_t3) > MAX_TEMP_DIVERGENCE):
                        return sum([temps[0], temps[2]]) / 2
                    
                    if(t2_t3 <= MAX_TEMP_DIVERGENCE and min(t1_t2, t1_t3) > MAX_TEMP_DIVERGENCE):
                        return sum([temps[1], temps[2]]) / 2
                    
                    if(t1_t2 <= MAX_TEMP_DIVERGENCE and min(t1_t3, t2_t3) <= MAX_TEMP_DIVERGENCE):
                        return sum(temps) / len(temps)

        return -242
        
        
class PIDController:
    def __init__(self, p = 20, i = 0.9 ,d = 10, setpoint = TEMP_SETPOINT, lowerLimit = MIN_OUTPUT,upperLimit = MAX_OUTPUT):

        # Controller
        self.controller  = PID(p, i, d, setpoint=setpoint)
        self.controller.output_limits = (lowerLimit, upperLimit)

        # Backupcontroller
        self.backup = SimpleController(setpoint)

        # Logger
        self.logger = Logger("PID Controller")
        self.logger.logInfo("Created controller : (p:{}, i:{}, d:{}, setpoint:{}, lowerLimit: {}, upperLimit: {}".format(p,i,d,setpoint,lowerLimit,upperLimit))

    def getOutput(self, input : float):
        try:
            if(input > EMERGENCY_TEMP_UPPER or input < EMERGENCY_TEMP_LOWER):
                self.logger.logErr("PIDController not capable to keep temperature in emergency bounds (current temperature: {})".format(input))
                return self.backup.getOutput(input)
            
            output = self.controller(input)
            self.logger.logInfo("Calculated output (input: {}, output: {})".format(input,output))
            return output
        
        except Exception as e:
            self.logger.logErr("Error calculating new output (input : {})".format(input), e)
            return self.backup.getOutput(input)

class SimpleController():
    def __init__(self, setpoint = TEMP_SETPOINT):
        self.setpoint = setpoint
        self.logger = Logger("Simple Controller")
    
    def getOutput(self, t):
        output = EMERGENCY_HEATPAD_OUTPUT

        if(self.setpoint > t and t > MIN_TEMP):
            output = MAX_SIMPLE_CONTROLLER_OUTPUT
        elif(self.setpoint < t and t < MAX_TEMP):
            output = MIN_SIMPLE_CONTROLLER_OUTPUT
        else:
            self.logger.logErr("No valid temperature readout (temp :{})".format(t))

        self.logger.logInfo("Caculated output to {}".format(output))
        return output

class Multiplexer():
    def __init__(self,SP0_PIN:int, SP1_PIN:int, SP2_PIN:int, LOG = True, CONVERT = True):
        self.logger = Logger("Multiplexer_p1{p1}_p2{p2}_p3{p3}".format(p1 = SP0_PIN, p2 = SP1_PIN, p3 = SP2_PIN),LOG)
        self.SP0_PIN = SingleGPIO(SP0_PIN,CONVERT=CONVERT)
        self.SP1_PIN = SingleGPIO(SP1_PIN,CONVERT=CONVERT)
        self.SP2_PIN = SingleGPIO(SP2_PIN,CONVERT=CONVERT)

    def setup(self):
        self.logger.logInfo("Setting up Multiplexer")
        self.SP0_PIN.setup()
        self.SP1_PIN.setup()
        self.SP2_PIN.setup()

    def setMultiplexer(self, heatpadNumber : int):
        if(heatpadNumber > 7 or heatpadNumber < 0):
            self.logger.logErr("Error settting Multiplexer Pins input={hN}".format(hN = heatpadNumber))
        else:
            state0 = (heatpadNumber >> 2) % 2
            state1 = (heatpadNumber >> 1) % 2
            state2 = heatpadNumber  % 2

            self._setPins(state0,state1,state2)

    def _setPins(self, STATE_PIN0:int, STATE_PIN1:int, STATE_PIN2:int):
        self.logger.logInfo("setting pins ({p1}, {p2}, {p3})".format(p1 = STATE_PIN0, p2=STATE_PIN1, p3 = STATE_PIN2))
        
        self.SP0_PIN._set(STATE_PIN0)
        self.SP1_PIN._set(STATE_PIN1)
        self.SP2_PIN._set(STATE_PIN2)

        time.sleep(0.1)

    def close(self):
        self.logger.logInfo("Finishing up with the Multiplexer")

        self.SP0_PIN.close()
        self.SP1_PIN.close()
        self.SP2_PIN.close()
    
    def getState(self):
        return self.SP2_PIN.state * 100 + self.SP1_PIN.state * 10 + self.SP0_PIN.state

# callibration values, threads, update check ?
class TemperatureReadoutBoard():
    
    def __init__(self, SPI_SELECTOR_PIN:int, shtReg:ShiftRegister, validInputs:list, CValue0 = 0.0 ,CValue1 = 0.0 , CValue2 = 0.0, CValue3 = 0.0, CValue4 = 0.0, CValue5 = 0.0, LOG = True, CONVERT = True):
        
        # Logger
        self.logger = Logger("Temperature Readout Board {pin}".format(pin = SPI_SELECTOR_PIN),LOG)

        # Readout SPI PINS
        self.SELECTOR_PIN = SPI_SELECTOR_PIN # SPI_SELECTOR_PIN

        # Sensor object
        self.connected = False
        self.sensor = None
        self.cs = None

        # Shift Register
        self.shtReg = shtReg

        # Calibration Offsets of temperature sensors
        self.CValues = [CValue0,CValue1,CValue2,CValue3,CValue4,CValue5,0,0]
        self.validInputs = validInputs

        # Heatpad temperatures
        self.heatpadTemps = [-242] * 8

    def connect(self):
        try:
            # Connect Board    def validate(): # lower < upper
            spi = board.SPI()
            self.cs = DigitalInOut(self.SELECTOR_PIN, shtReg=self.shtReg)
            self.sensor = adafruit_max31865.MAX31865(spi, self.cs)  

            time.sleep(0.1)

            self.connected = True

            self.logger.logInfo("Hardware succesful connected")

        except Exception as e:
            self.logger.logErr("Error connecting to Hardware",e)

    def disconnect(self):
        try:
            self.sensor = None
            self.connected = False

            self.logger.logInfo("Succesfully disconnected Hardware")

        except Exception as e:
            self.logger.logErr("Error disconnecting Hardware", e)
            
    
    def getTemperature(self, heatpadNumber):
        if(self.connected):

            if(heatpadNumber < 6 and heatpadNumber >= 0):

                if(self.heatpadTemps[heatpadNumber] != None):

                    if(self.heatpadTemps[heatpadNumber] > MIN_TEMP and self.heatpadTemps[heatpadNumber] < MAX_TEMP):

                        return self.heatpadTemps[heatpadNumber]
                    else:
                        self.logger.logErr("Temperature for Heatpad {hN} out of range".format(heatpadNumber))
                else:
                    self.logger.logErr("No Temperature for Heatpad {hN} was read yet")
            else:
                self.logger.logErr("No temperature for Heatpad Number {hN} available ".format(heatpadNumber))
        else:
            self.logger.logErr("No tempeature readable, since hardware is not connected/initialized")
        
        return None

    def getTemperatures(self):
        return self.heatpadTemps
        

    def measure(self,heatpadNumber:int):
        temp = 988
        try:
            if(heatpadNumber in self.validInputs):
                temp = self.sensor.temperature + self.CValues[heatpadNumber]
            
        except Exception as e:
            self.logger.logErr("Error measuring temperature of heatpad {num}".format(num = heatpadNumber),e)
            return -242
        
        self.logger.logInfo("Measured Heatpad {num} Temperature {temp} C°".format(num = heatpadNumber, temp = temp))
        self.heatpadTemps[heatpadNumber] = temp + self.CValues[heatpadNumber]
        return temp + self.CValues[heatpadNumber]
        

    def test(self):
        self.connect()
        for heatpadNumber in range(6):
            self.logger.logInfo("Heatpad {hN} Temperature: {temp}".format(hN = heatpadNumber, temp = self.getTemperature(heatpadNumber)))    
        self.disconnect()

class Heatpad():
    def __init__(self,CONTROL_PIN, LOG = True, CONVERT = True):
        self.CONTROL_PIN = GPIOMapping.convertTOBCM(CONTROL_PIN) if CONVERT else CONTROL_PIN
        self.controlValue = 0 
        self.lastUpdate = 0
        self.logger = Logger("Heatpad with pin {p}".format(p = CONTROL_PIN),LOG)
        self.output = None

    def connect(self):
        try:

            self.logger.logInfo("Setting up heatpad control_pin {pin} ".format(pin = self.CONTROL_PIN))  
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.CONTROL_PIN, GPIO.OUT)
            self.output = GPIO.PWM(self.CONTROL_PIN, 100)
            self.output.start(self.controlValue)
        except Exception as e:
            self.logger.logErr("Setting up heatpad control_pin {pin} ".format(pin = self.CONTROL_PIN),e)     
    
    def set(self, output):
        try:
            self.logger.logInfo("Setting heatpad {pin} to output of {out}".format(pin = self.CONTROL_PIN,out = output))
            self.controlValue = output
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.CONTROL_PIN, GPIO.OUT)
            self.output.ChangeDutyCycle(self.controlValue)
            
        except Exception as e:
            self.logger.logErr("Error setting heatpad {pin} to output of {out}".format(pin = self.CONTROL_PIN,out = output))

    def off(self):
        self.logger.logInfo("Shutting of heatpad")
        self.set(0.0)

class TemperatureSystem(TelemetryDataSource):
    def __init__(self, CS1_PIN : int, CS2_PIN : int, CS3_PIN : int, H1_PIN: int, H2_PIN: int, H3_PIN: int, H4_PIN : int, H5_PIN : int, H6_PIN : int, MULT1_PIN : int, MULT2_PIN : int, MULT3_PIN : int, shtReg : ShiftRegister, SETPOINT = TEMP_SETPOINT  , LOG = True):
        self.logger = Logger("Temperatue System",LOG)

        # Multiplexer Mapping
        self.tempMapping = DataGrouping(6,3,6, 0,0,0, 4,2,4, 2,1,2, 1,4,1, 5,6,5)

        self.logger.logInfo("Setup Temperature Boards")
        # Temperature Readout Boards
        trb0 = TemperatureReadoutBoard(CS1_PIN, None, self.tempMapping.getValidInputs(0))
        trb1 = TemperatureReadoutBoard(CS2_PIN, shtReg, self.tempMapping.getValidInputs(1))
        trb2 = TemperatureReadoutBoard(CS3_PIN, shtReg, self.tempMapping.getValidInputs(2))

        self.logger.logInfo("Setup Heatpads")
        # Heatpads
        hp0 = Heatpad(H1_PIN)
        hp1 = Heatpad(H2_PIN)
        hp2 = Heatpad(H3_PIN)
        hp3 = Heatpad(H4_PIN)
        hp4 = Heatpad(H5_PIN)
        hp5 = Heatpad(H6_PIN)

        self.logger.logInfo("Setup Multiplexer")
        # Multiplexer
        self.multiplexer = Multiplexer(MULT1_PIN, MULT2_PIN, MULT3_PIN)

        # System variables
        self.temperatureReadoutBoards = [trb0,trb1,trb2]
        self.heatpads = [hp0,hp1,hp2,hp3,hp4,hp5]
        self.pidCs = [PIDController(setpoint=SETPOINT) for heatpad in range(6)]
        self.SETPOINT = SETPOINT
        self.reading = False
        self.thread = None

        self.setup()

    def setup(self):
        self.logger.logInfo("Connecting Hardware")

        self.reading = False

        for readoutBoard in self.temperatureReadoutBoards:
            readoutBoard.connect()
        
        for heatpad in self.heatpads:
            heatpad.connect()

        self.logger.logInfo("Starting measurement loop")

    def disconnect(self):
        time.sleep(1)

        self.reading = False

        for readoutBoard in self.temperatureReadoutBoards:
            readoutBoard.disconnect()
        
        for heatpad in self.heatpads:
            heatpad.off()

        self.multiplexer.close()

    def readout(self):
        self.reading = True

        for heatpad in range(7):
            self.multiplexer.setMultiplexer(heatpad)

            for readoutBoard in self.temperatureReadoutBoards:

                temp = readoutBoard.measure(heatpad)

                self.logger.logInfo("Heatpad {num} : temperature {t}°".format(num = heatpad ,t = temp))
                self.logger.logSensorData("heatpad_raw_{}".format(heatpad), {"temperature_raw" : temp}) 
                
        self.reading = False

    def updateLoop(self):
        try:
            if(not self.reading):
                self.thread = threading.Thread(target=self._updateLoop)
                self.thread.start()

        except Exception as e:
            self.logger.logErr("Error measuring temperatures in thread")

    def _updateLoop(self):
        self.logger.logInfo("Measurement Loop")   
        
        self.readout()
        
        board0 = self.temperatureReadoutBoards[0].getTemperatures()
        board1 = self.temperatureReadoutBoards[1].getTemperatures()
        board2 = self.temperatureReadoutBoards[2].getTemperatures()

        temperatures = self.tempMapping.getFilteredTemperatures(board0,board1,board2)
        for i,t in enumerate(temperatures):
            out = self.pidCs[i].getOutput(t)
            self.heatpads[i].set(out)
            self.logger.logInfo("Heatpad {num} : temperature {t}° : output {o}% ".format(num = i ,t = t, o = out))
            self.logger.logSensorData("heatpad{}".format(i),{"temperature":t, "output":out})

    def getTemperatures(self):
        return  self.temperatureReadoutBoards[0].getTemperatures() + self.temperatureReadoutBoards[1].getTemperatures() + self.temperatureReadoutBoards[2].getTemperatures()

    def getSortedTemperatures(self):
        board0 = self.temperatureReadoutBoards[0].getTemperatures()
        board1 = self.temperatureReadoutBoards[1].getTemperatures()
        board2 = self.temperatureReadoutBoards[2].getTemperatures()

        return self.tempMapping.getSortedTemperatures(board0,board1,board2)
    
    def meaMeasurementShutOff(self):
        for heatpad in self.heatpads:
            heatpad.off()
    
    def getTeleData(self):
        temps =  [temp for temperatures in self.getSortedTemperatures() for temp in temperatures]
        multi = self.multiplexer.getState()
        heatpads = [h.controlValue for h in self.heatpads]

        return {"tmp1_1" : (temps[0],TeleDatatypes.FLOAT),
                "tmp1_2" : (temps[1],TeleDatatypes.FLOAT),
                "tmp1_3" : (temps[2],TeleDatatypes.FLOAT),
                "tmp2_1" : (temps[3],TeleDatatypes.FLOAT),
                "tmp2_2" : (temps[4],TeleDatatypes.FLOAT),
                "tmp2_3" : (temps[5],TeleDatatypes.FLOAT),
                "tmp3_1" : (temps[6],TeleDatatypes.FLOAT),
                "tmp3_2" : (temps[7],TeleDatatypes.FLOAT),
                "tmp3_3" : (temps[8],TeleDatatypes.FLOAT),
                "tmp4_1" : (temps[9],TeleDatatypes.FLOAT),
                "tmp4_2" : (temps[10],TeleDatatypes.FLOAT),
                "tmp4_3" : (temps[11],TeleDatatypes.FLOAT),
                "tmp5_1" : (temps[12],TeleDatatypes.FLOAT),
                "tmp5_2" : (temps[13],TeleDatatypes.FLOAT),
                "tmp5_3" : (temps[14],TeleDatatypes.FLOAT),
                "tmp6_1" : (temps[15],TeleDatatypes.FLOAT),
                "tmp6_2" : (temps[16],TeleDatatypes.FLOAT),
                "tmp6_3" : (temps[17],TeleDatatypes.FLOAT),
                "heatpad_1" : (heatpads[0],TeleDatatypes.INT),
                "heatpad_2" : (heatpads[1],TeleDatatypes.INT),
                "heatpad_3" : (heatpads[2],TeleDatatypes.INT),
                "heatpad_4" : (heatpads[3],TeleDatatypes.INT),
                "heatpad_5" : (heatpads[4],TeleDatatypes.INT),
                "heatpad_6" : (heatpads[5],TeleDatatypes.INT),
                "multiplexer" : (multi,TeleDatatypes.INT)}

    def selfTest(self):
        logger = Logger("Temerature System TEST")
        logger.logInfo("Start Readout Test")

        self.readout()
        logger.logInfo(str(self.getSortedTemperatures()))

        logger.logInfo("End Readout Test")

    def test():
        logger = Logger("Temperature System TEST")
        logger.logInfo("setup system ")
        
        shtReg = ShiftRegister(10,26,24)

        ts = TemperatureSystem(8,41,42, 27,29,31,33,35,37, 16,18,22, shtReg)

        logger.logInfo("start System")
        for x in range(1):
            ts.readout()
            # ts.updateLoop()
            # ts.thread.join()
            print("")
            logger.logInfo("==========================================\n")

        logger.logInfo("stop system")
        ts.disconnect()

