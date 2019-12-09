"""
This program has been created as part of the MST lab lecture of  the institute of micromechanics 
TU Wien.
This script encapsulates the configuration of the sentinel and provides functions for reading in 
an XML file, containing inital configuration.

Author: David FREISMUTH
Date: DEC 2019
License: 
"""

import xml.etree.ElementTree as ET
import os

class SentinelConfig:

    # The XML tag, that specifies the database name.
    XML_DATABASE_NAME = "./DatabaseConfig/DatabaseName"

    # The XML tag, that specifies the databse buffer size.
    XML_DATABASE_BUFFER_SIZE = "./DatabaseConfig/AquisitionBufferSize"

    # The XML tag, that specifies database storageIntervall
    XML_DATABASE_STORAGE_INTERVALL = "./DatabaseConfig/DatabaseWriteIntervall"
    
    # The XML tag, that specifies the Xpath to MeasurementConfig tag.
    XML_MEASUREMENT_CONFIG = "./MeasurementConfig"

    # The XML tag, that specifies the Xpath to Measurement tag.
    XML_MEASUREMENT = "Measurement"

    # The XLM tag, that specifies the channel tag.
    XML_MEASUREMENT_TAG = "./MeasurementConfig/Measurement/Channel/" 

    def __init__(self, configFileName):
        """
        Reads in the XML file given with configFileName, and constructs the SentinelConfig object
        accordingly.

        Parameters:
        configFileName (string): Path to the XML file, containing initial config for the sentinel.
        """

        # Check if file exists.
        if(not os.path.isfile(configFileName)):
            self.__valid = False
            return
        
        # Read in the configuration tree from the XML file.
        tree = ET.parse(configFileName)

        # Write it to object, if read was successfull
        if(not tree):
            self.__valid = False
        
        self.__configTree = tree.getroot()
        self.__valid = True

    def isValid(self):
        """
        Returns wether this SentinelConfig object is valid or not.

        Returns:
        Boolean, signaling whether this object is valid, or not.
        """

        return self.__valid

    def getConfigTree(self):
        """
        Returns the configuration tree, parsed by this object, provided this object is valid.

        Returns:
        An configuration tree, if this object is valid. None otherwise.
        """

        if(self.__valid):
            return self.__configTree
        else:
            return None