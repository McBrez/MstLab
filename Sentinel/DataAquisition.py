"""
	MCC 118 Functions Demonstrated:
		mcc118.a_in_scan_start
		mcc118.a_in_scan_read
		mcc118.a_in_scan_stop
	Purpose:
		Performa a finite acquisition on 1 or more channels.
	Description:
		Continuously acquires blocks of analog input data for a
		user-specified group of channels until the acquisition is
		stopped by the user.  The last sample of data for each channel
		is displayed for each block of data received from the device.
"""
from __future__ import print_function
from sys import stdout
from time import sleep
from daqhats import mcc118, OptionFlags, HatIDs, HatError
from daqhats_utils import select_hat_device, enum_mask_to_string, chan_list_to_mask
import threading

class DataAquisition(threading.Thread):
    """
    Encapsulates the data aquisition functions. Inherits from threading.Thread, so the aquisition
    can run parallely in a separate thread.

    Instance Attributes:
        scanConfig(DataAquisitionConfig): Stores the configuration of the data aquisition.
    """

    READ_ALL_AVAILABLE = -1
    CURSOR_BACK_2 = '\x1b[2D'
    ERASE_TO_END_OF_LINE = '\x1b[0K'

    def __init__(self, configObject, storeFunc):
        """
        Constructor, that copies the contents of configObject into the DataAquisition object.

        parameters:
            configObject (DataAquisitionConfig): Contains the configuration for creation of this 
            object.
            storeFunc ((void)(storeObj)): A refernce to function, that is called to store the 
            aquired data. The store function should return nothing, and take a storeObj. 
        """
        threading.Thread.__init__(self)
        self.scanConfig = configObject
        self.storeFunc = storeFunc

    def run(self):
        """
        Worker function, that can be called as thread. 
        """
        # Store the channels in a list and convert the list to a channel mask that
        # can be passed as a parameter to the MCC 118 functions.
        channel_mask = chan_list_to_mask(self-scanConfig.channels)
        num_channels = len(self.scanConfig.channels)

        try:
            # Select an MCC 118 HAT device to use.
            address = select_hat_device(HatIDs.MCC_118)
            hat = mcc118(address)

            print('\nSelected MCC 118 HAT device at address', address)

            actual_scan_rate = hat.a_in_scan_actual_rate(num_channels, self.scanConfig.scanRate)

            print('\nMCC 118 continuous scan example')
            print('    Functions demonstrated:')
            print('         mcc118.a_in_scan_start')
            print('         mcc118.a_in_scan_read')
            print('         mcc118.a_in_scan_stop')
            print('    Channels: ', end='')
            print(', '.join([str(chan) for chan in self.scanConfig.channels]))
            print('    Requested scan rate: ', self.scanConfig.scanRate)
            print('    Actual scan rate: ', actual_scan_rate)
            print('    Options: ', enum_mask_to_string(OptionFlags, self.scanConfig.scanMode))

            # Configure and start the scan.
            # Since the continuous option is being used, the samples_per_channel
            # parameter is ignored if the value is less than the default internal
            # buffer size (10000 * num_channels in this case). If a larger internal
            # buffer size is desired, set the value of this parameter accordingly.
            hat.a_in_scan_start(
                channel_mask,
                self.scanConfig.samples_per_channel,
                self.scanConfig.scanRate,
                self.scanConfig.scanMode)

            print('Starting scan ... Press Ctrl-C to stop\n')

            # Display the header row for the data table.
            print('Samples Read    Scan Count', end='')
            for ~, item in enumerate(self.scanConfig.channels):
                print('    Channel ', item, sep='', end='')
            print('')

            try:
                self.__read_and_display_data(hat, num_channels)

            except KeyboardInterrupt:
                # Clear the '^C' from the display.
                print(CURSOR_BACK_2, ERASE_TO_END_OF_LINE, '\n')
        except (HatError, ValueError) as err:
            print('\n', err)

    def __read_and_display_data(self, hat, num_channels):
    """
    Reads data from the specified channels on the specified DAQ HAT devices
    and updates the data on the terminal display.  The reads are executed in a
    loop that continues until the user stops the scan or an overrun error is
    detected
    Args:
        hat (mcc118): The mcc118 HAT device object.
        num_channels (int): The number of channels to display.
    Returns:
        None
    """
    total_samples_read = 0
    read_request_size = READ_ALL_AVAILABLE

    # When doing a continuous scan, the timeout value will be ignored in the
    # call to a_in_scan_read because we will be requesting that all available
    # samples (up to the default buffer size) be returned.
    timeout = 5.0

    # Read all of the available samples (up to the size of the read_buffer which
    # is specified by the user_buffer_size).  Since the read_request_size is set
    # to -1 (READ_ALL_AVAILABLE), this function returns immediately with
    # whatever samples are available (up to user_buffer_size) and the timeout
    # parameter is ignored.
    while True:
        read_result = hat.a_in_scan_read(read_request_size, timeout)

        # Check for an overrun error
        if read_result.hardware_overrun:
            print('\n\nHardware overrun\n')
            break
        elif read_result.buffer_overrun:
            print('\n\nBuffer overrun\n')
            break

        samples_read_per_channel = int(len(read_result.data) / num_channels)
        total_samples_read += samples_read_per_channel

        # Display the last sample for each channel.
        print('\r{:12}'.format(samples_read_per_channel),
              ' {:12} '.format(total_samples_read), end='')

        if samples_read_per_channel > 0:
            index = samples_read_per_channel * num_channels - num_channels

            for i in range(num_channels):
                print('{:10.5f}'.format(read_result.data[index+i]), 'V ',
                      end='')
            stdout.flush()

            sleep(0.1)

    print('\n')