from PumpSystem.pumpSystem import CustomValve,BetaSystem,NONBetaSystem,BartelsPump
from HeatingSystem.heatingSystem import TemperatureSystem
from Telemetry.Telemetry import ISSTelemetry,TelemetryDataSource,TeleDatatypes
from Bus.I2C import PythonWire
from Logger.Logger import Logger
from Logger.ErrorCounter import ErrorCounter
from ShiftRegister.shiftRegister import ShiftRegister
from GPIO.gpio import SingleGPIO
from Systemparameters.SystemData import SystemParameters
from IndependantSensors.MPU6050 import MPU6050
from IndependantSensors.RTC import RTC
from MEASystem.meaSystem import MeaSPI
from MicroscopeSystem.microscopeSystem import Microscope
from RestoreSystem.RestoreSystem import RestoreSystem
from DataMirrow.DataMirrow import DataMirrow
import time
import threading
import traceback

CELL_CHAMBER_1_4 = 0.11 # ml

SECOND = 1
MINUTE = 60 * SECOND    
HOUR = 60 * MINUTE
DAY = 24 * HOUR

BETA_DAY = 3 # DAY 4 (starting from 0)
STIMULATION_DAY = 14 # DAY 15 (starting from 0)

DEFAULT_ISS_NOT_RECEIVED_TIME = -1
MAX_LAUNCH_DAYS = 10

MEA_KHZ =  15
MEA_SECONDS = 30

MEA_SPEED = MeaSPI.getBaudRate(khz = MEA_KHZ)
MEA_SAMPLES = MeaSPI.getNumberOfSample(speed = MEA_SPEED, seconds=MEA_SECONDS)

# Variables to restore : time, iss_signal_received, pumped amount 
# Tasks: Storing Sensor Data, USB storing, schedule, restore

# Tasks:
# Detect Reboot throw file with first booting time
# Restore iss_signal_received, beta_released, missing_pumped_volume

