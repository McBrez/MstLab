"""
This program has been created as a part of the MST lab lecture.

Author: David FREISMUTH
Date: DEC 2019
"""

# Project imports
from SentinelConfig import SentinelConfig
from DatabaseInterface import DatabaseInterface
from DataAquisition import DataAquisition
from GpioHandler import GpioHandler

# Python imports
from multiprocessing import Manager, queues

class Sentinel:

    # The name of the config file, that gets read in at start up.
    CONFIG_FILE_NAME = "sentinelConfig.json"

    def __init__(self, configFile):
        """
        Stores the paths of the XML config file and the name of the SQLite
        database file. Does not start the object.

        Paramterers:
        configFile (string): Path to the XML config file.
        databaseFile (string): Name of the SQlite databse file that shall be
        created.
        """

        # Declare project object.
        self.configFile = configFile
        self.configObject = None
        self.databaseInterface = None
        self.dataAquisition = None
        self.gpioHandler = None

        # Declare additional objects.
        self.manager = None
        self.commQueue = None
        return

    def main(self):
        """
        Main method of the class. Starts the sentinel and all of its sub
        modules.
        """

        # Init sync manager for managed queue.
        self.manager = Manager()

        # Init queue for communication between DataAcquisition and 
        # DatabaseInterface module.
        self.commQueue = self.manager.Queue()

        # Parse XML configuration file into a DataAquisitionConfig object.
        self.configObject = SentinelConfig(self.configFile)
        if(not self.configObject.isValid()):
            print("Could not read configuration file. Aborting.")
            return

        # Start database interface
        self.databaseInterface = DatabaseInterface(
            self.configObject,
            self.commQueue)

        if(not self.databaseInterface.start()):
            print("Could not start database interface. Aborting.")
            return

        # Start data aquisition thread.
        self.dataAquisition = DataAquisition(
            self.configObject,
             self.commQueue)
        self.dataAquisition.start()

        # Start GPIO handler.
        self.gpioHandler = GpioHandler(
            self.configObject,
            self.dataAquisition.changeMeasConfig)
        self.gpioHandler.start()

        # Waiting for STRG + C.
        print("Sentinel started. Press STRG + C to stop.")
        try:
            input()
        except KeyboardInterrupt:
            print("Sentinel stop issued.")

        # Stop all modules.
        self.databaseInterface.stop()
        self.dataAquisition.stop()
        self.gpioHandler.stop()
        print("Sentinel has stopped.")

if __name__ == '__main__':
    mainClass = Sentinel(Sentinel.CONFIG_FILE_NAME)
    mainClass.main()
