from PumpSystem.pumpSystem import SingleGPIO
from Logger.Logger import Logger
from time import sleep
import time

class BooleanList():
    def __init__(self, data : list = []):
        self.list = list()
        self.logger = Logger("Boolean List {}".format(time.time()))

        for d in data:
            if type(d) == bool:
                self.list.append(d)
            else:
                self.logger.logErr("Input list doesn't contain only booleana e.g. : {} : {}".format(d,type(d)))
                self.list = []
                break
    
    def getList(self):
        return self.list

    def equals(self, booleanList):
        return self.list == booleanList.list

class ShiftRegister():
    #DS : Serial, SHCP: SRCLK, STCP: RCLK 
    def __init__(self, DS_PIN, SHCP_PIN, STCP_PIN, outputSize = 8):
        self.DS = SingleGPIO(DS_PIN)
        self.SHCP = SingleGPIO(SHCP_PIN)
        self.STCP = SingleGPIO(STCP_PIN)
        self.outputSize = outputSize
        self.logger = Logger("Shift Register")
        self.states = BooleanList([True for _ in range(self.outputSize)])
        self.setup()
    
    def setup(self):
        self.logger.logInfo("Setting up Shft Register")
        self.DS._set(False)
        self.SHCP._set(False)
        self.STCP._set(False)
        self.setHigh()
        
    def setHigh(self):
        self.states = BooleanList([True for x in range(self.outputSize)])
        self.set(self.states)

    def setLow(self):
        self.states = BooleanList([False for x in range(self.outputSize)])
        self.set(self.states)

    def setOutput(self, outputNumber:int, state:bool):
        if(outputNumber <= self.outputSize and outputNumber >= 0 and type(state) == bool):
            newStates = BooleanList([True for x in range(self.outputSize)])
            newStates.list[outputNumber] = state

            if not newStates.equals(self.states):
                self.set(newStates)
        
        else:
            self.logger.logErr("Error setting output to value, since outputNumber or outputtype is invalid : outputNumber: {}, ouput: {},  ouputSize:  {}".format(outputNumber, state , self.outputSize))
    
    def set(self, out : BooleanList):
        if(len(out.getList()) != self.outputSize):
            self.logger.logErr("Output has not pecise number of values to set shift register: outputSize={}, outValues={}".format(self.outputSize, out))

        else:
            #self.logger.logInfo("Set Shiftregister states to : {}".format(out.getList()))

            self.STCP._set(False)
            time.sleep(0.0001)

            for o in out.getList():
                self.SHCP._set(False)
                time.sleep(0.0001)

                self.DS._set(o)
                time.sleep(0.0001)

                #write DS to register
                self.SHCP._set(True)
                time.sleep(0.0001)

            #output values in shift register
            self.STCP._set(True)
            time.sleep(0.0001)

            #set all outputs to LOW
            self.DS._set(False)
            time.sleep(0.0001)

            self.SHCP._set(False)
            time.sleep(0.0001)

            self.STCP._set(False)
            time.sleep(0.0001)

            self.states = out


    def free(self):
        self.logger.logInfo("Freeing Shift Register")
        self.setHigh()

    def selfTest(self):
        logger = Logger("Shift register Test")
        logger.logInfo("Start")
        output = [True for x in range(self.outputSize)]

        for x in range(self.outputSize):
            output[max(x-1, 0)] = True
            output[x] = False

            self.set(BooleanList(output))
            sleep(2)
        
        output[len(output)-1] = True
        self.set(BooleanList(output))

        logger.logInfo("Stop")
    
    def test():
        shiftreg = ShiftRegister(10,26,24)
        #output = BooleanList([True, True, False, False, False, False, False, False])
        #shiftreg.set(output)
        shiftreg.setHigh()
    
        
