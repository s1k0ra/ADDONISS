from Logger.Logger import Logger
from Telemetry.Telemetry import TelemetryDataSource,TeleDatatypes
import subprocess

class BashExecution():
    def execute(cmd : str):
        logger = Logger("BashExecution")
        try:
            (e,s) = subprocess.getstatusoutput(cmd)
            if(e != 0):
                logger.logErr("Error executing command: {}".format(s))
                return -1
            return s
        except Exception as e:
            logger.logErr("Error executing command : {}".format(cmd),e)


class SystemParameters(TelemetryDataSource):
    def __init__(self):
        self.logger = Logger("System Paramters")
        
    def execute(self, cmd : str):
        return BashExecution.execute(cmd)

    def extractNumber(self, string : str):
        res = ""
        numberSpotted = False
        dotCount = 0
        for c in string:
            if(c.isdigit()):
                res += c
                numberSpotted = True
            
            elif(c == '.' and dotCount == 0):
                res += c
                dotCount+=1
            
            elif(not numberSpotted):
                pass

            else:
                break
        return res

    def getCPUTemp(self):
        s = ""
        try:
            s = self.execute("head -n 1 /sys/class/thermal/thermal_zone0/temp")
            temp = int(s) * 0.001
            self.logger.logInfo("cpu temp: {}C°".format(temp))
            self.logger.logSensorData("cpu_temp",{ "cpu_temp" : temp})
            return temp
        except Exception as e:
            self.logger.logErr("Error parsing CPUTeMP : {}".format(s),e)
            return -242

    def getSDVolumeSize(self):
        output = ""
        try:
            output = self.execute("df -h | sort -h -k3 -r | tr -s ' ' | cut -d ' ' -f 3 | head -n 1")
            self.logger.logInfo("sd_volume size: {}".format(output))
            self.logger.logSensorData("sd_volume_size",{ "sd_volume size" : output})
            return float(self.extractNumber(output)) 
        except Exception as e:
            self.logger.logErr("Error parsing sd volume size: {}".format(output),e)
            return -1


    def getUSBVOlumeSize(self):
        output = ""
        try:
            output = self.execute("df -h | sort -h -k3 -r | tr -s ' ' | cut -d ' ' -f 3 | head -n 2 | tail -1")
            self.logger.logInfo("usb_volume size: {}".format(output))
            self.logger.logSensorData("usb_volume_size",{ "usb_volume size" : output})
            return float(self.extractNumber(output)) 
        except Exception as e:
            self.logger.logErr("Error parsing usb volume: {}".format(output),e)
            return -1

    def getRAMUsage(self):
        output = ""
        try:
            output = self.execute("free -h | head -2 | tail -1 | tr -s ' ' | cut -d ' ' -f 3")
            self.logger.logInfo("ram_usage: {}".format(output))
            self.logger.logSensorData("ram_usage",{ "ram_usage" : output})
            return float(self.extractNumber(output))
        except Exception as e:
            self.logger.logErr("Error parsing RAM Usage: {}".format(output),e)
            return -1


    # uptime | tr -s ' ' | cut -d ' ' -f10
    def getCPUUsage(self):
        output = ""
        try:
            output = self.execute("uptime | tr -s ' ' | cut -d ' ' -f11")
            self.logger.logInfo("cpu_usage: {}".format(output))
            self.logger.logSensorData("cpu_usage",{ "cpu_usage" : output})
            return float(self.extractNumber(output))
        except Exception as e:
            self.logger.logErr("Error parsing cpu usage: {}".format(output),e)
            return -1



    def getTeleData(self):
        return {"cpu_temp" : (self.getCPUTemp(),TeleDatatypes.FLOAT),
                "cpu": (self.getCPUUsage(),TeleDatatypes.FLOAT),
                "ram":(self.getRAMUsage(),TeleDatatypes.FLOAT),
                "sd_volume":(self.getSDVolumeSize(),TeleDatatypes.FLOAT),
                "usb_volume":(self.getUSBVOlumeSize(),TeleDatatypes.FLOAT)}
    
    def test():
        logger = Logger("SystemParameter Read Test")
        logger.logInfo("Start")
        sp = SystemParameters()
        logger.logInfo("parmas: {}".format(sp.getTeleData()))
        
        