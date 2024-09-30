import abc
from enum import Enum
from Bus.I2C import PythonWire
import time
from Logger.Logger import Logger
import threading

START_STRING = "INITIATE_EXPERIMENT"

class TelemetryDataSource(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'getTeleData') and 
                callable(subclass.getTeleData) or 
                NotImplemented) 
    
    def getTeleData(self):
        """ returns dict with specified telemetry names and according data"""
        raise NotImplementedError

class TeleDatatypes(Enum):
    INT = 0
    FLOAT = 1

    def toDataTypeString(self, name : str, data):
        if(self.value == TeleDatatypes.INT.value):
            return self._intToByteDatum(name,data)

        elif(self.value == TeleDatatypes.FLOAT.value):
            return self._floatToByteDatum(name,data)

        else:
            logger = Logger("Enum")
            logger.logErr("Unknown Data Type can't be converted")
            return ""

    def _floatToByteDatum(self, name : str, data : float , digitsAfter = 2):
        return ('"{0}":{1:1.' + str(digitsAfter) + 'f}').format(str(name), float(data))  
    
    def _intToByteDatum(self,name : str, data : int):
        return  '"{0}":{1}'.format(str(name), int(data))


class PackageQueue():
    def __init__(self):
        self.logger = Logger("PackageQueue")
        self.queue = []

    def add(self, package):
        self.queue.append(package)
    
    def pop(self):
        if(len(self.queue) > 0):
            ele = self.queue[0]
            self.queue = self.queue[1:]
            return ele
        else:
            self.logger.logErr("Trying to pop from a empty queue")
    
    def length(self):
        return len(self.queue)
        

class ISSTelemetry(PythonWire):
    def __init__(self, systems : 'list[TelemetryDataSource]' , address=42, transmissionDelay = 5.5 , maxBytesForTransmission = 200, protocolBytes = 2):
        super().__init__(address, maxBytesForTransmission)
        super().begin()
        self.logger = Logger("ISSTelemetry")
        self.lastTransmission = 0
        self.transmissionDelay = transmissionDelay
        self.transmitting = False
        self.receiving = False
        self.queue = PackageQueue()
        self.systems = systems
        self.experimentStarted = False
        self.maxBytesForString = maxBytesForTransmission - protocolBytes
    
    def createString(self, data_dict : 'dict[str,int]', type_dict : 'dict[str,TeleDatatypes]', maxLength, startString=""):
        try:
            strings = [startString]
            currentPos = 0

            if(len(startString) > maxLength):
                self.logger.logErr("Error creating string from dict of values: start string={} bigger maxLength={}".format(startString, maxLength))

            for k in data_dict.keys():
                dat = data_dict[k]
                typ = type_dict[k]

                newPart = typ.toDataTypeString(k, dat)
                
                if(len(newPart) > maxLength):
                    self.logger.logErr("Maxlength to small for strings")
                    return []

                if(len(strings[currentPos]) + len(newPart) + 1 < maxLength):
                    strings[currentPos] += newPart + ","

                else:
                    if (strings[currentPos][-1] != "\n"):
                        strings[currentPos] =  strings[currentPos][:-1] + "\n"
                    currentPos += 1
                    strings.append(newPart + ",")

            return strings

        except IndexError as e:
            self.logger.logErr("Error creating string for dict : {}".format(data_dict),e)
            return []
        

    def sendCurrentStates(self, dicts : 'list[TelemetryDataSource]'):

        strings = []
        startString = ""

        try:

            for count, d in enumerate(dicts):
                data_dict = {}
                type_dict = {}

                for k in d.keys():
                    data_dict[k] = d[k][0]
                    type_dict[k] = d[k][1]

                newStrings = self.createString(data_dict,type_dict,self.maxBytesForString,startString=startString)
                strings += newStrings
                if(count != len(dicts) -1):
                    if(len(strings[len(strings) - 1]) < self.maxBytesForString):
                        startString = strings[-1]
                        strings = strings[:-1]
                    else:
                        startString = ""

            if(strings[-1][-1] != '\n'):
                strings[-1] = strings[-1][:-1] + '\n'

            for string in strings:
                self.queue.add(string)

        except IndexError as e:
            self.logger.logErr("Error creating Telemetry String",e)

    def writeString(self, string : str):
        self.beginTransmission()
        
        # protocol for microship
        self.write(1)
        self.write(len(string))

        if (len(self.buffer) + len(string) <= self.maxBytesForWrite):
            for d in string.encode('utf-8'):
                self.write(d)
        else:
            self.logger.logErr("Buffer Overflow when trying to send string over i2c: str = {}, len = {}".format(string, len(string)))

        self.endTransmission()

    def startTransmitting(self):
        if(self.transmitting == False):
            self.transmitting = True
            threading.Thread(target=self._transmitLoop).start()

    def _transmitLoop(self):
        while self.transmitting:
            self.transmit()
            time.sleep(1)

    def transmit(self):
        if(self.lastTransmission + self.transmissionDelay < time.time()):

            if(self.queue.length() == 0):
                self.sendCurrentStates([s.getTeleData() for s in self.systems])
            
            if(self.queue.length() != 0):
                dat = self.queue.pop()
                self.writeString(dat)
                self.logger.logInfo("Telemtry Data Package: {}".format(dat))

            self.lastTransmission = time.time()	
    
    def stopTransmitting(self):
        self.transmitting = False

    def startReceiving(self):
        if (self.receiving == False):
            self.receiving = True
            threading.Thread(target=self._receiveLoop).start()
    
    def _receiveLoop(self):
        while self.receiving:
            if(self.checkForStartSignal()):
                self.receiving = False
            time.sleep(1)

    def checkForStartSignal(self):
        iss_string1 = str(super().readBytes(42, 200))
        iss_string2 = str(super().readBytes(42, 200))

        iss_string = iss_string1 + iss_string2 + iss_string1
        iss_pos = iss_string.find(START_STRING)
        if(iss_pos >= 0 and self.experimentStarted != True):
            self.logger.logInfo("Experiment Start: ISS START SIGNAL RECEIVED: {}".format(iss_string[iss_pos:(len(START_STRING) + iss_pos)]))
            self.experimentStarted = True

        return self.experimentStarted
    
    def stopReceiving(self):
        self.receiving = False
    
    def getExperimentStartStatus(self):
        return self.experimentStarted
    
    def isReceiving(self):
        return self.receiving

    def isTransmitting(self):
        return self.transmitting

    def selfTest(self):
        self.logger.logInfo("Telemetry Test")
        for x in range(5):
            self.transmit()
            time.sleep(self.transmissionDelay)
        self.logger.logInfo("End")
            
