from Logger.Logger import Logger, LOG_DIRECTORY
from Telemetry.Telemetry import PackageQueue
import shutil
from os import listdir, remove
from os.path import isfile, join, getmtime

BACKUP_PATH = "/mnt/usb/"

class DataMirrow():

    def __init__(self):
        self.files_to_backup = PackageQueue()
        self.files_to_overwrite = PackageQueue()
        self.dates_of_files = dict()
        self.logger = Logger("DataMirrow")

    def backupFile(self):
        try:
            if(self.files_to_backup.length() > 0):
                f = self.files_to_backup.pop()
                src_path = join(LOG_DIRECTORY, f)
                dst_path = join(BACKUP_PATH, f)
                out = shutil.copy2(src_path, dst_path)
            
            elif(self.files_to_overwrite.length() > 0):
                f = self.files_to_overwrite.pop()
                src_path = join(LOG_DIRECTORY, f)
                dst_path = join(BACKUP_PATH, f)
                #remove(BACKUP_PATH + f)
                out = shutil.copy2(src_path, dst_path)
            
            else:
                self.getFilesToBackup()
        except Exception as e:
            self.logger.logErr("Error copying Files", e)
    
    def getFilesToBackup(self):
        try:
            for f in listdir(LOG_DIRECTORY):
                file_path = join(LOG_DIRECTORY, f)
                if isfile(file_path) and not f.startswith('.'):
                    date = getmtime(file_path)
                    listed = f in self.dates_of_files.keys()
                    if(listed and self.dates_of_files[f] != date):
                        self.files_to_overwrite.add(f)
                        self.dates_of_files[f] = date 
                    elif(not listed):
                        self.files_to_backup.add(f)
                        self.dates_of_files[f] = date
                
        except Exception as e:
            self.logger.logErr("Error getting Files", e)
        
