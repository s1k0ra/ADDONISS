import RPi.GPIO as GPIO
import time
from Logger.Logger import Logger
from HeatingSystem.heatingSystem import GPIOMapping
import threading
import board
import adafruit_ds3231

class Time():
    
    def __init__(self,rtc):
        self.rtc = rtc
        pass

    def getTime(self):
        return time.time()

class RTC():
    def __init__(self):
        self.logger = Logger("RTC")
        self.rtc = None

        self.connect()

    def connect(self):
        self.logger.logInfo("Connecting RTC")
        try:
            i2c = i2c = board.I2C()
            self.rtc = adafruit_ds3231.DS3231(i2c)
        except Exception as e:
            self.logger.logErr("Error Connecting to RTC",e)
    
    def setTime(self,year,month,date,hour,min,sec,wday,yday=-1,isdst=-1):
        try:
            t = time.struct_time((year, month, date, hour, min, sec, wday, yday, isdst))
            self.logger.logInfo("Setting time to: {}".format(t))  # uncomment for debugging
            self.rtc.datetime = t
        except Exception as e:
            self.logger.logErr("Error setting time on RTC")

    def getTime(self):
        t = -1
        self.logger.logInfo("Reading time from RTC")
        try:
            t = self.rtc.datetime
            self.logger.logInfo("Read time: {}".format(t))
            self.printTime(t)
        except Exception as e:
            self.logger.logErr("Error reading time from rtc",e)
        return t

    def printTime(self,t):
        days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
        self.logger.logInfo("The date is {} {}/{}/{}".format(days[int(t.tm_wday)], t.tm_mday, t.tm_mon, t.tm_year))
        self.logger.logInfo("The time is {}:{:02}:{:02}".format(t.tm_hour, t.tm_min, t.tm_sec))
    
    def setSystemTime(self):
        pass

    def test():
        rtc = RTC()
        rtc.getTime()




