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
import parser

# MC118 imports
from daqhats import mcc118, OptionFlags, HatIDs, HatError
from daqhats_utils import select_hat_device, enum_mask_to_string,\
     chan_list_to_mask

# Project imports
from SentinelConfig import SentinelConfig

class DataAquisition:
    """
    Encapsulates the data aquisition functions. Inherits from threading.Thread, 
    so the aquisition can run parallely in a separate thread.

    Instance Attributes:
        scanConfig(DataAquisitionConfig): Stores the configuration of the data 
        aquisition.
    """

    # Contant that specifies, that all available data shall be read.
    READ_ALL_AVAILABLE = -1
    CURSOR_BACK_2 = '\x1b[2D'
    ERASE_TO_END_OF_LINE = '\x1b[0K'
    
    # Time the scan buffer is popped. In seconds.
    __SCAN_SLEEP_TIME = 0.8

    def __init__(self, configObject, storeFunc):
        """
        Constructor, that copies the contents of configObject into the 
        DataAquisition object and registers the storage function that is used
        to pass the measured valus to database interface.

        Parameters:
            configObject (DataAquisitionConfig): Contains the configuration for 
            creation of this object.
            storeFunc ((void)(storeObj)): A refernce to function, that is called
            to store the aquired data. The store function should return nothing,
            and take a storeObj. 
        """

        # Register worker function as Thread.
        self.__workerThread = threading.Thread(
            group = None,
            target = self.__scanningFunction,
            name = "AcquisitionThread")

        # Register storage function as Thread.
        self.__storageThread = threading.Thread(
            group = None,
            target = self.__storageFunction,
            name = "StorageThread")

        # Load configuration objects.
        self.__configObject = configObject
        self.__measurementConfig = \
            self.__configObject.getConfig(
                SentinelConfig.JSON_MEASUREMENT_CONFIG)
        
        # Set the storage function.
        self.__storeFunc = storeFunc

        # Init value cache
        self.__valueCache = {}  

        # Flag that indicates, that the worker thread loop shall be executed.
        self.__runThread = False 

        # The active measurement configuration index.
        self.__activeMeasConfigIdx = 0

        # Stores active measurement configuration.
        self.__activeMeasConfig = []
            
        # Stores current active set of calucaltions.
        self._currCalculations = {}

        # Stores the current active measurement configuraiton name.
        self._currMeasurementConfigName = ""

        # A semaphore is needed on confugration change, so only one one call 
        # to self.changeMeasConfig() at a time is possible
        self.__changeMeasConfSem = threading.Semaphore(value = 1)

        # Storage variable for acquired data.
        self.__acquiredData = 0
    
        # Current scan rate.
        self.__currScanRate = 0.0

        # Timestamp of the last set of acquired data.
        self.__currTimestamp = datetime.now()

        # Dictionary that maps Channel number to tag name.
        self.__currChannelDict = {}

    def start(self):
        """
        Starts to worker thread
        """

        self.__runThread = True
        self.__workerThread.start()

    def __scanningFunction(self):
        """
        Worker function, that is called as thread. Initializes continuous 
        measurement, and triggers data processing and storage functions.
        """

        # Get current measurement configuration and some values out of it.
        self.__activeMeasConfig = \
            self.__measurementConfig[self.__activeMeasConfigIdx]
        self.__currScanRate = \
            self.__activeMeasConfig[SentinelConfig.JSON_MEASUREMENT_SCANRATE]
        self.__currCalculations = \
            self.__activeMeasConfig[SentinelConfig.JSON_MEASUREMENTS]
        self.__currMeasurementConfigName = \
            self.__activeMeasConfig[SentinelConfig.JSON_MEASUREMENT_NAME]

        # Write configured channel numbers from configuration into 
        # channelNums and create a mask from it.
        channelNums = []
        self.__currChannelDict = \
            self.__activeMeasConfig[SentinelConfig.JSON_MEASUREMENT_CHANNELS]
        for channel in self.__currChannelDict.keys():
            channelNums.append(int(channel))
        channel_mask = chan_list_to_mask(channelNums)

        # Get an instance of the selected hat device object.
        address = select_hat_device(HatIDs.MCC_118)
        hat = mcc118(address)

        # Cleanup scanning ressources.
        hat.a_in_scan_cleanup()

        # Trigger scanning. samples_per_channel is set to the scan rate, so 
        # buffer size is big enough to caputre one second worth of samples.
        hat.a_in_scan_start(
            channel_mask  = channel_mask,
            samples_per_channel = int(self.__currScanRate),
            sample_rate_per_channel = self.__currScanRate,
            options = OptionFlags.CONTINUOUS)

        # Measurement loop.
        while self.__runThread:
            # MCC118 library automatically creates a buffer for at least a 
            # second worth of samples. To leave some margin for error, the 
            # buffer is popped every 0.8 seconds.
            sleep(DataAquisition.__SCAN_SLEEP_TIME)

            # Read all available samples from all channels. Timeout is ignored.
            self.__acquiredData = hat.a_in_scan_read(
                samples_per_channel = DataAquisition.READ_ALL_AVAILABLE,
                timeout = 0)

            # Get current timestamp.
            self.__currTimestamp = datetime.now()

            # Redefine storage function thread object and start it.
            self.__storageThread = threading.Thread(
                group = None,
                target = self.__storageFunction,
                name = "StorageThread")     
            self.__storageThread.start()

        # Stop scanning.
        hat.a_in_scan_stop()

    def __storageFunction(self):
        """
        Worker function, that is called by __scanningFunction() as a thread, to
        trigger data processing and storage of acquired data. Data and 
        additional information is taken from the __acquiredData, 
        __currScanRate and __currTimestamp instance variables. The timestamps of
        the single acquired valus is reproduced by taking __currTimestamp and
        tracing back 1/__currScanRate seconds for each acquired value.
        """

        # Check for an overrun error
        if self.__acquiredData.hardware_overrun:
            print('\n\nHardware overrun\n')
            return
        elif self.__acquiredData.buffer_overrun:
            print('\n\nBuffer overrun\n')
            return

        # Pop from acquired data, until it is empty.
        loopCount = 0
        while len(self.__acquiredData) != 0:
            # Pop once for every configured channel. More recent values have 
            # higher indices. Values from different channels are ordered 
            # sequentially in the list. I.e for 4 channels -> 
            # [1,2,3,4,1,2,3,4,...]
            # The Values that are popped during one while loop iteration are 
            # considered as concurrent.
            channelValues = {}
            reversedList = self.__currChannelDict.values()
            reversedList.reverse()
            for chanTag in reversedList:
                channelValues[chanTag] = self.__acquiredData.data.pop()

            # Calculate timestamp for current channelVAlues by starting from the
            # original timestamp, and then subtracting the sample intervall 
            # multiplied by the loop iteration count.
            offset = (1.0 / self.__currScanRate) * loopCount
            timestampDelta = datetime.timedelta(usec = offset)
            reproducedTimestamp = self.__currTimestamp - timestampDelta

            # Execute configured measurement calculations with the set of 
            for name, expr in self.__currCalculations.items():
                # Evaluate expression
                value = self.__doCalculation(
                    expr = expr,
                    channelDict = self.__currChannelDict,
                    channelValues = channelValues)

                # Hand calculated value over to database interface.
                measurementName = \
                    self.__currMeasurementConfigName + "_" + name
                valueCache = dict([(reproducedTimestamp,value)])
                self.__storeFunc(measurementName, valueCache)

    def changeMeasConfig(self, measConfIdx):
        """
        Triggered by an RasPi GPIO value change. Changes the measurement
        configuration accordingly.

        measConfIdx (integer): The index of the measurement configuration, that
        shall be changed to.
        """

        # Aquire lock.
        self.__changeMeasConfSem.acquire()

        # Get current scan rate, before changing measurement configuration.
        scanRate = \
            self.__measurementConfig\
                [self.__activeMeasConfigIdx]\
                [SentinelConfig.JSON_MEASUREMENT_SCANRATE]

        # Set new measurement configuration index.
        self.__activeMeasConfigIdx = measConfIdx

        # Stop Acquisition loop and wait until it finishes. The timeout is 
        # generated from the currently active scanRate. If longer than 
        # 2 * scanRate is waited, an exception is raised.
        self.__runThread = False
        self.__workerThread.join(timeout = 2 * scanRate / 1000.0)
        
        if self.__workerThread.is_alive():
            # Thread is still alive, when it already should have terminated.
            # Raise an exception.
            raise Exception("DataAquisition working loop could not terminate")

        print("Changed measurement configuration to " + str(measConfIdx))

        # Restart thread.
        self.__runThread = True
        self.__workerThread = threading.Thread(
            group = None,
            target = self.__scanningFunction,
            name = "AcquisitionThread")
        self.__workerThread.start()
        print("Thread started.")

        # Release lock
        self.__changeMeasConfSem.release()

    def stop(self):
        """
        Stops the worker loop after completing one last worker loop iteration.
        """

        self.__runThread = False
        self.__workerThread.join()
        return

    def __doCalculation(self, expr, channelDict, channelValues):
        """
        Replaces the channel tags in the mathematical expression expr with 
        measurement values, given in channelValues.

        Parameters:
        
        expr (string): A mathematical expression containing channel tags.
        
        channelDict (dict<string,string>): A dictionary containing the 
        channel/channel tag association. The key is the channel number, the 
        value is the corresponding channel tag.

        channelValues (dict<string,float>) A dictionary containing the values 
        of the channels. The key is the channel tag, the value is the measured
        value of the corresponding channel.

        Returns:
        A float that represents the result of expr.
        """

        # Iterate over channelDict and try to replace channel tokens in expr
        # with the values from channelValues.
        for __, channelToken in channelDict.items():
            value = channelValues[channelToken]
            expr = expr.replace(channelToken, str(value))
        
        # Evaluate expression
        return eval(expr)