class Experiment(TelemetryDataSource):
    def __init__(self):
        self.rtc = RTC() 
        self.rtc.setSystemTime() # I2C
        self.logger = Logger("Experiment Scheduler")
        self.sr = ShiftRegister(10,26,24) 
        self.ts = TemperatureSystem(8,41,42, 27,29,31,33,35,37, 16,18,22, self.sr) # SPI
        self.nbs = NONBetaSystem(11,13,15) 
        self.bs =  BetaSystem(32,36,38,28,7,12,40) # I2C
        self.sp = SystemParameters() 
        self.mpu = MPU6050() # I2C
        self.mea = MeaSPI(device=0, speed=MEA_SPEED) # SPI
        self.mea.setShiftRegister(self.sr) 
        self.scope = Microscope() # I2C + USB 
        self.iss = ISSTelemetry([self, self.ts, self.nbs, self.bs, self.sp, 
                                 self.mpu, self.rtc, self.scope, self.mea, 
                                 ErrorCounter()]) # I2C
        self.mirr = DataMirrow()

        # Setting System Time
        

        # System Variables
        self.iss_signal_received = False
        self.iss_signal_received_on = DEFAULT_ISS_NOT_RECEIVED_TIME
        self.relativExperimentTime = 0
        self.experimentStartTime = time.time()
        self.n_pump_cycles = 0
        self.meaToMic = {4 : 0, 5 : 1}#
        self.positionInSchedule = 0
        self.teleCounter = 0
        self.rot_state = [22, 72, 73, 76, 89, 91]
        self.normalMeas = [mea_no for mea_no in range(6) if mea_no not in self.meaToMic.keys()]

        #Restoring System
        self.rs = RestoreSystem(timestamp = self.experimentStartTime, iss_singal_received = self.iss_signal_received, 
                                iss_signal_recevied_on = self.iss_signal_received_on, n_pump_cycles = self.n_pump_cycles)


    def start(self):
        #Check for Power Outage
        if(self.rs.detectPowerOutage()):
            self.logger.logInfo("Power Outage Detected")
            data = self.rs.getRestoreData()
            self.experimentStartTime = data.getTimestamp()
            self.iss_signal_received = data.getIssSignalReceived()
            self.iss_signal_received_on = data.getIssSignalReceivedOn()
            self.n_pump_cycles = data.getNPumpCycles()
            self.restore()
        else:
            self.logger.logInfo("No power outage detected: Starting System")
            self.rs.createRestoreFile()
            self.run()

    def estimateSystemState(self, seconds):
        days = seconds / DAY
        pump_cycles = 0

        if(days < MAX_LAUNCH_DAYS):
                pump_cycles = days / 2 
                return (int(days), int(pump_cycles))
        else:
            if(self.iss_signal_received_on == DEFAULT_ISS_NOT_RECEIVED_TIME):
                self.setIssSignalReceived(True, MAX_LAUNCH_DAYS * DAY)
                pump_cycles = MAX_LAUNCH_DAYS / 2 
                pump_cycles += (int(days - MAX_LAUNCH_DAYS)) * 2 
                return (int(days - MAX_LAUNCH_DAYS), int(pump_cycles))  
            else:
                days_before = self.iss_signal_received_on / DAY
                days_after = days - days_before
                pump_cycles = int(days_before) / 2
                pump_cycles += int(days_after) * 2
                return (int(days_after), int(pump_cycles))


    def restore(self):
        self.logger.logInfo("Restoring System")
        days, estimated_pump_cycles = self.estimateSystemState(time.time() - self.experimentStartTime)
        pumping = CountedLoop(functions_to_call = [self.bs.mediumChange, self.nbs.mediumChange], parallel=True)

        self.logger.logInfo("Estimated days ({}) and pump_cycles ({})".format(days, estimated_pump_cycles))

        if(estimated_pump_cycles < self.n_pump_cycles):
            pump_cycles_behind = estimated_pump_cycles - self.n_pump_cycles   
            self.logger.logInfo("Pumping {}  pumping cycles to catch up on pumping".format(pump_cycles_behind))  
            pumping.countedRun(max_runs=pump_cycles_behind)

        # Set Beta
        if(self.iss_signal_received and BETA_DAY < days):
            self.logger.logInfo("Set Beta Released")
            self.bs.setBetaReleased(True)

        self.run(days)


    def run(self, sday = 0):
        if(not self.iss_signal_received):
            self.logger.logInfo("Running Pre Launch Software")
            self.preLaunchSoftware(sday)

            self.logger.logInfo("Running Launch Software")
            self.launchSoftware(sday)

        self.setIssSignalReceived(True)        

        self.logger.logInfo("Running Iss Software")
        self.issSoftware(sday)


    def preLaunchSoftware(self, sday):
        if(sday < 1):
            #self.preLaunchTests()
            heat_tele = TimedLoop(functions_to_call = [self.ts._updateLoop, self.iss.transmit], 
                                    on_exit = [self.ts.meaMeasurementShutOff],
                                    parallel = False, delay_between_calls = 0.01)
            heat_tele.timedRun(30 * MINUTE)
            self.positionInSchedule += 1

            self.measurementSequence()
            self.positionInSchedule += 1


    # 10 Days tops
    def launchSoftware(self, sday):
        pumping = CountedLoop(functions_to_call = [self.bs.mediumChange, self.nbs.mediumChange], parallel=True)
        heating = StartStopLoop(functions_to_call = [self.ts._updateLoop], on_exit = [self.ts.meaMeasurementShutOff],
                              parallel = False, delay_between_calls = 0.01)

        heating.start()
        self.rtc.setSystemTime()
        startTime = time.time()

        self.positionInSchedule = 500
        # 2 Day loop
        for two_days in range(int(sday/2) , 5):
            self.logger.logInfo("Day {} Pumping".format(two_days * 2))
            pumping.countedRun(max_runs = 1)
            
            # Runs 2 Days
            while(startTime + 2 * DAY > time.time()):
                self.logger.logInfo("Check for ISS Signal")
                if(self.iss.checkForStartSignal()):
                    self.logger.logInfo("\n\n")
                    self.logger.logInfo("==============================")
                    self.logger.logInfo("Start signal really recieved <>")
                    heating.stop()
                    self.setIssSignalReceived(True)
                    return True
                self.iss.transmit()
                time.sleep(5)

            self.rtc.setSystemTime()
            self.relativExperimentTime += 2
        
        heating.stop()
    
    # 20 Days
    def issSoftware(self, sday):
        heating = StartStopLoop(functions_to_call = [self.ts._updateLoop], 
                                on_exit = [self.ts.meaMeasurementShutOff],
                                parallel = False, delay_between_calls = 0.01)
        heat_tele = TimedLoop(functions_to_call = [self.ts._updateLoop, self.iss.transmit], 
                                on_exit = [self.ts.meaMeasurementShutOff],
                                parallel = False, delay_between_calls = 0.01)
        copy = StartStopLoop(functions_to_call = [self.mirr.backupFile], 
                                parallel = False, delay_between_calls = 0.01)
        pumping = CountedLoop(functions_to_call = [self.bs.mediumChange, self.nbs.mediumChange], parallel=True)
        stimulate = False

        self.relativExperimentTime += sday

        for day in range(sday, 50):
            self.logger.logInfo("Day {} of iss software".format(day))

            # Activate stimulated mea readout at day 15
            if(day >= STIMULATION_DAY):
                self.logger.logInfo("Cell Stimulation activated")
                stimulate = True
            
            # Life Support
            self.positionInSchedule = 1000
            self.logger.logInfo("Life Support")
            heat_tele.timedRun(time_limit = 3 * HOUR)

            # Measurement Sequence 1.1
            self.positionInSchedule = 1100
            self.logger.logInfo("Measurement Sequence 1.1")
            self.measurementSequence(stimulate=stimulate)

            if(day == BETA_DAY):
                self.logger.logInfo("BETA DAY: Beta release")
                self.bs.mediumChange(betaRelease = True, waitForFinish = False)
                pumping.setFunctionsToCall([self.nbs.mediumChange])

            # Buffer (Heating, Telemetry)
            self.positionInSchedule = 1200
            self.logger.logInfo("Buffer (Heating, Telemetry)")
            heat_tele.timedRun(time_limit = 23 * MINUTE)

            # Pump Cycle 1
            self.positionInSchedule = 1300
            self.logger.logInfo("Pump Cycle 1")
            heating.start()
            pumping.countedRun(max_runs = 1) 
            heating.stop()

            if(day == BETA_DAY):
                pumping.setFunctionsToCall([self.bs.mediumChange, self.nbs.mediumChange])

            # Buffer (Heating, Telemetry)
            self.positionInSchedule = 1400
            self.logger.logInfo("Buffer (Heating, Telemetry)")
            heat_tele.timedRun(time_limit = 30 * MINUTE)

            # Measurement Sequence 1.2
            self.positionInSchedule = 1400
            self.logger.logInfo("Measurement Sequence 1.2")
            self.measurementSequence(stimulate=stimulate)

            # Buffer (Heating, Telemetry)
            self.positionInSchedule = 1500
            self.logger.logInfo("Buffer (Heating, Telemetry)")
            heat_tele.timedRun(time_limit = 1 * HOUR)
            copy.start()
            heat_tele.timedRun(time_limit = 3 * HOUR)
            copy.stop()
            heat_tele.timedRun(time_limit = 1 * HOUR)

            # Intermediate Measurement Sequence
            self.positionInSchedule = 1600
            self.logger.logInfo("Intermediate Measurement Sequence")
            self.measurementSequence(stimulate=stimulate)

            # Buffer (Heating, Telemetry)
            self.positionInSchedule = 1700
            self.logger.logInfo("Buffer (Heating, Telemetry)")
            heat_tele.timedRun(time_limit = 40 * MINUTE)
            copy.start()
            heat_tele.timedRun(time_limit = 3 * HOUR)
            copy.stop()
            heat_tele.timedRun(time_limit = 1 * HOUR)

            # Measurement Sequence 2.1
            self.positionInSchedule = 2000
            self.logger.logInfo("Measurement Sequence 2.1")
            self.measurementSequence(stimulate=stimulate)

            # Buffer (Heating, Telemetry)
            self.positionInSchedule = 2100
            self.logger.logInfo("Buffer (Heating, Telemetry)")
            heat_tele.timedRun(time_limit = 23 * MINUTE)

            # Pump Cycle 2
            self.positionInSchedule = 2200
            self.logger.logInfo("Pump Cycle 2")
            heating.start()
            pumping.countedRun(max_runs = 1)
            heating.stop()

            # Buffer (Heating, Telemetry)
            self.positionInSchedule = 2300
            self.logger.logInfo("Buffer (Heating, Telemetry)")
            heat_tele.timedRun(time_limit = 30 * MINUTE)

            # Measurement Sequence 2.2
            self.positionInSchedule = 2400
            self.logger.logInfo("Measurement Sequence 2.2")
            self.measurementSequence(stimulate=stimulate)

            # Buffer (Heating, Telemetry)
            self.positionInSchedule = 2500
            self.logger.logInfo("Buffer (Heating, Telemetry)")
            heat_tele.timedRun(time_limit = 6 * HOUR + 30 * MINUTE)  

            self.positionInSchedule = 2600
            self.logger.logInfo("Setting System Time")
            self.rtc.setSystemTime()
            self.relativExperimentTime += 1


    def measurementSequence(self, stimulate = False):
        sensor_readout = TimedLoop(functions_to_call = [self.mpu.read, self.iss.transmit], parallel=False)
        heating = TimedLoop(functions_to_call=[self.ts._updateLoop, self.iss.transmit], 
                              on_exit = [self.ts.meaMeasurementShutOff], 
                              parallel=True , delay_between_calls=0.01)

        # make sure heatpads are off
        self.logger.logInfo("Shutting Off Heating for Measurements")
        self.ts.meaMeasurementShutOff()

        for mea_no in self.meaToMic.keys():
            
            # Buffer (Telemetry, MPU6050)
            self.logger.logInfo("Buffer (Telemetry, MPU6050)")
            sensor_readout.timedRun(time_limit = 30 * SECOND)

            # MEA Readout mea_no
            self.logger.logInfo("MEAReadout mea_no = {}".format(mea_no))
            self.mea.readout(mea_no = mea_no, n_samples=MEA_SAMPLES, stimulation=stimulate) # 4
            
            # Buffer (Telemetry, MPU6050)
            self.logger.logInfo("Buffer (Telemetry, MPU6050)")
            sensor_readout.timedRun(time_limit = 30 * SECOND)
            
            # Microscope Readout mea_no
            self.logger.logInfo("Microscopes Readout micNum = {}".format(self.meaToMic[mea_no]))
            for _ in range(2):
                self.scope.take_exposure(micNumber = self.meaToMic[mea_no], frames = 10 , fps = 10, ledlevel = 230) # to 100 frames
                time.sleep(0.01)
            
            # Buffer (Telemetry, MPU6050)
            self.logger.logInfo("Buffer (Telemetry, MPU6050)")
            sensor_readout.timedRun(time_limit = 30 * SECOND)

            # Intermediate Heating
            self.logger.logInfo("Intermediate Heating")
            heating.timedRun(time_limit = 3 * MINUTE)
        
        for mea_no in self.normalMeas:

            # Buffer (Telemetry, MPU6050)
            self.logger.logInfo("Buffer (Telemetry, MPU6050)")
            sensor_readout.timedRun(time_limit = 30 * SECOND)
            
            # MEA Readout mea_no
            self.logger.logInfo("MEAReadout mea_no = {}".format(mea_no))
            self.mea.readout(mea_no = mea_no, n_samples=MEA_SAMPLES, stimulation=stimulate)

            # Buffer (Telemetry, MPU6050)
            self.logger.logInfo("Buffer (Telemetry, MPU6050)")
            sensor_readout.timedRun(time_limit = 30 * SECOND)

            # Intermediate Heating
            self.logger.logInfo("Intermediate Heating")
            heating.timedRun(time_limit = 3 * MINUTE)
        
        sensor_readout.stop()
        heating.stop()

    def setIssSignalReceived(self, received : bool, startTime = time.time()):
        if(self.iss_signal_received != received and received == True):
            self.rs.setIssSignalReceived(iss_signal_received=received)
            self.rs.setIssSignalReceivedOn(iss_signal_received_on=startTime)
            self.iss_signal_received = True
            self.iss_signal_received_on = startTime
            self.relativExperimentTime = int(self.iss_signal_received_on / DAY) * 1_000

    def preLaunchTests(self):
        heating = StartStopLoop(functions_to_call = [self.ts._updateLoop], on_exit = [self.ts.meaMeasurementShutOff],
            parallel = False, delay_between_calls = 0.01)


        logger = Logger("#")
        logger.logInfo("\n\n")
        logger.logInfo("====Temperature Test====")
        self.ts.selfTest()

        heating.start()

        logger.logInfo("\n\n")
        logger.logInfo("====Beta System Test====")
        self.bs.selfTest()

        logger.logInfo("\n\n")
        logger.logInfo("====Non Beta Test====")
        self.nbs.selfTest()

        logger.logInfo("\n\n")
        logger.logInfo("====MPU Test====")
        self.mpu.selfTest()

        logger.logInfo("\n\n")
        logger.logInfo("====RTC Test====")
        self.rtc.selfTest()

        heating.stop()

        logger.logInfo("\n\n")
        logger.logInfo("====MEA Test====")
        self.mea.selfTest()

        heating.start()

        logger.logInfo("\n\n")
        logger.logInfo("====ISS Test====")
        self.iss.selfTest()

        logger.logInfo("\n\n")
        logger.logInfo("====Microscopes Test====")
        self.scope.selfTest()

        heating.stop()

    
    def getTeleData(self):
        self.teleCounter += 1
        return {"system_status" : (int(self.iss_signal_received) * 1_000_000 + self.relativExperimentTime, TeleDatatypes.INT),
                "pb_status" : (self.positionInSchedule + self.rot_state[self.teleCounter % len(self.rot_state)] , TeleDatatypes.INT)}

    
    def thermalStableTest(self):
        while True:
            self.ts._updateLoop()
    
    def telemetryTest(self):
        self.iss.startTransmitting()

        time.sleep(60)

        self.iss.stopTransmitting()
    
    def meaTest(self):
        #self.mea.readout(mea_no = 2, n_samples=20_000_000, save = True)
        self.mea.readout(mea_no = 2, n_samples=MEA_SAMPLES, stimulation = True , save = True)


