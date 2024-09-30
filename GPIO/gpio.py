import RPi.GPIO as GPIO
from Logger.Logger import Logger
from time import sleep


BOARD2BCM=[
   -1, -1,  2, -1,  3, -1,  4, 14,
   -1, 15, 17, 18, 27, -1, 22, 23,
   -1, 24, 10, -1,  9, 25, 11,  8,
   -1,  7,  0,  1,  5, -1,  6, 12,
   13, -1, 19, 16, 26, 20, -1, 21]

class GPIOMapping(): 
    def convertTOBCM(pin : int):
        logger = Logger("Pin Converter")
        if(pin >= 1 and pin <= 40):
            if(BOARD2BCM[pin-1] != -1):
                return BOARD2BCM[pin-1]
        logger.logErr("Pin Error {pin}".format(pin = pin))
        return -1

class SingleGPIO():
    def __init__(self,PIN:int, LOG = True, CONVERT=True):
        self.PIN = GPIOMapping.convertTOBCM(PIN) if CONVERT else PIN
        self.state = False
        self.logger = Logger("PIN {pin}".format(pin = PIN),LOG)

    def setup(self):
        GPIO.setmode(GPIO.BCM)
        try:
            self.logger.logInfo("Setting up pin {pin} ".format(pin = self.PIN))
            GPIO.setup(self.PIN , GPIO.OUT)
            GPIO.output(self.PIN, False)
        except Exception as e:
            self.logger.logErr("Error setting up pin {pin} ".format(pin = self.PIN),e)
    
    def _set(self, state : bool):
        GPIO.setmode(GPIO.BCM)
        #self.logger.logInfo("Setting pin {}".format(state))
        try:
            GPIO.setup(self.PIN, GPIO.OUT)
            GPIO.output(self.PIN, state)
        except Exception as e:
            self.logger.logErr("Errpr setting pin",e)
        self.state = state
    
    def close(self):
        GPIO.setmode(GPIO.BCM)
        try:
            self._set(False)
            self.logger.logInfo("Freeing pin {pin}".format(pin = self.PIN))
            GPIO.output(self.PIN , False)
        except Exception as e:
            self.logger.logErr("Error freeing pin {pin}".format(pin = self.PIN),e)  
        
    def test(pin):
        logger = Logger("SingleGPIO Test")

        logger.logInfo("Start: Setup")
        gpio = SingleGPIO(pin)
        
        for x in range(100):

            logger.logInfo("On")
            gpio._set(True)
            sleep(1)

            logger.logInfo("Off")
            gpio._set(False)
            sleep(1)

        logger.logInfo("Free")
        gpio.close()

        logger.logInfo("End")
