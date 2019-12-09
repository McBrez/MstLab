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
        Constructs the database interface. Does not create a database or connect to it. Before this
        object is operational, and data can be written to the database,  start() function has to be
        called.

        Parameters:
        configObject (SentinelConfig): Holds the configuration of for the database interface.
        """
        
        self.configObject = configObject
        self.databaseName = \
            str(configObject.findtext(SentinelConfig.XML_DATABASE_NAME))
        self.bufferSize = \
            int(configObject.findtext(SentinelConfig.XML_DATABASE_BUFFER_SIZE))
        self.storageIntervall = \
            int(configObject.findtext(SentinelConfig.XML_DATABASE_STORAGE_INTERVALL))
        
        self.__workerThread = threading.Thread(
            group = None,
            target = self.__workerWriteback,
            name = 'databaseInterfaceWorker',
            daemon = None)
        
        self.__writeSemaphore = threading.Semaphore(value = 1)
        self.__connected = False
        self.dbConnection = None
        self.valueCache = {}
    
    def start(self):
        """
        Creates the database structure or connects to it, and starts worker threads.

        Returns:
        True if start was successfull. False otherwise.
        """

        # Only start, if not already started.
        if(self.__connected):
            return False
        
        # Start worker thread.
        self.__workerThread.start()
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

        # Aquire lock
        self.__writeSemaphore.acquire()
        self.valueCache.append(values)
        
        # Everything has been done. Releae lock.
        self.__writeSemaphore.release()

        return

    def __workerWriteback(self):
        """
        Worker function, that continuously calls a writeback function.
        """
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
            measConfigName = measurementConf.attrib['name']
            measurements = measurementConf.findall(SentinelConfig.XML_MEASUREMENT)

            # Iterate over measurements.
            for measurement in measurements:
                # Build table name from MeasurementConfig name + Measurement name.
                measName = measurement.attrib['name']
                tableName = measConfigName + "_" + measName
                query = DatabaseInterface.CREATE_QUERY.substitute(tableName = tableName)
                c.execute(query)

        # Enter writeback loop.
        while(True):
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

    def addTestData(self):
        self.valueCache["TestConfig_TestMeasurement1"] = {}
        self.valueCache["TestConfig_TestMeasurement1"]["someTimeStamp1"] = 1.1
        self.valueCache["TestConfig_TestMeasurement1"]["someTimeStamp2"] = 2.2

        self.valueCache["TestConfig_TestMeasurement2"] = {}
        self.valueCache["TestConfig_TestMeasurement2"]["someTimeStamp1"] = 3.3
        self.valueCache["TestConfig_TestMeasurement2"]["someTimeStamp2"] = 3.3