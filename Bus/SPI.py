# https://forums.raspberrypi.com/viewtopic.php?t=190362 suggests using PIGPIO library to directly implement SPI without any layer in between for maximum speed (ca. 3x improvement)
from subprocess import check_output

from sys import platform

if platform == "linux":
    import spidev

from Logger.Logger import Logger

""" Interface to the /dev/spidevX.Y kernel driver """
""" TODO: async-await implementation? """


class SpidevBus:
    CLOSE_ON_ERROR = "COE"

    """ Initializes """

    def __init__(self, device: int, bus: int = 0, speed: int = 12_800_000, mode=0b01, no_cs: bool = True):
        self.spi = None
        self.logger = Logger("Spidev-SPI Bus")
        self.bus = bus
        self.device = device
        self.speed = speed
        self.mode = mode
        self.no_cs = no_cs
        self.setup()

    def setup(self):
        self.logger.logInfo("Setting up Bus")

        self.init()

    def init(self):
        self.spi = spidev.SpiDev()
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = self.speed
        self.spi.mode = self.mode
        self.spi.no_cs = self.no_cs

    def read(self, nbytes: int):
        return self.spi.readbytes(nbytes)

    def write(self, byte_array):
        return self.spi.writebytes(byte_array)

    """ A list of bytes is written to the SPI device and as each byte in that list is sent out, it is replaced by the data simultaneously read from the SPI slave device over the MISO line """

    def transfer(self, byte_array, speed=0):
        return self.spi.xfer(byte_array, speed or self.speed)

    def close(self):
        if self.spi:
            self.spi.close()

        self.spi = None


""" SPI wrapper using PIGPIO """


class Pigpio_SpiBus:
    """ See https://abyz.me.uk/rpi/pigpio/python.html#spi_open for arguments """

    def __init__(self, cs_pin: int, pi_instance=None, bus: int = 0, speed: int = 16000000, mode=0b01):
        self.handle = None
        self.logger = Logger("PiGPIO-SPI Bus")
        self.bus = bus
        self.cs = cs_pin
        self.speed = speed
        self.pi = pi_instance
        self.mode = mode
        self.setup()

    def setup(self):
        self.logger.logInfo("Setting up Bus")
        try:
            # try to start deamon
            out = check_output(["sudo", "pigpiod"])  ###not working !!!
        except Exception as e:
            self.logger.logErr("Error starting deamon for pigpio", e)

        self.init()

    def init(self):
        if self.pi == None:
            self.pi = pi()

        # TODO: build spi_flags
        # For now, only mode
        # spi_flags = 0b.....
        # self.handle = spi_open(self.cs_pin, self.speed, spi_flags)

        if not self.pi.connected:
            raise Exception("SPI wrapper could not connect to pigpio deamon")
        else:
            self.handle = self.pi.spi_open(self.cs, self.speed, self.mode)

    def on_error(self, error):
        print(error)
        self.close()

    def read(self, nbytes: int):
        length, data = self.pi.spi_read(self.handle, nbytes)
        if length == nbytes:
            return data
        else:
            self.on_error()

    def write(self, byte_array):
        return self.pi.spi_write(self.handle, byte_array)

    """ A list of bytes is written to the SPI device and as each byte in that list is sent out, it is replaced by the data simultaneously read from the SPI slave device over the MISO line """

    def transfer(self, byte_array):
        return self.pi.spi_xfer(self.handle, byte_array)

    def close(self):
        if self.handle != None:
            self.pi.spi_close(self.handle)

        self.handle = None
