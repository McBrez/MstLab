
# Introduction
This program has been created as part of the "Mikrosystemtechnik Labor" lecture 
at the "Institut für Sensor und Aktuator Systeme" TU Wien.
The purpose of this program is to acquire measurement samples, store them in a database and to 
provide a way to configure multiple measurement configurations. The python script `Sentinel.py` (resides in the folder `Sentinel/`) implements these requirements. It is supposed to be executed on a Raspberry Pi with an [MCC118](https://www.mccdaq.de/DAQ-HAT/MCC-118.aspx) DAQ extension hat.
The configuration is done in the sentinelConfig.json file. See section "Configuration" for details. 

The multiple database files, that are created by the Sentinel script can be examined with the `Observer/testPlot.py` script.


# Installation
1. Download and install the MCC118 python library from [here](https://www.mccdaq.de/daq-software/DAQ-HAT-Library.aspx).
2. Execute following shell commands:
```
sudo apt-get update
sudo apt-get upgrade
pip3 install RPi.GPIO
```

# Configuration
The behaviour of `Sentinel/Sentinel.py` can be configured through the `Sentine/sentinelConfig.json` file. The following section 
shows a valid configuration: 

```json
{
    "DatabaseConfig" : {
        "DatabaseName" : "sentinelDb.sl3",
        "ChangeIntervall" : 100,
        "WriteIntervall" : 10000
    },
    "MeasurmentConfig" : [
        {
            "ConfigName" : "Config1",
            "Channels" : {
                "0" : "UR1"
            },
            "ScanRate" : 100000,
            "Measurements" : {
                "CurrentShunt" : "UR1"
            },
            "OutputState" : false 
        },
        {
            "ConfigName" : "Config2",
            "Channels" : {
                "0" : "UR3",
                "1" : "UR4"
            },
            "ScanRate" : 50000,
            "Measurements" : {
                "Meas11" : "UR3 - UR4"
            },
            "OutputState" : true 
        }
    ],
    "MeasurementControl" : {
        "MeasConfSwitchTimer" : 10,
        "MeasConfigOutputsGpio" : [29,31,32,33]
    }
} 
```

* **DatabaseConfig**
	Dictionary containing database specific configuration.

* **ChangeIntervall**
    The Intervall in write cycles, until the database file gets changed. If set 
    to 0, database files will not get changed.

* **DatabaseName**
	The base name of the database file, without file ending. The single database
    files will be named in the format DatabaseName_Timestamp.
	
* **WriteIntervall**
	Interval in Milliseconds, the script shall write back to the database.
	
* **MeasurmentConfig**
	List containing one or more measurement configurations.

* **ConfigName**
	The name of the measurement configuration. The name of the SQL table corresponding to this measurement configuration will be derived from this name. The format is <ConfigName>_<MeasurementName>.
 
* **Channels**
	Dictionary containing the mapping from DAQ channels to tag name. The keys of this dictionary is a string containing a single number (the channel number). The corresponding value is a user defined tag name. 

* **ScanRate**
	The desired sample rate of the DAQ card.
	
* **Measurements**
	Dictionary containing the different measurements. The key is the name of the measurement. This name is used in the name of SQL table the measurement values get written to. The format is <ConfigName>_<MeasurementName>. The values of this dictionary contain a mathematical expression, that will be evaluated on each acquired value from the DAQ card. In this expression, the tags defined in the "Channels" dictionary can be used.

* **OutputState** 
	Defines the state of the GPIOs of the Raspberry Pi, when this measurment configuration is active. 
	
* **MeasurementControl**
	Dictionary containing measurement control specific configuration.
	
* **MeasConfSwitchTimer**
	Intervall in seconds, the script shall switch through the measurement configurations.
	
* **MeasConfigOutputsGpio**
	List that defines the GPIOs that serve as output state. Always has to contain 4 values. Note that there are different port [numbering schemes](https://www.raspberrypi.org/documentation/usage/gpio/) on the raspberry pi. In this list, the board numbering scheme is used, rather than the gpio numbering.
	
# Usage 
Usage consists of two phases: First the Sentinel script is started, to gather data. Secondly, the data may be analyzed by the testPlot script.
## Sentinel
To run the data acquisition script `Sentinel/Sentinel.py`, just execute the following via the sehll:
```
python3 Sentinel.py 
```
The programm is stopped by hitting STRG+C _once_. Hitting it multiple times may corrupt the most recent database file. It may take some time until the script really stops, as it is waited for the database to close.
## TestPlot
To do evaluation of the acquired data run the following:
```
python3 testPlot.py -f <base name of database files> 
```
This loads all databases and tries to display the data that is contained in them. The parameter after `-f` is mostly equal to the value that has been chosen for `databaseName` in the `sentinelConfig.json` file. A path might have to be added, if the databases are not in the same directory as the testPlot script.
Example: If the database files look like this:
```
sentinelDb_2020-02-04T18-05-54.sl3
sentinelDb_2020-02-04T18-06-20.sl3
sentinelDb_2020-02-04T18-06-47.sl3
```
The -f parameter has to look like this:
```
sentinelDb
```

# Contact
David Freismuth, Matr. Nr. 1326907
e1326907@student.tuwien.ac.at
