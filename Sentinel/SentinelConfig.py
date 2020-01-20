"""
This program has been created as part of the MST lab lecture of the institute
of micromechanics TU Wien.
This script encapsulates the configuration of the sentinel and provides 
functions for reading in an JSON file, containing inital configuration.

Author: David FREISMUTH
Date: DEC 2019
License: 
"""
# Python imports
import json
import os
import copy

class SentinelConfig:
    """
    Encapsulates configuration data. Exposes functions for reading in a
    configurations file and retrieving configuration data.
    """

    # Points to the root element of the Database configuration. Will return
    # a dictionary containing the databse configurations.
    JSON_DATABASE_CONFIG = "DatabaseConfig"

    # The name of the database file, that will be created/connected to on
    # startup.
    JSON_DATABASE_NAME = "DatabaseName"

    # The size of the acquisition buffer.
    JSON_ACQUISITION_BUFFER = "AcquisitionBufferSize"

    # How often the value cache is written back to database. Value is in 
    # milli seconds.
    JSON_WRITE_INTERVALL = "WriteIntervall"

    # Points to the Measurement configurations. Will return a list of
    # dictionraries, containing measurement configurations.
    JSON_MEASUREMENT_CONFIG = "MeasurmentConfig"

    # The name of the measurment configuration.
    JSON_MEASUREMENT_NAME = "ConfigName"

    # The channels of the DAQ hardware, that shall be used. returns a 
    # dictionary, that maps from channel number to channel tag.
    JSON_MEASUREMENT_CHANNELS = "Channels"

    # The rate with which the values shall be sampled.
    JSON_MEASUREMENT_SCANRATE = "ScanRate"

    # Specifies the state of the GPIO output pin, if a specific measurment 
    # configuration is active.
    JSON_MEASUREMENT_OUT_STATE = "OutputState"

    # Contains the measurements that shall be done. The results of these
    # measurements will be written to database. Returns a dictionary where
    # the keys are user defined names of the measurments. The values are 
    # mathematical expressions, that state how the value of the measuremnt 
    # shall be calculated from the values that have been read from the 
    # DAQ card. The mathematical expressions have to be given as a string,
    # that is parseable by the praser.eval() python function. The Variables 
    # in this expression are the channel names, defined via the 
    # JSON_MEASUREMENT_CHANNELS configuration.
    JSON_MEASUREMENTS = "Measurements" 

    # Dictionary that contains information on how the measurement shall be
    # controlled.    
    JSON_MEAS_CONTROL = "MeasurementControl"
    
    # A list of GPIO pin numbers that specifies which measurement configuration
    # shall be active.
    JSON_MEAS_CONTROL_SEL = "MeasConfigSelectionGpio"

    # A integer that specifies a GPIO pin, that assumes a state corresponding to
    # the currently active measurement configuration.
    JSON_MEAS_CONTROL_OUTPUT = "MeasConfigOutputGpio"

    # An integer, that specifies the intervall, in which the measurment 
    # configuration is changed. Intepreted as in seconds.
    JSON_MEAS_CONTROL_SWITCH_INT = "MeasConfSwitchTimer"

    def __init__(self, configFileName):
        """
        Reads in the JSON file given with configFileName, and constructs the 
        SentinelConfig object accordingly.

        Parameters:
        configFileName (string): Path to the JSON file, containing initial 
        config for the sentinel.
        """

        # Check if file exists.
        if not os.path.isfile(configFileName):
            self.__valid = False
            return

        # Read the JSON file into a dict.
        jsonFilePtr = open(configFileName, 'r')
        self.__configDict = json.load(jsonFilePtr)

        if self.__configDict != None:
            self.__valid = True
        else:
            self.__valid = False

    def isValid(self):
        """
        Returns wether this SentinelConfig object is valid or not.

        Returns:
        Boolean, signaling whether this object is valid, or not.
        """

        return self.__valid

    def getConfig(self, configDomain):
        """
        Returns a configuration data according to the configDomain parameter.

        Parameters:
        configDomain (string): Specifies of what configuration domain the data
        shall be retrieved. Can be one of the following: 
            JSON_DATABASE_CONFIG: A dict containing the database 
            configuration will be returned.

            JSON_MEASUREMENT_CONFIG: A list containing dicts with Measurement
            configuration will be returned

            JSON_MEAS_CONTRO: A dictionary of measurement control information.

        Returns:
        A deep copy of the configuration object.

        Throws:
        Exception: When this object has not initialized correctly.
        ValueError: When configDomain is not a valid configuration key.
        """

        # Check wether this object contains valid values.
        if not self.__valid:
            raise Exception("Config object does not contain valid values.")


        if configDomain == SentinelConfig.JSON_DATABASE_CONFIG:
            return copy.deepcopy(self.__configDict[configDomain])
        elif configDomain == SentinelConfig.JSON_MEASUREMENT_CONFIG:
            return copy.deepcopy(self.__configDict[configDomain])
        elif configDomain == SentinelConfig.JSON_MEAS_CONTROL:
            return copy.deepcopy(self.__configDict[configDomain])
        else:
            # Invalid config key has been passed. Raise ValueError.
            raise ValueError("Invalid configuration key.")