import RPi.GPIO as GPIO
from time import sleep
from Logger.Logger import Logger
from GPIO.gpio import GPIOMapping
import threading
from GPIO.gpio import SingleGPIO
from Bus.I2C import PythonWire
from Telemetry.Telemetry import TelemetryDataSource,TeleDatatypes

#Pump Constants
PUMP_PXX_TIME = 7.519 #seconds
PUMP_PXX_BETA_TIME = 8.203 #seconds
PUMP_Pu_TIME = 1320 #seconds
PU_PUMPING_DELAY = 60 #seconds

PUMPING_LOG_RESOLUTION = 0.5 #seconds

#Bartels constants
I2C_HIGHDRIVER_ADRESS = 0x78
I2C_DEVICEID = 0x00
I2C_POWERMODE = 0x01
I2C_FREQUENCY = 0x02
I2C_SHAPE = 0x03
I2C_BOOST = 0x04
I2C_PVOLTAGE = 0x06
I2C_P1VOLTAGE = 0x06
I2C_P2VOLTAGE = 0x07
I2C_P3VOLTAGE = 0x08
I2C_P4VOLTAGE = 0x09
I2C_UPDATEVOLTAGE = 0x0A
I2C_AUDIO = 0x05

GPIO.setmode(GPIO.BCM)

class Pump(SingleGPIO):
    def __init__(self, PIN: int, SPEED = 1, LOG = True, CONVERT = True):
        super().__init__(PIN, CONVERT)
        self.logger = Logger("Pumpe {pin}".format(pin = PIN))
        self.pumpingLogger = PumpVolumeLogger(PIN)
        self.SPEED = SPEED
        
    def on(self):
        self.logger.logInfo("Pumpe on")
        self._set(True)
        self.pumpingLogger.start()
        
    def off(self):
        self.logger.logInfo("Pumpe off")
        self._set(False)
        self.pumpingLogger.stop()

    def pump(self, duration):
        self.logger.logInfo("pumping for {t} seconds".format(t=duration))
        self.on()
        sleep(duration * self.SPEED)
        self.off()

    def test():
        logger = Logger("Pump TEST")
        logger.logInfo("Setting up pump")
        pump = Pump(11)
        pump.setup()

        logger.logInfo("Turnin pump on")
        pump.on()
        sleep(5)

        logger.logInfo("Turning pump off")
        pump.off()
        pump.close()


class Valve(SingleGPIO):
    def __init__(self, PIN : int, LOG = True):
        super().__init__(PIN,LOG)
        self.logger = Logger("Valve {pin}".format(pin = PIN),LOG)
    
    def open(self):
        self.logger.logInfo("Valve open")
        self._set(True)

    def close(self):#
        self.logger.logInfo("Valve close")
        self._set(False)

    def test():
        logger = Logger("Valve TEST")
        logger.logInfo("Setting up Valve")
        valve = Valve(11)

        logger.logInfo("Open Valve")
        valve.open()
        sleep(10)

        logger.logInfo("Close Valve")
        valve.close()
        valve.close()

