import RPi.GPIO as GPIO
import time
from Logger.Logger import Logger
from HeatingSystem.heatingSystem import GPIOMapping
import threading
import board
import adafruit_ds3231
from datetime import datetime
from Telemetry.Telemetry import TelemetryDataSource,TeleDatatypes
from Systemparameters.SystemData import BashExecution
from time import mktime

class RTC(TelemetryDataSource):
    def __init__(self):
        self.logger = Logger("RTC")
        self.rtc = None
        self.timestamp = (1980,0,0,0,0,0,0,0,0)

        self.connect()

    def connect(self):
        self.logger.logInfo("Connecting RTC")
        try:
            i2c = i2c = board.I2C()
            self.rtc = adafruit_ds3231.DS3231(i2c)
        except Exception as e:
            self.logger.logErr("Error Connecting to RTC",e)
    
    def setRTCByTimestamp(self,timestamp:int):
        dt = datetime.utcfromtimestamp(timestamp)
        self.setRTCTime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday())


    def setRTCTime(self,year,month,date,hour,min,sec,wday,yday=-1,isdst=-1):
        try:
            t = time.struct_time((year, month, date, hour, min, sec, wday, yday, isdst))
            self.logger.logInfo("Setting time to: {}".format(t))  # uncomment for debugging
            self.rtc.datetime = t
        except Exception as e:
            self.logger.logErr("Error setting time on RTC")

    def getTime(self):
        self.logger.logInfo("Reading time from RTC")
        try:
            self.timestamp = self.rtc.datetime
            self.logger.logInfo("Read time: {}".format(self.timestamp))
            self.printTime(self.timestamp)
        except Exception as e:
            self.logger.logErr("Error reading time from rtc",e)
        return self.timestamp


    def printTime(self,t):
        days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
        self.logger.logInfo("The date is {} {}/{}/{}".format(days[int(t.tm_wday)], t.tm_mday, t.tm_mon, t.tm_year))
        self.logger.logInfo("The time is {}:{:02}:{:02}".format(t.tm_hour, t.tm_min, t.tm_sec))
    
    def setSystemTime(self):
        self.getTime()
        try:
            time = "{}-{}-{} {}:{}:{}".format(self.timestamp.tm_year,  self.timestamp.tm_mon, self.timestamp.tm_mday, self.timestamp.tm_hour, self.timestamp.tm_min, self.timestamp.tm_sec)
            cmd = "sudo date -s '{}'".format(time)
            output = BashExecution.execute(cmd)
            self.logger.logInfo("Setting system time to: {}".format(output))
        except Exception as e:
            self.logger.logErr("Error setting system time", e)

    def getTeleData(self):
        return {"timestamp" : (int(mktime(self.timestamp)), TeleDatatypes.INT)}

    def selfTest(self):
        self.logger.logInfo("RTC Test")
        self.getTime()
        self.setSystemTime()
        self.logger.logInfo("End")

    def test():
        rtc = RTC()
        rtc.getTime()
        rtc.setSystemTime()




