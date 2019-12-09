"""
This program has been created as part of the MST lab lecture of  the institute of micromechanics 
TU Wien.
This script encapsulates an scqlite database to achieve data persistence. It also exposes an store 
function, that can be called by the data aquisition module, that allows to dump the measurment 
values.

Author: David FREISMUTH
Date: DEC 2019
License: 
"""

# Python imports
import sqlite3
from string import Template
import threading.threading

# Project imports
from SentinelConfig import SentinelConfig

class DatabaseInterface:

    # Template for query that creates tables for measurements.
    CREATE_QUERY = Template( \
        "CREATE TABLE IF NOT EXISTS $tableName " \
        "(timestamp TEXT PRIMARY KEY, " \
        "value REAL NOT NULL)" )

    # Template for query that inserts measurement values.
    VALUE_INSERT_QUERY = Template( \
        "INSERT INTO $tableName " \
        "(timestamp TEXT PRIMARY KEY, " \
        "value REAL NOT NULL)" )

    def __init__(self, configObject):
        """
        Constructs the database interface. Does not create a database or connect to it. Before this
        object is operational, and data can be written to the database,  start() function has to be
        called.

        Parameters:
        configObject (SentinelConfig): Holds the configuration of for the database interface.
        """
        
        self.configObject = configObject
        self.databaseName = \
            configObject.findtext(SentinelConfig.XML_DATABASE_NAME)
        self.bufferSize = \
            configObject.findtext(SentinelConfig.XML_DATABASE_BUFFER_SIZE)
        self.storageIntervall = \
            configObject.findtext(SentinelConfig.XML_DATABASE_STORAGE_INTERVALL)
        
        self.__connected = False
        self.dbConnection = None
        self.valueCache = []
        return
    
    def start(self):
        """
        Creates the database structure or connects to it, and starts worker threads.

        Returns:
        True if start was successfull. False otherwise.
        """

        # Only start, if not already started.
        if(self.__connected):
            return False

        # Try to establish connection to databse.
        try:
            # self.dbConnection = sqlite3.connect(self.databaseName)
            self.dbConnection = sqlite3.connect(self.databaseName)
        except:
            self.__connected = False
            return False

        # Create database structure
        c = self.dbConnection.cursor()

        # Create a table for each Measurement and MeasurementConfig
        measConfigTree = \
            self.configObject.findall(SentinelConfig.XML_MEASUREMENT_CONFIG)

        # Iterate over measurement configurations
        for measurementConf in measConfigTree:
            # Build table name from MeasurementConfig name + Measurement name.
            measConfigName = measurementConf.attrib['name']
            measurements = measurementConf.findall(SentinelConfig.XML_MEASUREMENT)

            # Iterate over measurements.
            for measurement in measurements:
                measName = measurement.attrib['name']
                tableName = measConfigName + "_" + measName
                query = DatabaseInterface.CREATE_QUERY.substitute(tableName = tableName)
                c.execute(query)
        

        return True

        
    def stop(self):
        """
        Closes the database interface.

        Returns:
        True is stopped successfully. False otherwise.
        """
        return False

    def storeFunction(self, values):
        """
        Used to queue measurement values for storage to database.

        Parameters:
        values: Immutable list of triples. The first value of the tuple 
        is expected to be a timestamp in the format XXX. THe second value should
        be the measurement tag. The third is the measurement value.
        """

        self.valueCache.append(values)

        return

    def workerWriteback(self):
        """
        Worker function, that is run in a separate thread and writes the value
        cache back to database.
        """

        while True:
            # Do nothing, if no values are in the cache.
            if(len(self.valueCache)):       
                #Lock threads 
                for valueTriple in self.valueCache:
                    pass