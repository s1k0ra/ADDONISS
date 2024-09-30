import numpy as np

def process_sample(msb, lsb):
    # To check bitwise operations, print them using format(value,'08b')
    # Shift msb 4 bits to the right
    channel_no = msb >> 4

    # AND mask to only select last 4 bits
    # equivalent to msb & 0b00001111
    adc_msb = msb & 0b1111

    # Shift msb 8 bits to the left, this is where lsb is added
    adc_data = (adc_msb << 8) + lsb

    return adc_data, channel_no


"""
Transforms the samples_raw (list of lists) from read_samples_raw
to numpy arrays containing time, channels and ADC value

Calculates n_samples from samples_raw if it's not supplied
By setting  process_channels=False, channels are stored "AS IS"
"""


def process_samples(times_raw, samples_raw, n_samples=0, process_channels=True):
    chunk_size = len(samples_raw[0])
    chunk_size_half = int(chunk_size // 2)

    if n_samples == 0:
        n_samples = len(samples_raw) * chunk_size_half

    times = np.empty(n_samples + 1, dtype=np.double)
    data = np.empty(n_samples, dtype=np.uint16)
    channels = np.empty(n_samples, dtype=np.uint8)

    # Merge list of lists and flatten
    samples = np.array(samples_raw, dtype=np.uint16).flatten()

    j = -1 # index of the times_raw array to use as time
    k = 1  # channels read out sequentially: first 0->15 channels 1->16, second 0-15 17->32, then again 0->15
           # k = -1 means first 16 channels (1-16), +1 second 16channels (17-32)
    dt_step = (times_raw[1] - times_raw[0]) / chunk_size_half

    for i in range(0, n_samples):
        # Switch sign of k after every 16 samples to get all 32 channels
        if i % 16 == 0:
            k = k * (-1)

        adc_value, channel = process_sample(samples[i * 2], samples[i * 2 + 1])
        times[i] = times_raw[j] + dt_step * (i % chunk_size_half)  # we retrieve the time once for all samples of a chunk and interpolate between chunks
        data[i] = adc_value
        channels[i] = channel + (0 if (not process_channels or k == -1) else 16)

    return times, data, channels, samples


"""
Verifies samples_raw as returned by read_sample_pairs.
Checks the first and last chunk (if given).

Makes sure the channel_no runs up from 0 to 15 and returns
and errors specifying the number of entries which either
- do not have a matching channel_no (i.e. prev.+1) or
- are missing (i.e. from channel_no=13 to 0 will add 3)
"""

def verify_samples(self, samples_raw):
    # Analyze first chunk
    times, data, channels, samples = process_samples(times_raw=[0], samples_raw=[samples_raw[0]],
                                                        process_channels=False)

    def calc_errors(channels, start_channel=0):
        errors = 0
        # expected channel
        exp_channel = start_channel

        # We expected channels to increment by 1, run until 15 and then back to 0
        # i.e. 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,0 etc.
        for channel in channels:
            if not exp_channel == channel:
                if channel == 0:
                    # Some channels have been skipped
                    #   if exp_channel was 14, we skipped 14+15 (i.e. 2 channels)
                    #   if exp_channel was 15, we skipped 15 (i.e. 1 channel)
                    errors += 16 - exp_channel
                else:
                    if exp_channel < channel:
                        # expected 5, got 7 -> error is simple difference
                        errors += channel - exp_channel
                    else:
                        # expected 7, got 5 -> all channels from expected channel to 15, then from 0 to actual channel
                        # expected 15, got 0
                        errors += (16 - exp_channel) + channel

            # We expect channels to increment by one once after every measurement
            if channel >= 15:
                exp_channel = 0
            elif exp_channel > channel:
                exp_channel = channel + 1
            else:
                exp_channel += 1

        return errors

    errors = calc_errors(channels)
    n_tested = len(channels)

    # Analyze last chunk (if exists)
    if len(samples_raw) > 1:
        times, data, channels, samples = process_samples(times_raw=[0], samples_raw=[samples_raw[len(samples_raw) - 1]])

        errors += calc_errors(channels, start_channel=channels[0])
        n_tested += len(channels)

    return errors, errors / n_tested, n_tested