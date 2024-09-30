from Bus.SPI import SpidevBus
from Common.Files import generate_filepath
import time
import numpy as np
from MEASystem.meaTools import process_sample, process_samples
from Telemetry.Telemetry import TelemetryDataSource,TeleDatatypes
import traceback

# Maps MEA index to connector; MEA index 0=MEA 1, index 1=MEA2, etc.
MEA_CONNECTOR_MAP = {
    0: 7,
    1: 6,
    2: 5,
    3: 4,
    4: 3,
    5: 2
}

MEA_SPEED_ADJUSTMENT = 1.5

# MeaSPI reads out the MEAs using the same spidev instance
# mea_no runs from 0-5 for the total 6 MEAs
class MeaSPI(SpidevBus, TelemetryDataSource):
    active = False
    active_mea = None
    shift_register = None
    readoutCounter = [0] * 6

    def getTeleData(self):
        return {"mea_1" : (self.readoutCounter[0], TeleDatatypes.INT),
                "mea_2" : (self.readoutCounter[1], TeleDatatypes.INT),
                "mea_3" : (self.readoutCounter[2], TeleDatatypes.INT),
                "mea_4" : (self.readoutCounter[3], TeleDatatypes.INT),
                "mea_5" : (self.readoutCounter[4], TeleDatatypes.INT),
                "mea_6" : (self.readoutCounter[5], TeleDatatypes.INT)}

    def setShiftRegister(self, shift_register):
        self.shift_register = shift_register

    def start_read(self, mea_no: int, stimulation : bool):
        self.logger.logInfo("Start MEA readout for mea {}".format(mea_no))

        if self.active:
            raise Exception('Error: Readout still in progress')

        if not (mea_no in MEA_CONNECTOR_MAP):
            raise Exception('Invalid MEA number. Only 0-5')

        # Turn on MEA readout board, wait for 2s
        self.shift_register.setOutput(MEA_CONNECTOR_MAP[mea_no], False)

        self.active = True
        self.active_mea = mea_no

        time.sleep(1.5)

        # Send SPI byte "39" (not hex!)
        rcvd = 0
        if(stimulation):
            rcvd = self.transfer([40])
        else:
            rcvd = self.transfer([39])

        # Wait for response "82" (not hex!) (readout until then will be zeros)
        # Read should block the program until it receives 1 byte

        # Wait for 2 seconds, if still not ready ==> raise exception
        t_s = time.time()
        while rcvd[0] != 82:
            rcvd = self.read(1)
            if time.time() - t_s > 2:
                self.active = False
                self.active_mea = None

                raise Exception('MEA timed out')

        self.logger.logInfo("Armed MEA readout for mea {}".format(mea_no))

    def stop_read(self):
        self.shift_register.setHigh()
        self.active = False
        self.active_mea = None
        self.logger.logInfo('Stopped MEA readout')

    # Returns msb, lsb
    def read_sample_pair(self):
        if not self.active:
            raise Exception('MEA not active')

        # NNNNDDDD DDDDDDDD
        # where "N" is a channel number and "D" is the data
        return self.read(2)

    def read_sample(self):
        msb, lsb = self.read_sample_pair()

        return process_sample(msb, lsb)

    """
    Attempts to read n_samples*2 bytes from the MEA and outputs them to
    a list of lists of size chunk_size.
    
    The resulting n_samples might differ (be lower) than the supplied
    n_samples if n_samples*2 is not a multiple of chunk_size
    """

    def read_samples_raw(self, n_samples, chunk_size=4096):
        if not self.active:
            raise Exception('MEA not active')

        if n_samples < chunk_size:
            raise Exception('Number of samples must be larger than chunk_size')

        if not (chunk_size % 2 == 0):
            raise Exception('chunk_size expected to be a multiple of 2')

        samples_raw = []

        n_readouts = n_samples * 2 // chunk_size
        # n_samples may be changed because supplied n_samples*2 may not be a multiple of chunk_size
        n_samples = int(n_readouts * chunk_size / 2)

        for i in range(0, n_readouts):
            samples_raw.append(self.read(chunk_size))

        return samples_raw, n_samples

    """
    Do a MEA readout and save the results as compressed NPZ file in the format:
    Array: [
        Array[double]: [read_start, read_end],
        Array[UInt16]: ADC_VALUES
    ]
    
    mea_no ∈ 0:5 (MEAs 1-6)
    """

    def readout(self, mea_no: int, stimulation = False, n_samples=4096, save=True, debug=False):
        # one sample is 2byte large
        # 1 Mio. samples ==> 2 MB data
        
        try:
            self.logger.logInfo("Mea Readout with speed={} and samples={}".format(self.speed, n_samples))

            # Setting up SPI-Bus
            super().setup()
            time.sleep(0.01)

            self.start_read(mea_no, stimulation)

            r_start = time.time()
            samples_raw, n_samples = self.read_samples_raw(n_samples)
            r_end = time.time()
            r_time = r_end - r_start

            self.stop_read()

            # Close SPI-Bus
            super().close()
            time.sleep(0.01)

            payload = np.array([
                np.array([r_start, r_end], dtype=np.double),
                np.array(samples_raw, dtype=np.uint16),
            ], dtype=object)

            # sn_start = time.time()
            # np.save('samples_raw.npy', payload)
            # sn_time = time.time() - sn_start

            if save:
                sz_start = time.time()
                np.savez_compressed(generate_filepath('_MEA_' + str(mea_no) + '.npz'), payload)

                if debug:
                    r_rate = round(n_samples * 2 / 1024 / r_time)
                    print('Read Time', r_time, 's')
                    print('Read Rate', r_rate, 'kB/s')

                    # print("Save Time(NPY)", sn_time, "s")
                    print('Save Time(NPZ)', (time.time() - sz_start), 's')

                    print('Read total size', n_samples * 2, 'bytes')

            self.readoutCounter[mea_no] += 1

            return payload
        except Exception as e:
            self.logger.logErr("Failed MEA readout for mea {}".format(mea_no),e)

    # For all MEAs, read one value; WARNING: takes 6*2+X seconds
    def readout_all(self, n_samples=1):
        result_samples = []
        result_times = []

        for i in range(0, 5):
            temp = self.readout(i, n_samples, save=False)
            temp_times = temp[0]
            temp_samples = temp[1]

            result_times.append(temp_times)
            result_samples.append(temp_samples)

        return result_samples, result_times

    
    def getNumberOfSample(speed, seconds):
        return int(((speed / 8) / 2) * seconds/MEA_SPEED_ADJUSTMENT)
    
    def getBaudRate(khz):
        return int(32 * khz * 1_000 * 2 * 8 * MEA_SPEED_ADJUSTMENT) 

    def selfTest(self):
        seconds = 30
        self.logger.logInfo("MEA Test")
        for mea_no in range(6):
            self.readout(mea_no, n_samples=MeaSPI.getNumberOfSample(speed = self.speed, seconds = seconds), stimulation=False)
            time.sleep(5)

        self.logger.logInfo("End")
