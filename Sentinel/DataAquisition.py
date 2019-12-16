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
            self.__configObject.getConfig(
                SentinelConfig.JSON_MEASUREMENT_CONFIG)
        
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

        self.__runThread = True

        # Get constant for single shot read.
        options = OptionFlags.DEFAULT

        # Get current measurement configuration and some values out of it.
        self.__activeMeasConfig = self.__getMeasConfig()
        readIntervall = \
            self.__activeMeasConfig[SentinelConfig.JSON_MEASUREMENT_SCANRATE]
        calculations = \
            self.__activeMeasConfig[SentinelConfig.JSON_MEASUREMENTS]
        measurementConfigName = \
            self.__activeMeasConfig[SentinelConfig.JSON_MEASUREMENT_NAME]

        # Convert from milli seconds to seconds.
        readIntervall = readIntervall / 1000.0

        # Write configured channel numbers from configuration into 
        # channelNums
        channelNums = []
        channelDict = \
            self.__activeMeasConfig[SentinelConfig.JSON_MEASUREMENT_CHANNELS]
        for channel in channelDict.keys():
            channelNums.append(int(channel))

        # Get an instance of the selected hat device object.
        address = select_hat_device(HatIDs.MCC_118)
        hat = mcc118(address)

        # Measurement Loop.
        channelValues = {}
        while self.__runThread:

            # Construct timestamp.
            timestamp = datetime.now().isoformat()
         
            # Read a single value from each configured channel.
            channelValues.clear()
            for chan in channelNums:
                channelTag = channelDict[str(chan)]
                channelValues[channelTag] = hat.a_in_read(chan, options)

            # Execute configured measurement calculations.
            for name, expr in calculations.items():
                # Evaluate expression
                value = self.__doCalculation(expr, channelDict, channelValues)
                
                # Hand calculated value over to database interface.
                measurementName = \
                    measurementConfigName + "_" + name
                valueCache = dict([(timestamp,value)])
                self.__storeFunc(measurementName, valueCache)

            # Wait the configured interval between reads.
            sleep(readIntervall)

    def __getMeasConfig(self):
        """
        Reads RasPi GPIO inputs to determine the active measurment 
        configuration.

        Returns:
        A dict representing the measurment configuration.
        """

        # Currently only returns the first measurment configuration.
        return self.__measurementConfig[0]

    def changeMeasConfig(self, measConfIdx):
        """
        Triggered by an RasPi GPIO value change. Changes the measurement
        configuration accordingly.

        measConfIdx (integer): The index of the measurement configuration, that
        shall be changed to.
        """

        # TODO:
        pass

    def stop(self):
        """
        Stops the worker loop after completing one last worker loop iteration.
        """

        self.__runThread = False
        return

    def __doCalculation(self, expr, channelDict, channelValues):
        """
        Replaces the channel tags in the mathematial expression expr with 
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

        