class CustomValve():
    def __init__(self, PWM_PIN : int, POWER_PIN : int, startPoint = 9, endPoint = 5, frequency = 50, LOG = True, CONVERT = True):
        self.PWM_PIN = GPIOMapping.convertTOBCM(PWM_PIN) if CONVERT else PWM_PIN
        self.startPoint = startPoint
        self.endPoint = endPoint
        self.freqeuncy = frequency 
        self.pwm = None
        self.power = SingleGPIO(POWER_PIN, CONVERT=CONVERT)
        self.state = False
        self.logger = Logger("Custom Valve",LOG)

    def setup(self):
        self.logger.logInfo("Setting up servo and power pin")
        self.power.setup()
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.PWM_PIN, GPIO.OUT)
            self.pwm = GPIO.PWM(self.PWM_PIN, self.freqeuncy)
            self.pwm.start(self.startPoint)
        except Exception as e:
            self.logger.logErr("Error setting up valve",e)


    def open(self):
        self.logger.logInfo("Opening valve")
        self.power._set(True)
        sleep(2)

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.PWM_PIN, GPIO.OUT)
            self.pwm.ChangeDutyCycle(self.endPoint)
            self.state = True
        except Exception as e:
            self.logger.logErr("Error opening valve", e)

        sleep(2)
        self.power._set(False)
    
    def close(self):
        GPIO.setmode(GPIO.BCM)
        try:
            GPIO.setup(self.PWM_PIN, GPIO.OUT)
            self.pwm.stop()
            self.power.close()
        except Exception as e:
            self.logger.logErr("Error freeing pins",e)
        
    def test():
        logger = Logger ("Custom Valve TEST")
        logger.logInfo("Setting up Valve")
        valve = CustomValve(12,11)
        valve.setup()
        sleep(3)
        
        logger.logInfo("Open Valve")
        valve.open()
        sleep(3)

        logger.logInfo("Freeing valve")
        valve.close()

        logger.logInfo("End")

class BartelsPump():
    def __init__(self):
        self.bPumpState = [0, 0, 0, 0]  # boolean
        self.nPumpVoltageByte = [0x00, 0x00, 0x00, 0x00]  # uint_8t
        self.nFrequencyByte = 0x40  # uint8_t
        self.Wire = PythonWire(I2C_HIGHDRIVER_ADRESS) 
        self.logger = Logger("Bartels Pump")
        self.pumpingLogger = PumpVolumeLogger("Bartels Pump")
        self.setup()

    def setup(self):
        self.Wire.begin()
        self.Highdriver_init()
        self.off()
        #self.close()

    def Highdriver_init(self):
        self.Wire.beginTransmission(I2C_HIGHDRIVER_ADRESS)
        # Start Register 0x01
        self.Wire.write(I2C_POWERMODE)
        # Register 0x01 = 0x01 (enable)
        self.Wire.write(0x01)
        # Register 0x02 = 0x40 (100Hz)
        self.Wire.write(self.nFrequencyByte)
        # Register 0x03 = 0x00 (sine wave)
        self.Wire.write(0x00)
        # Register 0x04 = 0x00 (800KHz)
        self.Wire.write(0x00)
        # Register 0x05 = 0x00 (audio off)
        self.Wire.write(0x00)
        # Register 0x06 = Amplitude1
        self.Wire.write(0x00)
        # Register 0x07 = Amplitude2
        self.Wire.write(0x00)
        # Register 0x08 = Amplitude3
        self.Wire.write(0x00)
        # Register 0x09 = Amplitude4
        self.Wire.write(0x00)
        # Register 0x0A = 0x01 (update)
        self.Wire.write(0x01)
        self.Wire.endTransmission()

        self.bPumpState[3] = 0
        self.nPumpVoltageByte[3] = 0x1F

    def Highdriver_setvoltage(self,_voltage):
        self.Wire.beginTransmission(I2C_HIGHDRIVER_ADRESS)
        self.Wire.write(I2C_PVOLTAGE)
        self.Wire.write(0)
        self.Wire.write(0)
        self.Wire.write(0)
        self.Wire.write((self.nPumpVoltageByte[3] if self.bPumpState[3] else 0))
        # update new driver Entries
        self.Wire.write(0x01)
        self.Wire.endTransmission()

    def on(self):
        self.logger.logInfo("Turning On Bartels Pump")

        self.bPumpState[3] = 1
        self.Highdriver_setvoltage(250)
    
    def off(self):
        self.logger.logInfo("Turning Off Bartels Pump")

        self.bPumpState[3] = 0
        self.Highdriver_setvoltage(0)   
    
    def close(self):
        self.Wire.close()

    def test():
        bp = BartelsPump()
        
        bp.on()
        
        sleep(5) 
        
        bp.off() 

