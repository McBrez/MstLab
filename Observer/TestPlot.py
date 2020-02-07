"""
This program has been created as part of the MST lab lecture of the institute
of micromechanics TU Wien.
This script shows the data that has been acquired by Sentinel.py. It is assumed,
that all analyzed database, have the same scheme.

Parameter:

-f, --fileBaseName: The base name of the file, that shall be analyzed. Do not
enter file ending. Defaults to the following:
\\\\raspberrypi.local\\daqpi\\MstLab\\Sentinel\\sentinelDb

Author: David FREISMUTH
Date: DEC 2019
License: 
"""

# Python imports
import sqlite3
import datetime
import argparse
import matplotlib.pyplot as plt 
import glob
import os

# CONSTANTS --------------------------------------------------------------------

# File ending of sqlite database files.
SQLITE_FILE_ENDING = ".sl3"

# The default name of sqlite database files. Will be used, if script has been
# called without -f option.
DEFAULT_FILE_BASE_NAME = \
    "\\\\raspberrypi.local\\daqpi\\MstLab\\Sentinel\\sentinelDb"

# The column index of the timestamp in the databases.
IDX_DB_TIMESTAMP = 0

# The column index of the value in the databases.
IDX_DB_VALUE = 1

# MAIN -------------------------------------------------------------------------

# Set up argparse.
parser = argparse.ArgumentParser(
    description="Shows data that has been acquired by Sentinel.")
parser.add_argument(
    '--fileBaseName', '-f',
    dest='fileBaseName',
    action='store',
    nargs = '?',
    default=DEFAULT_FILE_BASE_NAME,
    help=
    'The base name of the file, that shall be analyzed. Do not enter file ending')
args = parser.parse_args()

# Get a list of all database file that match to the specified database file 
# base name
fileNamePattern = args.fileBaseName + "_*" + SQLITE_FILE_ENDING
dbFileList = glob.glob(fileNamePattern)

# Sort the dbFileList after modification time.
dbFileListSorted = \
    sorted(
        dbFileList,
        key = lambda dbFile: os.path.getctime(dbFile))

# Iterate over detected database files.
corruptFileCounter = 0
firstIteration = True
startTimestamp = 0.0
startTimestampStr = ""
fig = None
axs = None
for dbFile in dbFileListSorted:
    try:
        dbConnection = sqlite3.connect(dbFile)
    except:
        # Database file seems to be corrupted. Skip this one.
        corruptFileCounter += 1
        continue
    
    # Get all tables from the database
    cursor = \
        dbConnection.execute(
            "SELECT name FROM sqlite_master WHERE type='table';")
    tables = []
    for table in cursor:
        tables.append(table[0])

    # If this is the first file, set up the plots according to the discovered
    # tables in the database.
    if firstIteration:
        fig,axs = plt.subplots(len(tables), sharex = True, sharey=True)
        for i, table in enumerate(tables):
            axs[i].set_title(table)
            axs[i].set_ylabel('Voltage (V)')

    # Iterate over the tables in the current database.
    for i, table in enumerate(tables):
        c = dbConnection.cursor()
        result = \
            dbConnection.cursor().execute(
                "SELECT * FROM " + table + " ORDER BY timestamp ASC")
        x = [] 
        y = []

        # Iterate over rows in the table.
        for row in result:
            # If this is the first row of the first table of the first file, 
            # save the timestamp, to be able to subract it from all future
            # timestamps.
            if firstIteration:
                startTimestamp = row[IDX_DB_TIMESTAMP]
                startTimestampStr = \
                    datetime.datetime.fromtimestamp(
                        row[IDX_DB_TIMESTAMP]).isoformat()
                firstIteration = False

            curTimestamp = row[IDX_DB_TIMESTAMP] - startTimestamp
            x.append(curTimestamp)
            y.append(row[IDX_DB_VALUE])
        
        # plotting the points  
        axs[i].plot(x, y, 'b') 
    
    # Close connection to currently analyzed database.
    dbConnection.close()

# Print some information.
if corruptFileCounter > 1:
    print(
        str(corruptFileCounter) + " of " + str(len(dbFileList)) + " database " +
        "files where corrupted. Data of those will not be shown.")
print(
    "Showing data of " + str(len(dbFileList) - corruptFileCounter) + " " +
    "files.")

# Do some final configurations on the figure and then show it.
fig.suptitle(
    'Energy Harvesting measurement started at ' + startTimestampStr,
    fontsize=16)
axs[-1].set_xlabel('Time (s)')
plt.show() 