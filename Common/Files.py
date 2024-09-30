from datetime import datetime
import os
import uuid
from Logger.Logger import LOG_DIRECTORY

def generate_time_part():
    now = datetime.now()
    return now.strftime("%Y-%m-%d_%H-%M-%S")


def generate_filepath(suffix, prefix="", base_path = LOG_DIRECTORY):
    unique_part = uuid.uuid4().hex[0:15]
    return (base_path + prefix + generate_time_part() + "_" + unique_part + suffix)


