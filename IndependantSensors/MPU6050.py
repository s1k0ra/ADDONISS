from Logger.Logger import Logger
import subprocess
import time
import board
import adafruit_mpu6050
from Telemetry.Telemetry import TelemetryDataSource,TeleDatatypes

class MPU6050(TelemetryDataSource):
    def __init__(self):
        self.logger = Logger("MPU6050")
        try:
            self.i2c = board.I2C()
            self.acc = [-100,-100,-100]
            self.gyro = [-100,-100,-100]
            self.temp = -242
            self.mpu = adafruit_mpu6050.MPU6050(self.i2c, address = 0x69)
        except Exception as e:
            self.logger.logErr("Error connecting MPU6050",e)

    def read(self):
        try:
            self.acc = self.mpu.acceleration
            self.gyro = self.mpu.gyro
            self.temp = self.mpu.temperature

            #self.logger.logInfo("Acceleration: X:%.2f, Y: %.2f, Z: %.2f m/s^2" % (self.acc))
            #self.logger.logInfo("Gyro X:%.2f, Y: %.2f, Z: %.2f rad/s" % (self.gyro))
            #self.logger.logInfo("Temperature: %.2f C" % self.temp)
            
            self.logger.logSensorData("mpu6050", self.getTeleData())
        except Exception as e:
            self.logger.logErr("Error reading data from mpu6050",e)

    def getTeleData(self):
        return  {"acc_x" : (self.acc[0],TeleDatatypes.FLOAT) 
                ,"acc_y" : (self.acc[1] ,TeleDatatypes.FLOAT)
                ,"acc_z" : (self.acc[2],TeleDatatypes.FLOAT)
                ,"gyro_x" : (self.gyro[0],TeleDatatypes.FLOAT)
                ,"gyro_y" : (self.gyro[1],TeleDatatypes.FLOAT)
                ,"gyro_z" : (self.gyro[2],TeleDatatypes.FLOAT)
                ,"mpu_tmp" : (self.temp,TeleDatatypes.FLOAT)}
    
    def selfTest(self):
        self.logger.logInfo("MPU6050 Test")
        self.read()
        self.logger.logInfo("End")
