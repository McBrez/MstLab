# importing the required module
import matplotlib.pyplot as plt 
import sqlite3
import datetime

dbConnection = sqlite3.connect("\\\\128.130.46.28\\daqpi\\MstLab\\Sentinel\\sentinelDb.sl3")
cursor = dbConnection.execute("SELECT name FROM sqlite_master WHERE type='table';")

tables = []
for table in cursor:
    tables.append(table[0])

for table in tables:
    c = dbConnection.cursor()
    result = dbConnection.cursor().execute("SELECT * FROM " + table + " WHERE idx < 1000000 ORDER BY idx ASC")
    x = [] 
    y = []
    startTimestamp = result[0][1]
    startTimestampstr = datetime.fromtimetamp(startTimestamp).isoformat()
    for row in result:
        curTimestamp = row[1] - startTimestamp
        x.append(curTimestamp)
        y.append(row[2])
    
    average = sum(y) / len(y)
    print("Average of " + table + ": " + str(average))
    # plotting the points  
    plt.plot(x, y) 
  
    # naming the x axis 
    plt.xlabel('Time (s)') 
    # naming the y axis 
    plt.ylabel('value (V)') 

    plt.title(table + " started at " + startTimestampstr) 

    # function to show the plot 
    plt.show() 