class PumpVolumeLogger():
    def __init__(self, name):
        self.name = name
        self.logger = Logger("Pump Amount Logger {}".format(self.name))
        self.pumpedAmount = 0
        self.state = False
    
    def start(self):
        self.state = True
        threading.Thread(target=self._logPumpedVolume).start()

    def stop(self):
        self.state = False
    
    def _logPumpedVolume(self):
        self.logger.logInfo("Pump Amount Logger started")
        self.logger.logSensorData("pumped_amount{}_".format(self.name), {"timesteps" : -1})

        while(self.state):
            sleep(PUMPING_LOG_RESOLUTION)
            self.pumpedAmount += PUMPING_LOG_RESOLUTION
            self.logger.logSensorData("pumped_amount{}_".format(self.name), {"timesteps" : self.pumpedAmount})

class BetaSystem(TelemetryDataSource):
    def __init__(self,  PUMP_P1B_PIN : int, PUMP_P2B_PIN : int, PUMP_P3B_PIN : int,
                        PUMP_Pu_PIN : int, VALVE_NL_PIN : int , VALVE_V_PWM_PIN :int,
                        VALVE_V_PIN :int ,PUMP_P1B_SPEED = 1, PUMP_P2B_SPEED = 1,
                        PUMP_P3B_SPEED = 1, PUMP_Pu_SPEED = 1, NORMAL_PUMPING_TIME = PUMP_PXX_TIME,
                        BETA_PUMPING_TIME = PUMP_PXX_BETA_TIME, PU_PUMPING_TIME = PUMP_Pu_TIME,
                        PUMPING_DELAY = 1, PU_PUMPING_DELAY = PU_PUMPING_DELAY, LOG = True):        
        
        #pumps
        self.PUMP_P1B = Pump(PUMP_P1B_PIN, PUMP_P1B_SPEED)
        self.PUMP_P2B = Pump(PUMP_P2B_PIN, PUMP_P2B_SPEED)
        self.PUMP_P3B = Pump(PUMP_P3B_PIN, PUMP_P3B_SPEED)
        self.PUMP_Pu = Pump(PUMP_Pu_PIN, PUMP_Pu_SPEED)
        self.PUMP_BAR = BartelsPump()

        #valves
        self.VALVE_NL = Valve(VALVE_NL_PIN)
        self.VALVE_V = CustomValve(VALVE_V_PWM_PIN,VALVE_V_PIN)

        #states
        self.betaReleased = False
        self.ongoingMediumChange = False

        #pumping times
        self.NORMAL_PUMPING_TIME = NORMAL_PUMPING_TIME
        self.BETA_PUMPING_TIME = BETA_PUMPING_TIME
        self.PU_PUMPING_TIME = PU_PUMPING_TIME
        self.PUMPING_DELAY = PUMPING_DELAY
        self.PU_PUMPING_DELAY = PU_PUMPING_DELAY

        self.timeOfMediumChangeWithoutBeta =    3 * (self.NORMAL_PUMPING_TIME + self.PUMPING_DELAY)
        self.timeOfMediumChangeWithBeta =       self.timeOfMediumChangeWithoutBeta                  + 2 * self.PUMPING_DELAY
        self.timeOfBetaRelease =                3 * (self.BETA_PUMPING_TIME + self.PUMPING_DELAY)   + (self.PU_PUMPING_TIME + self.PUMPING_DELAY)

        self.maxTimeOfMediumChange = max(self.timeOfBetaRelease, self.timeOfMediumChangeWithBeta, self.timeOfMediumChangeWithoutBeta)

        #Logger
        self.logger = Logger("BetaSystem", LOG)

        #setup GPIOs
        self.setup()
        self.thread = None
        self.mediumChanges = 0

    def setup(self):
        self.logger.logInfo("Setting up Beta System")
        try:
            self.PUMP_P1B.setup()
            self.PUMP_P2B.setup()
            self.PUMP_P3B.setup()
            self.PUMP_Pu.setup()
            self.PUMP_BAR.setup()
            self.VALVE_NL.setup()
            self.VALVE_V.setup()
        except Exception as e:
            self.logger.logErr("Error setting up beta system")

    def _mediumChangeWithoutBeta(self, ongoing = True): 
        self.logger.logInfo("Medium Change Without Beta")
        self.ongoingMediumChange = True if ongoing else self.ongoingMediumChange

        try:

            self.VALVE_NL.open()

            self.PUMP_P1B.pump(self.NORMAL_PUMPING_TIME)
            sleep(self.PUMPING_DELAY)

            self.PUMP_P2B.pump(self.NORMAL_PUMPING_TIME)
            sleep(self.PUMPING_DELAY)

            self.PUMP_P3B.pump(self.NORMAL_PUMPING_TIME)
            sleep(self.PUMPING_DELAY)

            self.VALVE_NL.close()

        except Exception as e:
            self.logger.logInfo("Error while medium change without beta",e)
        
        self.ongoingMediumChange = False if ongoing else self.ongoingMediumChange

    def _mediumChangeWithBeta(self):
        self.logger.logInfo("Medium Change With Beta")
        self.ongoingMediumChange = True

        try:
            self.PUMP_BAR.on()
            sleep(self.PUMPING_DELAY)
            self._mediumChangeWithoutBeta(ongoing = False)
            sleep(self.PUMPING_DELAY)
            self.PUMP_BAR.off()
            
        except Exception as e:
            self.logger.logErr("Error while medium change with beta",e)
            #self._mediumChangeWithBeta() 
        self.ongoingMediumChange = False

    def _distributeBeta(self):
        self.logger.logInfo("Distributing Beta")
        self.ongoingMediumChange = True

        try:
            if(not self.betaReleased):
                self.VALVE_V.open()
                self.PUMP_BAR.on()

                self.PUMP_Pu.pump(self.PU_PUMPING_TIME)
                sleep(self.PU_PUMPING_DELAY)

                self.PUMP_P1B.pump(self.BETA_PUMPING_TIME)
                sleep(self.PUMPING_DELAY)

                self.PUMP_P2B.pump(self.BETA_PUMPING_TIME) 
                sleep(self.PUMPING_DELAY)

                self.PUMP_P3B.pump(self.BETA_PUMPING_TIME) 
                sleep(self.PUMPING_DELAY)

                self.PUMP_BAR.off()

                self.betaReleased = True
        except Exception as e:
            self.logger.logErr("Error while distributing Beta",e)
        
        self.ongoingMediumChange = False

    def estimateMediumChangeDuration(self, betaRelease = False):
        if(betaRelease):
            return self.timeOfBetaRelease
        elif(not self.betaReleased):
            return self.timeOfMediumChangeWithoutBeta
        else:
            return self.timeOfMediumChangeWithBeta

    def mediumChange(self, betaRelease = False, waitForFinish = True):
            if(waitForFinish):
                self._mediumChange(betaRelease=betaRelease)
            else:
                self.thread = threading.Thread(target=self._mediumChange, args=([betaRelease]))
                self.thread.start()

    def _mediumChange(self, betaRelease = False):
        self.logger.logInfo("Medium Change Number {}".format(self.mediumChanges))

        if(self.ongoingMediumChange):
            self.logger.logErr("Other medium change already running")
            for x in range(int(self.maxTimeOfMediumChange) + 1):
                if(self.ongoingMediumChange == False):
                    break
                sleep(1)

        if(betaRelease): 
            try:
                self._distributeBeta()
            except Exception as e:
                self.logger.logErr("Error distributing beta with thread",e)

        elif (not self.betaReleased):
            try:
                self._mediumChangeWithoutBeta()
            except Exception as e:
                self.logger.logErr("Error changing medium before beta with thread",e)
        else:
            try:
                self._mediumChangeWithBeta()
            except Exception as e:
                self.logger.logErr("Error changing medium after beta with thread",e)

        self.mediumChanges += 1


    def off(self):
        self.logger.logInfo("Shutting off hardware")
        try:
            self.PUMP_P1B.off()
            self.PUMP_P2B.off()
            self.PUMP_P3B.off()
            self.PUMP_Pu.off()
            self.PUMP_BAR.off()

            self.PUMP_BAR.close()
            self.VALVE_NL.close()
            self.VALVE_V.close()    
        except Exception as e:
            self.logger.logErr("Error shutting off hardware",e)    

    def setBetaReleased(self, betaReleased : bool):
        if(betaReleased == True):
            self.betaReleased = betaReleased

    def getTeleData(self):
        return {"p4_volume" : (self.PUMP_P1B.pumpingLogger.pumpedAmount,TeleDatatypes.INT),
                "p5_volume" : (self.PUMP_P2B.pumpingLogger.pumpedAmount,TeleDatatypes.INT),
                "p6_volume" : (self.PUMP_P3B.pumpingLogger.pumpedAmount,TeleDatatypes.INT),
                "p_abeta_volume": (self.PUMP_Pu.pumpingLogger.pumpedAmount,TeleDatatypes.INT),

                "p4_status" : (self.PUMP_P1B.state,TeleDatatypes.INT),
                "p5_status" : (self.PUMP_P2B.state,TeleDatatypes.INT),
                "p6_status" : (self.PUMP_P3B.state,TeleDatatypes.INT),
                "p_abeta_status" : (self.PUMP_Pu.state,TeleDatatypes.INT),

                "valve1" : (self.VALVE_NL.state,TeleDatatypes.INT),
                "valve2" : (self.VALVE_V.state,TeleDatatypes.INT), 

                "abeta_status" : (self.VALVE_V.state,TeleDatatypes.INT),

                "p_trap_status" : (self.PUMP_BAR.bPumpState[3],TeleDatatypes.INT),
                "p_trap_amp": (self.PUMP_BAR.nPumpVoltageByte[3],TeleDatatypes.FLOAT),
                "p_trap_freq" : (self.PUMP_BAR.nFrequencyByte,TeleDatatypes.FLOAT)}
    
    def selfTest(self):
        logger = Logger("BetaSystem TEST")

        logger.logInfo("Test Pump P1B")
        self.PUMP_P1B.pump(5)
        logger.logInfo("Test Pump P2B")
        self.PUMP_P2B.pump(5)
        logger.logInfo("Test Pump P3B")
        self.PUMP_P3B.pump(5)
        logger.logInfo("Test Pump Pu")
        self.PUMP_Pu.pump(5)

        sleep(5)

        # logger.logInfo("Test Valve NL")
        # self.VALVE_NL.open()
        # sleep(5)
        # self.VALVE_NL.close()

        # logger.logInfo("Test Custom Valve ")
        # self.VALVE_V.open()

        logger.logInfo("Test Bartels Pump")
        self.PUMP_BAR.on()
        sleep(5)
        self.PUMP_BAR.off()

        logger.logInfo("End")        


    def test():
        logger = Logger("BetaSystem TEST")
        logger.logInfo("Setting up Beta System")
        #pwm = 12
        #pin 28 error !!!
        betaSystem = BetaSystem(32,36,38,37,7,12,40)

        logger.logInfo("Medium Change before beta release")
        betaSystem.mediumChange()
        betaSystem.thread.join()

        logger.logInfo("Releasing Beta")
        #betaSystem.distributeBeta()
        betaSystem.mediumChanges = 7
        betaSystem.mediumChange()
        betaSystem.thread.join()

        logger.logInfo("Medium Change after beta release")
        betaSystem.mediumChange()
        betaSystem.thread.join()

        betaSystem.off() 
        logger.logInfo("End")
    

