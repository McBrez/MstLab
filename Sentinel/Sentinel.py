"""
This program has been created as a part of the MST lab lecture. 

Author: David FREISMUTH
Date: DEC 2019
"""

# Project imports
from SentinelConfig import SentinelConfig
from DatabaseInterface import DatabaseInterface
from DataAquisition import DataAquisition

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

        self.configFile = configFile
        self.configObject = None
        self.databaseInterface = None
        self.dataAquisition = None
        return

    def main(self):
        """
        Main method of the class. Starts the sentinel and all of its sub 
        modules.
        """

        # Parse XML configuration file into a DataAquisitionConfig object.
        self.configObject = SentinelConfig(self.configFile)
        if(not self.configObject.isValid()):
            print("Could not read configuration file. Aborting.")
            return     

        # Start database interface
        self.databaseInterface = DatabaseInterface(
            self.configObject.getConfig(SentinelConfig.JSON_DATABASE_CONFIG))

        if(not self.databaseInterface.start()):
            print("Could not start database interface. Aborting.")
            return

        # Start data aquisition thread.
        self.dataAquisition = DataAquisition(
            configTree,
            self.databaseInterface.storeFunction)
        self.dataAquisition.start()

        # Start networking

        # Endless loop

if __name__ == '__main__':
    mainClass = Sentinel(Sentinel.CONFIG_FILE_NAME)
    mainClass.main()