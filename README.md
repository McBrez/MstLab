# Introduction
This program has been created as part of the micro system lab lecture at the "Institut für Sensor- 
und Aktuatorsysteme" TU Wien.
The purpose of this program is to acquire measurment samples, store them in a database and to 
provide a way to configure multiple measurment configurations, The python script "Sentinel.py" 
is supposed to be executed on a Raspberry Pi with a [MCC118](https://www.mccdaq.de/DAQ-HAT/MCC-118.aspx) DAQ extension hat.
The configuration is done in the sentinelConfig.json file. See section "Configuration" for details. 

# Installation
1. Download and install the MCC118 python library from [here](https://www.mccdaq.de/daq-software/DAQ-HAT-Library.aspx).
2. Execute following shell commands:
```
sudo apt-get update
sudo apt-get upgrade
pip3 install RPi.GPIO
```

# Configuration
The behaviour of the script can be configured through the sentinelConfig.json file. The following
shows a valid configuration: 

```json
{
    "DatabaseConfig" : {
        "DatabaseName" : "sentinelDb.sl3",
        "AcquisitionBufferSize" : 300,
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
        "MeasConfigSelectionGpio" : [3],
        "MeasConfigOutputGpio" : 7
    }
} 
```



# Contact
David Freismuth, Matr. Nr. 1326907
e1326907@student.tuwien.ac.at