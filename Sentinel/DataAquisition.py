"""
This program has been created as part of the "Mikrosystemtechnik Labor" lecture 
at the "Institut für Sensor und Aktuator Systeme" TU Wien.
This class handles the data acquistion via the MCC118 DAQ card. The DAQ card is
run in continuous measurement mode. A Thread, that is spawned by this class on
start(), clears the buffer of the DAQ card, and pushes the acquired values to
a multiprocessing.Pool for further processing. The processed value are then 
pushed to the database interface for storage. Also, the measurement 
configuration is handled in this module. After a specified time span has elapsed
the measurement configuration switches. A corresponding message is sent to the
GPIO handler module, that sets up the ouput accordingly.

Author: David FREISMUTH
Date: DEC 2019
License: 
"""

# Python imports
from __future__ import print_function
from time import sleep
import threading
from multiprocessing import Process, Pool
from datetime import datetime, timedelta
import parser
import signal

# MC118 imports
from daqhats import mcc118, OptionFlags, HatIDs, HatError
from daqhats_utils import select_hat_device, enum_mask_to_string,\
     chan_list_to_mask

# Project imports
from SentinelConfig import SentinelConfig

class DataAquisition:
    """
    Encapsulates the data aquisition functions.
    """

    # Contant that specifies, that all available data shall be read.
    READ_ALL_AVAILABLE = -1
    
    # Time the scan buffer is popped. In seconds.
    __SCAN_SLEEP_TIME = 0.8

    def __init__(self, configObject, dbIfQueue, gpioQueue):
        """
        Constructor, that copies the contents of configObject into the 
        DataAquisition object and registers the storage function that is used
        to pass the measured valus to database interface.

        Parameters:
            configObject (SentinelConfig): Contains the configuration for 
            creation of this object.

            dbIfQueue (Manager.Queue): Managed queue object, that is used to 
            communicate with the database interface.

            gpioQueue (Manager.Queue):  Managed queue object, that is used to 
            communicate with the GPIO module.
        """
        # Load configuration objects.
        self.__configObject = configObject
        self.__measurementConfig = \
            self.__configObject.getConfig(
                SentinelConfig.JSON_MEASUREMENT_CONFIG)
        self.__measurementControl = \
            self.__configObject.getConfig(
                SentinelConfig.JSON_MEAS_CONTROL)

        # Register worker function as Thread.
        self.__workerThread = threading.Thread(
            group = None,
            target = self.__scanningFunction,
            name = "AcquisitionThread")

        # Init Threading pool. As much processes will be spawned, as the machine
        # has CPU cores.
        self.__processingWorkerPool = Pool()

        # The time a single measurment configuration is active. After that, 
        # It gets changed to the next measurment configuration.
        self.__measConfSwitchTimerIntervall = \
            self.__measurementControl \
                [SentinelConfig.JSON_MEAS_CONTROL_SWITCH_INT] 

        # Register timer that is responsible for periodic changing of 
        # measurement configuration.
        self.__confChangeTimer = threading.Timer(
            interval = self.__measConfSwitchTimerIntervall,
            function = self.__confChangeFunc)
      
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

        # Storage dict for acquired data. Maps from timestamps to a namedtuple
        # object that contains the acquired data.
        self.__acquiredData = {}
    
        # Current scan rate.
        self.__currScanRate = 0

        # Dictionary that maps Channel number to tag name.
        self.__currChannelDict = {}

        # The queue to the dbInterface.
        self.__dbIfQueue = dbIfQueue

        # The queue to the gpio module.
        self.__gpioQueue = gpioQueue

    def start(self):
        """
        Starts the worker thread
        """

        self.__runThread = True
        self.__workerThread.start()

        # Initialize output state. 
        self.__gpioQueue.put_nowait(self.__activeMeasConfigIdx)
        
        # Only start config change time, if there are more than one 
        # configurations.
        if(len(self.__measurementConfig) > 1):
            self.__confChangeTimer.start()

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
            sample_rate_per_channel = float(self.__currScanRate),
            options = OptionFlags.CONTINUOUS)

        # Measurement loop.
        asyncResult = None
        while self.__runThread:
            # MCC118 library automatically creates a buffer for at least a 
            # second worth of samples. To leave some margin for error, the 
            # buffer is popped every 0.8 seconds.
            sleep(DataAquisition.__SCAN_SLEEP_TIME)

            # Read all available samples from all channels. Timeout is ignored.
            acquiredData = hat.a_in_scan_read(
                samples_per_channel = DataAquisition.READ_ALL_AVAILABLE,
                timeout = 0)

            # Check for an overrun error.
            if acquiredData.hardware_overrun:
                print('\n\nHardware overrun\n')
                continue
            elif acquiredData.buffer_overrun:
                print('\n\nBuffer overrun\n')
                continue

            # Get current timestamp.
            timestamp = datetime.now()

            args = (
                timestamp,
                acquiredData.data,
                self.__dbIfQueue,
                self.__currCalculations,
                self.__currMeasurementConfigName,
                self.__currChannelDict,
                self.__currScanRate) 

            # Push workload to worker pool.
            asyncResult = self.__processingWorkerPool.apply_async(
                func = DataAquisition.processingFunction,
                args = args)
       
        # Stop scanning.
        hat.a_in_scan_stop()
        hat.a_in_scan_cleanup()

    @staticmethod
    def processingFunction(
        timestamp,
        data,
        queue,
        currCalculations,
        currMeasurementConfigName,
        currChannelDict,
        currScanRate):
        """
        Worker function, that is called by __scanningFunction() as a thread, to
        trigger data processing and storage of acquired data. Data and 
        additional information is taken from the __acquiredData and
        __currScanRate instance variables. The timestamps of the single acquired
        values is reproduced by taking __currTimestamp and tracing back 
        1/__currScanRate seconds for each acquired value.

        Parameters:
        
        timestamp(datetime): Timestamp corresponding to the most recent 
        measurement in data.
        
        data(float[]): List of floats containing measurement data.

        queue(Manager.Queue): Managed queue, used for communication with 
        database interface module.

        currCalculations(dict<string,string>): Contains currently active 
        calculations
        
        currMeasurementConfigName(string): Currently active measurement name.

        currChannelDict(dict<string,string>): Currently active channel mapping.

        currScanRate(int): Currently active scan rate.
        """

        try:
            # Create resultDict, that is used as structure that is handed over
            #  to database interface. Each active calculation must exist as a 
            # key in this dict and has to point to another dict.
            resultDict = {}
            for name, expr in currCalculations.items():
                measurementName = \
                    currMeasurementConfigName + "_" + name
                resultDict[measurementName] = {}

            # Calculate offset for reconstruction of timestamps.
            offset = (1.0 / currScanRate)
            reproducedTimestamp = timestamp.timestamp()

            # Pop from acquired data, until it is empty.
            loopCount = 0
            while len(data) > 0:
                # Pop once for every configured channel. More recent values have 
                # higher indices. Values from different channels are ordered 
                # sequentially in the list. I.e for 4 channels -> 
                # [1,2,3,4,1,2,3,4,...]
                # The Values that are popped during one while loop iteration are 
                # considered as concurrent and there have the same timestamp.
                channelValues = {}
                reversedList = list(currChannelDict.values())
                reversedList.reverse()
                for chanTag in reversedList:
                    channelValues[chanTag] = data.pop()

                # Calculate timestamp for current channelValues by starting from
                # the original timestamp, and then subtracting the sample
                # intervall multiplied by the loop iteration count. Offset from 
                # the original timestamp in milliseconds.
                reproducedTimestamp = reproducedTimestamp - offset
                
                # Execute configured measurement calculations with the set of 
                # values.
                for name, expr in currCalculations.items():
                    # Evaluate expression
                    value = DataAquisition.__doCalculation(
                        expr = expr,
                        channelDict = currChannelDict,
                        channelValues = channelValues)

                    # Store calculated values in resultDict.
                    measurementName = \
                        currMeasurementConfigName + "_" + name
                    resultDict[measurementName][reproducedTimestamp] = value

                loopCount = loopCount + 1

            print("Got " + str(loopCount) + " measurements.")
            # Hand calculated and timestamped values over to database interface.
            for measName, valueDict in resultDict.items():
                queue.put_nowait((measName, valueDict))
        
        except KeyboardInterrupt:
            print("Processing worker stopped.")

    def changeMeasConfig(self, measConfIdx):
        """
        Triggered by an RasPi GPIO value change. Changes the measurement
        configuration accordingly.

        measConfIdx (integer): The index of the measurement configuration, that
        shall be changed to.
        """

        # Aquire lock.
        self.__changeMeasConfSem.acquire()

        # Stop Acquisition loop and wait until it finishes.
        self.__runThread = False
        self.__workerThread.join()
        
        if self.__workerThread.is_alive():
            # Thread is still alive, when it already should have terminated.
            # Raise an exception.
            raise Exception("DataAquisition working loop could not terminate")

        # Set new measurement configuration index.
        self.__activeMeasConfigIdx = measConfIdx
        print("Changed measurement configuration to " + str(measConfIdx))

        # Set GPIOs accordingly.
        self.__gpioQueue.put_nowait(self.__activeMeasConfigIdx)

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

        self.__confChangeTimer.cancel()
        self.__runThread = False
        self.__workerThread.join()
        self.__processingWorkerPool.terminate()

        # Put End symbol to queue
        self.__dbIfQueue.put_nowait(-1)
        print("Stopped acquisition module")

        return

    @staticmethod
    def __doCalculation(expr, channelDict, channelValues):
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

    def __confChangeFunc(self):
        """
        Worker function, that switches measurement configuration after a user 
        specified amount of time.
        """
        
        if(self.__runThread):
            # Get the count of configured measurment configurations.
            measConfCount = len(self.__measurementConfig)

            # Calculate the new measurement config index by incrementing.
            newMeasConfIdx = (self.__activeMeasConfigIdx + 1) % measConfCount

            # Trigger change of measurment configuration
            self.changeMeasConfig(newMeasConfIdx)

            # Create new Timer.
            self.__confChangeTimer = threading.Timer(
                interval = self.__measConfSwitchTimerIntervall,
                function = self.__confChangeFunc)
            
            self.__confChangeTimer.start()