"""
This program has been created as part of the MST lab lecture of the institute
of micromechanics TU Wien.
This script encapsulates the configuration of the sentinel and provides 
functions for reading in an JSON file, containing inital configuration.

Author: David FREISMUTH
Date: DEC 2019
License: 
"""

import json
import os

class SentinelConfig:
    """
    Encapsulates configuration data. Exposes functions for reading in a
    configurations file and retrieving configuration data.
    """

    # Containts configuration keys and their representation in the JSON 
    # configuration file. At __init__() of this object, the keys and their
    # valus will be written as instance attributes to this object. 
    __CONFIG_KEY_DICT = {
        # Points to the root element of the Database configuration. Will return
        # a dictionary containing the databse configurations.
        "JSON_DATABASE_CONFIG" : "DatabaseConfig",

        # The name of the database file, that will be created/connected to on
        # startup.
        "JSON_DATABASE_NAME" : "DatabaseName",

        # The size of the acquisition buffer.
        "JSON_ACQUISITION_BUFFER" : "AcquisitionBufferSize",

        # How often the value cache is written back to database. Value is in 
        # milli seconds.
        "JSON_WRITE_INTERVALL" : "WriteIntervall",

        # Points to the Measurement configurations. Will return a list of
        # dictionraries, containing measurement configurations.
        "JSON_MEASUREMENT_CONFIG" : "MeasurmentConfig",

        # The name of the measurment configuration.
        "JSON_MEASUREMENT_NAME" : "ConfigName",

        # The channels of the DAQ hardware, that shall be used. returns a 
        # dictionary, that maps from channel number to channel tag.
        "JSON_MEASUREMENT_CHANNELS" : "Channels",

        # The rate with which the values shall be sampled.
        "JSON_MEASUREMENT_SCANRATE" : "ScanRate",

        # Contains the measurements that shall be done. The results of these
        # measurements will be written to database. Returns a dictionary where
        # the keys are user defined names of the measurments. The values are 
        # mathematical expressions, that state how the value of the measuremnt 
        # shall be calculated from the values that have been read from the 
        # DAQ card. The mathematical expressions have to be given as a string,
        # that is parseable by the praser.eval() python function. The Variables 
        # in this expression are the channel names, defined via the 
        # JSON_MEASUREMENT_CHANNELS configuration.
        "JSON_MEASUREMENTS" : "Measurements" 
    }
   
    def __init__(self, configFileName):
        """
        Reads in the JSON file given with configFileName, and constructs the 
        SentinelConfig object accordingly.

        Parameters:
        configFileName (string): Path to the JSON file, containing initial 
        config for the sentinel.
        """

        # Check if file exists.
        if(not os.path.isfile(configFileName)):
            self.__valid = False
            return

        # Parse __CONFIG_KEY_DICT into instance attributes.
        for key, value in __CONFIG_KEY_DICT.items():
            self.key = value

        # Read the JSON file into a dict.
        jsonFilePtr = open(configFileName, 'r')
        self.configDict = json.load(jsonFilePtr)

        if self.configDict != None:
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

    def getConfig(self, configKey):
        """
        Returns configuration data, specified by configKey. configKey can be 
        one of the JSON_* constants of SentinelConfig.

        Parameters:
        configKey (string): Specifies what configuration data should be 
        retrieved. Can be one of the JSON_* constants of SentinelConfig.

        Returns:
        The configuration data specified by configKey. None if the configuration
        could not be found.

        Throws:
        Exception: When the requested configuration data should be present, but
        was missing in the JSON config file.
        """

        # Check if configKey is a known configuration key.
        configFound = False

        if configKey == SentinelConfig.JSON_DATABASE_CONFIG:
            if SentinelConfig.JSON_DATABASE_CONFIG in self.__configDict.keys():
                retVal = self.__configDict[configKey]
                configFound = True

        elif configKey == SentinelConfig.JSON_DATABASE_NAME:
            if SentinelConfig.JSON_DATABASE_NAME in self.__configDict.keys():
                retVal = self.__configDict[configKey]
                configFound = True      

        elif configKey == SentinelConfig.JSON_ACQUISITION_BUFFER:

        elif configKey == SentinelConfig.JSON_WRITE_INTERVALL:

        elif configKey == SentinelConfig.JSON_MEASUREMENT_CONFIG:

        elif configKey == SentinelConfig.JSON_MEASUREMENT_NAME:

        elif configKey == SentinelConfig.JSON_MEASUREMENT_CHANNELS:

        elif configKey == SentinelConfig.JSON_MEASUREMENT_SCANRATE:
        
        elif configKey == SentinelConfig.JSON_MEASUREMENTS:

        else:
            # Unknown configuration key.
            retVal = None