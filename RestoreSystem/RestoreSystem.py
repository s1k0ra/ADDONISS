import os
import pickle
import time
from Logger.Logger import Logger

# Restore File
RESTORE_FILE = "/home/warr/restore.config"
BACKUP_RESTORE_FILE = "/home/warr/restore_backup.config"

class RestoreData():
    def __init__(self, timestamp, iss_signal_received, iss_signal_received_on , n_pump_cycles):
        self.timestamp = timestamp
        self.iss_signal_received = iss_signal_received
        self.iss_signal_received_on = iss_signal_received_on
        self.n_pump_cycles = n_pump_cycles

    def getTimestamp(self):
        return self.timestamp

    def getIssSignalReceived(self):
        return self.iss_signal_received
    
    def getIssSignalReceivedOn(self):
        return self.iss_signal_received_on

    def getNPumpCycles(self):
        return self.n_pump_cycles

    def setIssSignalReceived(self, iss_signal_received):
        self.iss_signal_received = iss_signal_received

    def setIssSignalReceivedOn(self, iss_signal_received_on):
        self.iss_signal_received_on = iss_signal_received_on

    def setNPumpCycles(self, n_pump_cycles):
        self.n_pump_cycles = n_pump_cycles
    

class RestoreSystem():
    def __init__(self, timestamp : int, iss_singal_received : bool, iss_signal_recevied_on : int , n_pump_cycles : int):
        self.logger = Logger("RestoreSystem")
        self.rd = RestoreData(timestamp = timestamp,
                            iss_signal_received = iss_singal_received,
                             iss_signal_received_on= iss_signal_recevied_on, 
                             n_pump_cycles= n_pump_cycles)
    
    def createRestoreFile(self):
        if not (os.path.isfile(RESTORE_FILE)):
            self.logger.logInfo("Creatting Restore File")
        else:
            self.logger.logErr("Warning: restore file already exits and will be overwritten")
        self._saveRestoreInfosRedundant()

    def detectPowerOutage(self, restore_file = RESTORE_FILE):
        if(os.path.isfile(restore_file)):
            try:
                with open(restore_file, 'rb') as file:
                    self.rd = pickle.load(file)
                self.logger.logInfo("System Data restored: {} {} {} {}".format(self.rd.getTimestamp(),
                                                                                self.rd.getIssSignalReceived(),
                                                                                self.rd.getIssSignalReceivedOn(),
                                                                                self.rd.getNPumpCycles()))
                return True
            except Exception as e:
                self.logger.logErr("Error detecting power outage", e)
        else:
            return False

        if(restore_file != BACKUP_RESTORE_FILE):
            return self.detectPowerOutage(restore_file=BACKUP_RESTORE_FILE)
        else:
            return False

    def _saveRestoreInfos(self, restore_file):
        try:
            with open(restore_file, 'wb') as file:
                pickle.dump(self.rd, file, pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            self.logger.logErr("Unable to save restore infos", e)

    def _saveRestoreInfosRedundant(self):
        self._saveRestoreInfos(RESTORE_FILE)
        time.sleep(0.01)
        self._saveRestoreInfos(BACKUP_RESTORE_FILE)

    def setIssSignalReceived(self, iss_signal_received):
        self.rd.setIssSignalReceived(iss_signal_received)
        self._saveRestoreInfosRedundant()
    
    def setIssSignalReceivedOn(self, iss_signal_received_on):
        self.rd.setIssSignalReceivedOn(iss_signal_received_on)
        self._saveRestoreInfosRedundant()

    def setNPumpCycles(self, n_pump_cycles):
        self.rd.setNPumpCycles(n_pump_cycles)
        self._saveRestoreInfosRedundant()
    
    def getRestoreData(self):
        return self.rd

