"""
	MCC 118 Functions Demonstrated:
		mcc118.a_in_scan_start
		mcc118.a_in_scan_read
		mcc118.a_in_scan_stop
	Purpose:
		Performs a finite acquisition on 1 or more channels.
	Description:
		Continuously acquires blocks of analog input data for a
		user-specified group of channels until the acquisition is
		stopped by the user.  The last sample of data for each channel
		is displayed for each block of data received from the device.
"""

# Python imports
from __future__ import print_function
from sys import stdout
from time import sleep
import threading
from datetime import datetime

# MC118 imports
from daqhats import mcc118, OptionFlags, HatIDs, HatError
from daqhats_utils import select_hat_device, enum_mask_to_string,\
     chan_list_to_mask

# Project imports
from SentinelConfig import SentinelConfig

class DataAquisition(threading.Thread):
    """
    Encapsulates the data aquisition functions. Inherits from threading.Thread, 
    so the aquisition can run parallely in a separate thread.

    Instance Attributes:
        scanConfig(DataAquisitionConfig): Stores the configuration of the data 
        aquisition.
    """

    READ_ALL_AVAILABLE = -1
    CURSOR_BACK_2 = '\x1b[2D'
    ERASE_TO_END_OF_LINE = '\x1b[0K'

    def __init__(self, configObject, storeFunc):
        """
        Constructor, that copies the contents of configObject into the 
        DataAquisition object and registers the storage function that is used
        to pass the measured valus to database interface.

        parameters:
            configObject (DataAquisitionConfig): Contains the configuration for 
            creation of this object.
            storeFunc ((void)(storeObj)): A refernce to function, that is called
            to store the aquired data. The store function should return nothing,
            and take a storeObj. 
        """

        # Call constructor of super class.
        threading.Thread.__init__(self)

        # Load configuration objects.
        self.__configObject = configObject
        self.__measurementConfig = \
            self.configObject.getConfig(SentinelConfig.JSON_MEASUREMENT_CONFIG)
        
        # Set the storage function.
        self.__storeFunc = storeFunc

        # Init value cache
        self.__valueCache = {}  

        # Flag that indicates, that the worker thread loop shall be executed.
        self.__runThread = False 

        # The active measurement configuration. Is set on start of worker 
        # thread.
        self.__activeMeasConfig = {}

    def run(self):
        """
        Worker function, that can be called as thread. Initializes measurement
        config and contains measurment loop.  
        """

        # Get constant for single shot read.
        options = OptionFlags.DEFAULT

        # Get current measurement configuration and some values out of it.
        self.__activeMeasConfig = self.__getMeasConfig()
        readIntervall = \
            self.__activeMeasConfig[SentinelConfig.JSON_MEASUREMENT_SCANRATE]
        # Convert from milli seconds to seconds.
        readIntervall = readIntervall / 1000.0

        # Get channels
        channelNums = []
        channelKeys = \
            self.__activeMeasConfig[SentinelConfig.JSON_MEASUREMENT_CHANNELS]\
                .keys()
        for channel in channelKeys:
            channelNums.append(int(channel))

        # Get an instance of the selected hat device object.
        address = select_hat_device(HatIDs.MCC_118)
        hat = mcc118(address)

        while self.__runThread:
            # Construct timestamp.
            
            
            # Read a single value from each selected channel.
            for chan in channelNums:
                
                value = hat.a_in_read(chan, options)



            # Wait the configured interval between reads.
            sleep(readIntervall)

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
        read_request_size = DataAquisition.READ_ALL_AVAILABLE

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

                timestamp = datetime.now().isoformat()
                valueCache = {}
                valueCache[timestamp] = read_result.data[index]
                self.storeFunc('TestConfig_TestMeasurement1', valueCache)
                sleep(0.1)

        print('\n')

    def __getMeasConfig(self):
        """
        Reads RasPi GPIO inputs to determine the active measurment 
        configuration.

        Returns:
        A dict representing the measurment configuration.
        """

        # Currently only returns the first measurment configuration.
        return self.__measurementConfig[0]

    def __changeMeasConfig(self):
        """
        Triggered by an RasPi GPIO value change. Changes the measurement
        configuration accordingly.
        """

        # TODO:
        pass

    def stop(self):
        """
        Stops the worker loop after completing one last worker loop iteration.
        """

        self.__runThread = False
        return