class TimedLoop():
    def __init__(self, functions_to_call, on_exit = [], parallel = True, delay_between_calls = 0.01):
        self.functions_to_call = functions_to_call
        self.on_exit = on_exit
        self.parallel = parallel
        self.delay_between_calls = delay_between_calls
        self.active = False
        self.logger = Logger("TimedLoop")
    
    def timedRun(self, time_limit):
        try:
            self.active = True
            if(self.parallel):
                for func in self.functions_to_call:
                    thread = threading.Thread(target=self._updateLoop,args=([func], time_limit))
                    thread.start()
            else:
                thread = threading.Thread(target=self._updateLoop,args=(self.functions_to_call,time_limit))
                thread.start()
            
            start_time = time.time()
            while(start_time + time_limit > time.time()):
                time.sleep(1)
            self.active = False

            if(len(self.on_exit) > 0):
                time.sleep(3)
                for func in self.on_exit:
                    func()

        except Exception as e:
            self.logger.logErr("Error during execution of loop", e)
    
    def _updateLoop(self, functions, time_limit):
        
        start_time = time.time()
        while(self.active and start_time + time_limit > time.time()):
            for func in functions:
                func()
            time.sleep(self.delay_between_calls)

    def stop(self):
        self.active = False

    def setFunctionsToCall(self, functions_to_call):
        self.functions_to_call = functions_to_call

