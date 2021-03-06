"""
This program has been created as part of the "Mikrosystemtechnik Labor" lecture 
at the "Institut für Sensor und Aktuator Systeme" TU Wien.
This is the main class of the project, which instatiates all necessary sub 
modules and handles communication between them.

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
import signal

class Sentinel:

    # The name of the config file, that gets read in at start up.
    CONFIG_FILE_NAME = "sentinelConfig.json"

    def __init__(self, configFile):
        """
        Initializes the object. The object has then to be started with main().

        Paramterers:
        configFile (string): Path to the XML config file.
        """

        # Declare project object.
        self.configFile = configFile
        self.configObject = None
        self.databaseInterface = None
        self.dataAquisition = None
        self.gpioHandler = None

        # Declare additional objects.
        self.manager = None
        self.dbIfQueue = None
        self.gpioQueue = None
        return

    def main(self):
        """
        Main method of the class. Starts the sentinel and all of its sub
        modules.
        """

        # Deactivate signal handler, so spawned processes dont inherit it. 
        # This is necessary, to be able to shutdown gracefully on a SIGINT.
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

        # Init sync manager for managed queue.
        self.manager = Manager()

        # Init queue for communication between DataAcquisition and 
        # DatabaseInterface module.
        self.dbIfQueue = self.manager.Queue()

        # Init queue for communication between DataAcquisition and 
        # GpioHandler module.
        self.gpioQueue = self.manager.Queue()

        # Parse XML configuration file into a DataAquisitionConfig object.
        self.configObject = SentinelConfig(self.configFile)
        if(not self.configObject.isValid()):
            print("Could not read configuration file. Aborting.")
            return

        # Start database interface
        self.databaseInterface = DatabaseInterface(
            self.configObject,
            self.dbIfQueue)

        if(not self.databaseInterface.start()):
            print("Could not start database interface. Aborting.")
            return

        # Start GPIO handler.
        self.gpioHandler = GpioHandler(
            self.configObject,
            self.gpioQueue)
        if(not self.gpioHandler.start()):
            print(
                "Could not start GpioHandler. Probably configuration specified "
                "in the configuration file is invalid. Aborting.")
            return

        # Start data aquisition thread.
        self.dataAquisition = DataAquisition(
            self.configObject,
            self.dbIfQueue,
            self.gpioQueue)
        self.dataAquisition.start()

        # Reactivate signal handler for SIGINT
        signal.signal(signal.SIGINT, original_sigint_handler)

        # Waiting for STRG + C.
        print("Sentinel started. Press STRG + C to stop.")
        try:
            input()
        except KeyboardInterrupt:
            print("Sentinel stop issued.")

        # Stop all modules.
        self.dataAquisition.stop()
        self.databaseInterface.stop()
        self.manager.shutdown()
        self.gpioHandler.stop()
        print("Sentinel has stopped.")

if __name__ == '__main__':
    mainClass = Sentinel(Sentinel.CONFIG_FILE_NAME)
    mainClass.main()
