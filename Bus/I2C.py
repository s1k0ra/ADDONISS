from time import sleep
from Logger.Logger import Logger
import time
import busio
import board

class PythonWire():
    def __init__(self, address, maxBytesForWrite=200):
        self.address = address
        self.buffer = []
        self.i2c = None
        self.maxBytesForWrite = maxBytesForWrite
        self.logger = Logger("I2C Bus")

    def begin(self):

        self.logger.logInfo("Setting up i2c")

        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
        except Exception as e:
            self.logger.logErr("Error opening i2c connection",e)

    def beginTransmission(self,address=None):
        if(address != None):
            self.address = address
            
        self.buffer = []

    def write(self, data : int):
        if(len(self.buffer) >= self.maxBytesForWrite):
            self.logger.logErr("Buffer exceeded in write for I2C")
        else:
            self.buffer.append(data)
    

    def readBytes(self,address, size:int):
        try:
            data = bytearray(size)
            self.i2c.readfrom_into(address, data)
            return data
        except Exception as e:
            self.logger.logErr("Error reading bytes from address: {} size: {}".format(address,size),e)

    def endTransmission(self):

        try:
            self.i2c.writeto(self.address, bytes(self.buffer), stop=False)
        except Exception as e:
            self.logger.logErr("Error writing data at the of transmission input: {}".format(self.buffer),e)
    
    def close(self):
        try:
            self.logger.logInfo("Closing i2c")
            self.logger.logErr("Not Implemented")
        except Exception as e:
            self.logger.logErr("Error closing i2c",e)

    
    def test():
        wire = PythonWire(address=42,baudRate=100_000)
        wire.begin()
        string = '"tmp1_1":23.2\n'
        #string = PythonWire._tmpToByteDatum("tmp1_1",23.2) + "\n"

        
        while True:
            print("Send")

            wire.beginTransmission(42)
            wire.write(1)
            print(string)
            print(len(string))
            wire.write(len(string))

            for c in string.encode('utf-8'):
                wire.write(c)

            wire.endTransmission()

            #print(wire.readBytes(42, 20))
            #print("End")
            
            time.sleep(5)







