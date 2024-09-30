import csv
import time
import threading
import abc
import traceback

WRITE = True
PRINT = False
LOG_DIRECTORY = "/home/warr/"

# Normal Time + seperate Error File

class LoggedSensorObject(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'getLogData') and 
                callable(subclass.getLogData) or 
                NotImplemented)
    
    def getLogData(self):
        """ returns dict with name and log data"""
        raise NotImplementedError

class Logger():
    _error_counter = 0
    _error_file = ""

    def __init__(self, name : str, LOG = True):
        self.name = name
        self.LOG = LOG
        self.mainFile = LOG_DIRECTORY + "mcsp_" + name.replace(" ","") + "_" + str(int(time.time() * 100)) + ".log"
        self.files = {}

        if(Logger._error_file == ""):
            Logger._error_file = LOG_DIRECTORY + "errors_" + str(int(time.time() * 100)) + ".log"
 
    def logErr(self, msg:str, e:Exception = None):
        threading.Thread(target=self._logErr,args=(msg,e)).start()

    def logInfo(self, msg:str, e:Exception = None):
        threading.Thread(target=self._logInfo,args=(msg,e)).start()

    def logSensorData(self, sensorName:str, data:dict):
        threading.Thread(target=self._logSensorData,args=(sensorName, data)).start()


    def _logErr(self, msg:str, e:Exception = None):
        try:
            if(PRINT):
                str_msg = ""
                if(e == None):
                    str_msg = "[-] <{t}> {name} : {msg}".format(t=time.strftime("%d-%m-%Y %H:%M:%S"), name = self.name, msg = msg)
                else:
                    str_msg = "[-] <{t}> {name} : {msg} - {emsg}".format(t=time.strftime("%d-%m-%Y %H:%M:%S"), name = self.name, msg = msg,emsg = e)
                if(PRINT):
                    print(str_msg)
            if(WRITE):
                self._writeTextLogFile(str_msg)
                self._writeTextLogFile(str_msg, file = Logger._error_file)
            Logger._error_counter += 1

                    
        except Exception as e:
            pass

    def _logInfo(self, msg:str, e:Exception = None):
        try:
            str_msg = ""
            if(e == None):
                str_msg = "[i] <{t}> {name} : {msg}".format(t=time.strftime("%d-%m-%Y %H:%M:%S"), name = self.name, msg = msg)
            else:
                str_msg = "[i] <{t}> {name} : {msg} - {emsg}".format(t=time.strftime("%d-%m-%Y %H:%M:%S"), name = self.name, msg = msg,emsg = e)
            if(self.LOG and PRINT):
                print(str_msg)
            if(WRITE):
                self._writeTextLogFile(str_msg)

        except Exception as e:
            pass
    
    def _logSensorData(self, sensorName:str, data:dict):
        if(not sensorName in self.files.keys()):
            self.files[sensorName] = LOG_DIRECTORY + sensorName + str(int(time.time())) + ".log"
        if(WRITE):
            self._writeDataCSV(data,self.files[sensorName])       

    def _writeDataCSV(self, data:dict ,LOG_FILE:str):
        if(WRITE):
            try:
                dataList = [time.time()]
                for k in data.keys():
                    dataList.append(k)
                    dataList.append(data[k])

                with open(LOG_FILE, mode='a') as csv_file:
                    writer = csv.writer(csv_file, delimiter=',')
                    writer.writerow(dataList)
            except Exception as e:
                self.logErr("Error writing Data to CSV File (data: {}, file: {})".format(data, LOG_FILE),e)
        else:
            self.logErr("writeDataCSV is called, but WRITE is not activated ")
    
    def _writeTextLogFile(self,string:str, file = None):
        if(file == None):
            file = self.mainFile
        if(WRITE):
            try:
                with open(file, mode='a') as csv_file:
                    writer = csv.writer(csv_file, delimiter=',')
                    writer.writerow([time.time(), string])
            except Exception as e:
                print("[-] Error writing to text log file {} - {}".format(string,e))
        else:
            self.logErr("writeTextLogFile is called, but WRITE is not activated ")
    
    def getErrorCount():
        return Logger._error_counter
    



#database ...
    
