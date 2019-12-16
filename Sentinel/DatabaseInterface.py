"""
This program has been created as part of the MST lab lecture of  the institute
of micromechanics TU Wien.
This script encapsulates an scqlite database to achieve data persistence. It 
also exposes an store function, that can be called by the data aquisition 
module, that allows to dump the measurment values.

Author: David FREISMUTH
Date: DEC 2019
License: 
"""

# Python imports
import sqlite3
from string import Template
import threading
import time

# Project imports
from SentinelConfig import SentinelConfig

class DatabaseInterface:

    # Template for query that creates tables for measurements.
    CREATE_QUERY = Template( \
        "CREATE TABLE IF NOT EXISTS $tableName " \
        "(idx INTEGER PRIMARY KEY,"
        "timestamp TEXT, " \
        "value REAL NOT NULL)" )

    # Template for query that inserts measurement values.
    VALUE_INSERT_QUERY = Template( \
        "INSERT INTO $tableName (timestamp, value) "
        "VALUES $valueList" )

    def __init__(self, configObject):
        """
        Constructs the database interface. Does not create a database or connect
        to it. Before this object is operational, and data can be written to the
        database, start() function has to be called.

        Parameters:
        configObject (SentinelConfig): The configuration data is extracted from
        this object.
        """
        
        # Get main configuration domains
        self.databaseConfig = configObject.getConfig(
            SentinelConfig.JSON_DATABASE_CONFIG)
        self.measurementConfig = configObject.getConfig(
            SentinelConfig.JSON_MEASUREMENT_CONFIG)

        # Extract configuration data from databaseConfig.
        self.databaseName = \
            str(self.databaseConfig[SentinelConfig.JSON_DATABASE_NAME])
        self.bufferSize = \
            int(self.databaseConfig[SentinelConfig.JSON_ACQUISITION_BUFFER])
        self.storageIntervall = \
            int(self.databaseConfig[SentinelConfig.JSON_WRITE_INTERVALL])
        
        # Set up worker thread.
        self.__workerThread = threading.Thread(
            group = None,
            target = self.__workerWriteback,
            name = 'databaseInterfaceWorker',
            daemon = None)
        
        # A semaphore is needed, to avoid race conditions when this object is
        # trying to write back to databse, and another module is adding values
        # to the value cache.
        self.__writeSemaphore = threading.Semaphore(value = 1)

        # Boolean that signals wether this object is connected to a database.
        self.__connected = False

        # The database connection.
        self.dbConnection = None

        # Values will be written to this dict from other objects.
        # DatabaseInterface will write the contents of valueCache back to 
        # database, if the configured write intervall elapsed. 
        self.valueCache = {}

        # Controlls the worker loop.
        self.__runThread = False
    
    def start(self):
        """
        Creates the database structure or connects to it, and starts worker 
        threads.

        Returns:
        True if start was successfull. False otherwise.
        """

        # Only start, if not already started.
        if(self.__connected):
            return False
        
        # Start worker thread.
        self.__runThread = True
        self.__workerThread.start()
        return True

        
    def stop(self):
        """
        Closes the database interface.

        Returns:
        True is stopped successfully. False otherwise.
        """

        self.__runThread = True
        self.__workerThread.join()
        self.dbConnection.close()    
        

    def storeFunction(self, measurement, value):
        """
        Used to queue measurement values for storage to database.

        Parameters:
        
        measurement (string): A name to uniquely identify the meaurement. 
        Is also the name of the SQL table the values are written to. As such, 
        measurement should comply with SQL syntax rules.

        values: (dict<string,float>): A dictionary, that contains timestamp, 
        value tuples.
        """

        # Aquire lock
        self.__writeSemaphore.acquire()
        
        # Add dict to valueCache, if not already in valueCache
        if measurement not in self.valueCache.keys():
            self.valueCache[measurement] = {}
        
        self.valueCache[measurement].update(value)

        # Everything has been done. Releae lock.
        self.__writeSemaphore.release()

        return

    def __workerWriteback(self):
        """
        Worker function, that creates database structure according to 
        configuration, and then continuously executes the write back of the 
        value cache to the databse.
        """
        # Try to establish connection to databse.
        try:
            self.dbConnection = sqlite3.connect(self.databaseName)
        except:
            self.__connected = False
            return False

        # Create database structure
        c = self.dbConnection.cursor()

        # Create a table for each Measurement and MeasurementConfig
        for measurementConf in self.measurementConfig:
            measConfigName = \
                str(measurementConf[SentinelConfig.JSON_MEASUREMENT_NAME])
            measurements = \
                measurementConf[SentinelConfig.JSON_MEASUREMENTS]

            # Iterate over measurements.
            for measurementName in measurements.keys():
                # Build table name from MeasurementConfig name + Measurement 
                # name.
                tableName = measConfigName + "_" + str(measurementName)
                query = \
                    DatabaseInterface.CREATE_QUERY.substitute(
                        tableName = tableName)
                c.execute(query)

        # Enter writeback loop.
        while(self.__runThread):
            # Call __writeback every storageIntervall milliseconds.
            time.sleep(self.storageIntervall/1000.0)
            self.__writeback()

    def __writeback(self):
        """
        Writes value cache to the database.
        """
        # Do nothing, if no values are in the cache.
        if(len(self.valueCache)):       
            # Aquire lock, so valueTriple is ensured to not change.
            self.__writeSemaphore.acquire()

            # Iterate over valueCache to build the SQL statments.
            for tableName, valueDict in self.valueCache.items():
                # Build value list for SQL query.
                valueListStr = ""
                firstIteration = True
                for timestamp, value in valueDict.items():
                    # Do not add comma on first iteration of loop
                    if(firstIteration):
                        valueListStr += "('" + timestamp + "', " + str(value) + ")"
                        firstIteration = False
                    else:
                         valueListStr += ",('" + timestamp + "', " + str(value) + ")"

                insertQuery = \
                    DatabaseInterface.VALUE_INSERT_QUERY.substitute(
                        tableName = tableName,
                        valueList = valueListStr)
                self.dbConnection.cursor().execute(insertQuery)

            # Clear value cache
            self.valueCache = {}

            # Commit changes to DB and release semaphore.
            self.dbConnection.commit()
            self.__writeSemaphore.release()