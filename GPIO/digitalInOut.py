from GPIO.gpio import SingleGPIO
from ShiftRegister.shiftRegister import ShiftRegister
from Logger.Logger import Logger
import time

#41 = SS_MEA1
#42 = SS_MEA2
#43 = SS_MEA3
#44 = SS_MEA4
#45 = SS_MEA5
#46 = SS_MEA6
#47 = SS_TReadout_1
#48 = SS_TReadout_2

class SelektroPin():
    def __init__(self, PIN:int, shtReg : ShiftRegister = None, LOG = True, CONVERT=True):
        self.shtReg = None
        self.singlePin = None
        self.state = False
        self.pin = PIN
        self.logger = Logger("SelektorPin {pin}".format(pin = PIN), LOG)

        if(PIN >= 41 and PIN <= 48 and shtReg != None):
            self.logger.logInfo("Setting cs to shiftregister")
            self.shtReg = shtReg

        elif(PIN >= 1 and PIN <= 40 and shtReg == None):
            self.logger.logInfo("Setting cs to singlegpio")
            self.singlePin = SingleGPIO(PIN,LOG,CONVERT)
            self.setup()
        
        else:
            self.logger.logErr("No valid arguments PIN = {} shtReg = {}".format(PIN, shtReg))

    def setup(self):
        if(self.singlePin != None):
            self.singlePin.setup()
            self.singlePin._set(True)

    def set(self, state:bool):
        if(state != self.state):
            if(state == True):
                if(self.singlePin != None):
                    self.singlePin._set(state)
                else:
                    self.shtReg.setHigh()
                    
            else:
                if(self.singlePin != None):
                    self.singlePin._set(state)
                else:
                    self.shtReg.setOutput(self.pin % 40 - 1, state)

        self.state = state


    def getState(self):
        return self.state
    
    def free(self):
        if(self.singlePin != None):
            self.singlePin.close()
        else:
            self.shtReg.free()

class DigitalInOut():

    def __init__(self, PIN, shtReg : ShiftRegister = None, LOG = True, CONVERT=True):
        self.cs = SelektroPin(PIN, shtReg, LOG, CONVERT)
        self.logger = Logger("DigitalInOut Custom {}".format(PIN))

    def switch_to_output(self, value=False, drive_mode=None):
        if (drive_mode != None):
            self.logger.logErr("DigitalInOut.switch_to_output value={} or drive_mode={} not default value, probabbly not implementes".format(value, drive_mode))
        self.logger.logInfo("Setting up pin with value = {}".format(value))
        self.cs.set(value) 
    
    @property
    def value(self):
        return self.cs.getState() == True

    @value.setter
    def value(self, val):
         #self.logger.logInfo("Setting Pin to {}".format(val))
         self.cs.set(val)