class NONBetaSystem(TelemetryDataSource):
    def __init__(self, PUMP_P1A_PIN : int, PUMP_P2A_PIN : int, PUMP_P3A_PIN : int, PUMP_P1A_SPEED = 1, PUMP_P2A_SPEED = 1, PUMP_P3A_SPEED = 1, NORMAL_PUMPING_TIME = PUMP_PXX_TIME, PUMPING_DELAY = 1, LOG = True):
        
        #pumps
        self.PUMP_P1A =  Pump(PUMP_P1A_PIN,PUMP_P1A_SPEED)
        self.PUMP_P2A =  Pump(PUMP_P2A_PIN,PUMP_P2A_SPEED)
        self.PUMP_P3A =  Pump(PUMP_P3A_PIN,PUMP_P3A_SPEED)

        #pumping time
        self.NORMAL_PUMPING_TIME = NORMAL_PUMPING_TIME
        self.PUMPING_DELAY = PUMPING_DELAY

        #states
        self.ongoingMediumChange = False

        #setup
        self.logger = Logger("NONBetaSystem",LOG)
        self.thread = None
        self.setup()

    def _mediumChange(self):
        self.logger.logInfo("Medium Change")

        if(self.ongoingMediumChange):
            self.logger.logErr("Other medium change already running")

        self.ongoingMediumChange = True

        try:

            self.PUMP_P1A.pump(self.NORMAL_PUMPING_TIME)
            sleep(self.PUMPING_DELAY)

            self.PUMP_P2A.pump(self.NORMAL_PUMPING_TIME)
            sleep(self.PUMPING_DELAY)

            self.PUMP_P3A.pump(self.NORMAL_PUMPING_TIME)
            sleep(self.PUMPING_DELAY)

        except Exception as e:
            self.logger.logErr("Error while medium change",e)
            self.ongoingMediumChange = False
        
        self.ongoingMediumChange = False

    def estimateMediumChangeDuration(self):
        return 3 * (self.NORMAL_PUMPING_TIME + self.PUMPING_DELAY)

    def mediumChange(self):
        try:
            self.thread = threading.Thread(target=self._mediumChange)
            self.thread.start()
        except Exception as e:
            self.logger.logErr("Error changing medium with thread")

    def setup(self):
        self.logger.logInfo("Setting up Hardware")
        try:
            self.PUMP_P1A.setup()
            self.PUMP_P2A.setup()
            self.PUMP_P3A.setup()
        except Exception as e:
            self.logger.logErr("Error while setting up hardware",e)

    def off(self):
        self.logger.logInfo("Shutting off hardware")
        try:
            self.PUMP_P1A.off()
            self.PUMP_P2A.off()
            self.PUMP_P3A.off()
        except Exception as e:
            self.logger.logErr("Error shutting off hardware",e)

    def getTeleData(self):
        return {"p1_volume" : (self.PUMP_P1A.pumpingLogger.pumpedAmount,TeleDatatypes.INT),
                "p2_volume" : (self.PUMP_P2A.pumpingLogger.pumpedAmount,TeleDatatypes.INT),
                "p3_volume" : (self.PUMP_P3A.pumpingLogger.pumpedAmount,TeleDatatypes.INT),
                "p1_status" : (self.PUMP_P1A.state,TeleDatatypes.INT),
                "p2_status" : (self.PUMP_P2A.state,TeleDatatypes.INT),
                "p3_status" : (self.PUMP_P3A.state,TeleDatatypes.INT)}

    def selfTest(self):
        #allow logging on all devices
        logger = Logger("NonBetaSystem TEST")

        logger.logInfo("Testing Pump P1A")
        self.PUMP_P1A.pump(5)
        logger.logInfo("Testing Pump P2A")
        self.PUMP_P2A.pump(5)
        logger.logInfo("Testing Pump P3A")
        self.PUMP_P3A.pump(5)

        logger.logInfo("End")
      

    def test():
        logger = Logger("NonBetaSystem TEST")
        logger.logInfo("Setting up Non Beta System")
        nonBetaSystem = NONBetaSystem(11,13,15)

        logger.logInfo("Medium Change")
        nonBetaSystem.mediumChange()
        nonBetaSystem.thread.join()

        nonBetaSystem.off()
        logger.logInfo("End")
