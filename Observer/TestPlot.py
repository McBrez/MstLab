# importing the required module
import matplotlib.pyplot as plt 
import sqlite3
import datetime

dbConnection = sqlite3.connect("\\\\raspberrypi.local\\daqpi\\MstLab\\Sentinel\\sentinelDb.sl3")
cursor = dbConnection.execute("SELECT name FROM sqlite_master WHERE type='table';")

tables = []
for table in cursor:
    tables.append(table[0])

fig,axs = plt.subplots(len(tables), sharex = True, sharey=True)
firstTable = True
startTimestamp = 0.0
startTimestampStr = ""
for i, table in enumerate(tables):
    c = dbConnection.cursor()
    result = dbConnection.cursor().execute("SELECT * FROM " + table + " ORDER BY timestamp ASC")
    x = [] 
    y = []

    for row in result:
        if firstTable:
            startTimestamp = row[1]
            startTimestampStr = \
                datetime.datetime.fromtimestamp(row[1]).isoformat()
            firstTable = False

        curTimestamp = row[1] - startTimestamp
        x.append(curTimestamp)
        y.append(row[2])
    
    if(len(y) == 0):
        print ("table has no data. Skipping this one.")
        continue
    
    average = sum(y) / len(y)
    print("Average of " + table + ": " + str(average))
    # plotting the points  
    axs[i].plot(x, y) 
  
    # # naming the x axis 
    # axs[i].xlabel('Time (s)') 
    # # naming the y axis 
    # axs[i].ylabel('value (V)') 

    # axs[i].title(table + " started at " + startTimestampStr) 

# function to show the plot 
plt.show() 