class CountedLoop():
    def __init__(self, functions_to_call, on_exit = [], parallel = True, delay_between_calls = 0.01, loop_limit = int(1 * HOUR)):
        self.functions_to_call = functions_to_call
        self.on_exit = on_exit
        self.parallel = parallel
        self.delay_between_calls = delay_between_calls
        self.active = False
        self.loop_limit = loop_limit
        self.logger = Logger("CountedLoop")
    
    def countedRun(self, max_runs):
        try:
            if(self.loop_limit < max_runs):
                self.logger.logErr("max runs exceeds loop limit {} {}".format(max_runs, self.loop_limit))
                max_runs = self.loop_limit

            self.active = True

            if(self.parallel):
                actives = [True for _ in self.functions_to_call]
                for n,func in enumerate(self.functions_to_call):
                    thread = threading.Thread(target=self._updateLoop, args=([func], max_runs, n, actives))
                    thread.start()
                
                for _ in range(self.loop_limit):
                    if(actives == [False for _ in self.functions_to_call]):
                        break
                    time.sleep(1)
            else:
                for _ in range(max_runs):
                    for func in self.functions_to_call:
                        func()
            
            if(len(self.on_exit) > 0):
                time.sleep(3)
                for func in self.on_exit:
                    func()

            self.active = False
                    
        except Exception as e:
            self.logger.logErr("Error executing loop", e)

    
    def _updateLoop(self, functions, max_runs, n, actives):
        for _ in range(max_runs):
            if(not self.active):
                break
            for func in functions:
                if(not self.active):
                    break
                func()
            time.sleep(self.delay_between_calls)
        actives[n] = False
    
    def stop(self):
        self.active = False

    def setFunctionsToCall(self, functions_to_call):
        self.functions_to_call = functions_to_call
        
class StartStopLoop():
    def __init__(self, functions_to_call, on_exit = [], parallel = True, delay_between_calls = 0.01, loop_limit = int(10 * HOUR * (1/0.01))):
        self.functions_to_call = functions_to_call
        self.on_exit = on_exit
        self.parallel = parallel
        self.delay_between_calls = delay_between_calls
        self.active = False
        self.loop_limit = loop_limit
        self.logger = Logger("TimedLoop")

    
    def start(self):
        self.active = True
        if(self.parallel):
            for func in self.functions_to_call:
                thread = threading.Thread(target=self._updateLoop, args=([[func]]))
                thread.start()
        else:
            thread = threading.Thread(target=self._updateLoop, args=([self.functions_to_call]))
            thread.start()

    def _updateLoop(self, functions):
        for _ in range(self.loop_limit):
            if(not self.active):
                break
            for func in functions:
                if(not self.active):
                    break
                func()
            time.sleep(self.delay_between_calls)
    
    def stop(self):
        self.active = False

        if(len(self.on_exit) > 0):
            time.sleep(3)
            for func in self.on_exit:
                func()
    
    def setFunctionsToCall(self, functions_to_call):
        self.functions_to_call = functions_to_call
        