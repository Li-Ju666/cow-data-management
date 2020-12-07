# -*- coding: utf-8 -*-
import numpy as np
import datetime as dt

"""
This method reads an "Avkastn" file to list of tuples (cow_id, date, produced volume).
The method is based on an assumption of overlapping data, only extracting 
entry akt 23456 8, translating to akt=mon, - ,sat, fri, thu, wed, tue, - ,sun.  

NEEDS TO BE REVIEWED - PER IS CHECKING WITH FARMERS

"""

def readAvkastfile(textfile, first_upload=False):
    #add date 0 2345 7 each time
    #exception first time upload?
    #1st time Pattern: mon, - ,sat, fri, thu, wed, tue, - , sun, sat, fri, thu, wed, tue, mon, sun, sat
    #other Pattern: mon, - ,sat, fri, thu, wed, tue, - ,sun 
    
    
    textfile_arr = textfile.split()
    date_str = textfile_arr[3]
    year = int("20" + date_str[0:2])
    month = int(date_str[2:4])
    day = int(date_str[4:6])
    
    tuple_list = []

    if not first_upload:
        #Currently assuming no data is missing
        array = np.genfromtxt(textfile, dtype=None,  skip_header=4, skip_footer=5, missing_values='missing', autostrip=True)
        for arr in array:
            cow_id = arr[0]
            delay = [0, 2, 3, 4, 5, 6, 8]
            for i in range(7):
                d = dt.datetime(year,month,day) - dt.timedelta(days=delay[i])
                tuple_list.append((str(cow_id),str(d),str(arr[i+3])))
    
    else: 
        array = np.genfromtxt(textfile, dtype=None,  skip_header=4, skip_footer=5, missing_values='missing', autostrip=True)
        for arr in array:
            cow_id = arr[0]
            delay = [0, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16]
            for i in range(15):
                d = dt.datetime(year,month,day) - dt.timedelta(days=delay[i])
                tuple_list.append((str(cow_id),str(d),str(arr[i+3])))
    return tuple_list


"""
This method takes a "Mjölkplats yymmdd" file and transforms it into a list of tuple entries
containting (cow, date time, milking place). The status of a cow decides how the data is treated:

SINLD - The first consequtive morning milkings are matched to monday/wednesday/friday, the rest is not saved.
TIDIG - The data is checked for shifted (morning/evening) data. If the data is shifted, elements after the shift is skipped.
ALL OTHERS - Handled as "TIDIG", but rows with missing entries are skipped.

SUGGESTION: Include Avkast file in the method to match the data with date-time. For this, we must understand the file.

"""
def readMjolkplatsfile(textfile, avkfile=None):
    #Save file date
    textfile_arr = textfile.split()
    date_str = textfile_arr[1]
    year = int("20" + date_str[0:2])
    month = int(date_str[2:4])
    day = int(date_str[4:6])

    #Read lines, ignoring å ä ö
    file1 = open(textfile,'r', errors='ignore')
    lines = file1.readlines()
    file1.close()

    #Read avkastn file
    # 1. Read file
    # 2. Check what cows are relavent
    #avk_array = np.genfromtxt(textfile, dtype=None,  skip_header=4, skip_footer=5, missing_values='missing', autostrip=True)



    n_max = len(lines)-6
    n_line = 0

    #Use only wanted rows (skip 5 first and 5 last)
    #Creating list of cow_dicts with info + array
    tuple_list = []

    for line in lines:
        if (n_line > 4 and n_line < n_max):
            entry_list = line.split()
            cow_id = int(entry_list[0])
            status = entry_list[1]
            dim = int(entry_list[2])    #DIM not interesting?
            data = entry_list[3:]       #Get milking data in list
            milk_info_input = []        #List/array to upload

            missing = False             #not used
            wrong_order = False         #not used
            #CHECK THE DATA AND SET MISSING/WRONG_ORDER TRUE
            #Check status
            
            if (status == "SINLD"): #Skip cows marked as dried off (status is updated when done milking)
                """
                dryoff_time = dt.datetime(year,month,day) - dt.datetime(2020,9,1) #REPLACE WITH ACTUAL DRY-OFF DATE
                if (dt.timedelta(days=7) > dryoff_time):
                    # For SINLD cows we adjust milking timestamps to morning milkings
                    # on monday, wednesday and friday. 
                    milkPlace = True
                    sinld = True
                    sinldShift = 0 # Shift days caused by SINLD-scheme
                    delay = 0.5
                    for elem in data:
                        if milkPlace:
                            mp = elem
                            milkPlace = False
                        else:
                            #Split timestamp into hours & minutes
                            split_str = elem.split(':')
                            #For the period of the cow being SINLD, data are recorded for
                            #monday, wednesday and friday
                            if sinld: #perhaps irrelavent/redundant
                                if (int(split_str[0]) < 12):
                                    if (sinldShift%7 == 0):
                                        d = dt.datetime(year,month,day) - dt.timedelta(days=sinldShift)
                                        t = dt.time(int(split_str[0]),minute=int(split_str[1]))
                                        milktime = dt.datetime.combine(d.date(),t)
                                        milkPlace = True
                                        tuple_list.append((str(cow_id),str(milktime), str(mp)))
                                        sinldShift += 3
                                    elif (sinldShift%7 == 3):
                                        d = dt.datetime(year,month,day) - dt.timedelta(days=sinldShift)
                                        t = dt.time(int(split_str[0]),minute=int(split_str[1]))
                                        milktime = dt.datetime.combine(d.date(),t)
                                        milkPlace = True
                                        tuple_list.append((str(cow_id),str(milktime), str(mp)))
                                        sinldShift += 2
                                    elif (sinldShift%7 == 5):
                                        d = dt.datetime(year,month,day) - dt.timedelta(days=sinldShift)
                                        t = dt.time(int(split_str[0]),minute=int(split_str[1]))
                                        milktime = dt.datetime.combine(d.date(),t)
                                        milkPlace = True
                                        tuple_list.append((str(cow_id),str(milktime), str(mp)))
                                        sinldShift += 2
                                    else:
                                        print("SINLD-shifting encountered an error")
                                else:
                                    #If the cow is no longer considered SINLD, then we
                                    #cannot match a milking to a date.
                                    sinld = False
                                    break
                else:
                    print(str(cow_id) + " not valid, since dryoff-date long ago")
                """
                n_line += 1
                continue
            elif (status == "TIDIG"):
                milkPlace = True
                delay = 0.5
                newRecords = []
                if not (len(data)==30):
                    for elem in data:
                        if milkPlace:
                            mp = elem
                            milkPlace = False
                        else:
                            #Split timestamp into hours & minutes
                            split_str = elem.split(':')

                            #Check for shifted values
                            if (delay%1 == 0):
                                if (int(split_str[0]) < 12):
                                    #print("small forbidden time value:",elem,"for TIDIG cow",cow_id)
                                    break
                            else:
                                if (int(split_str[0]) > 12):
                                    #print("large forbidden time value:",elem,"for TIDIG cow",cow_id)
                                    break
                            
                            #Construct timestamp, counting backwards for date
                            #and reading timestamp for time.
                            d = dt.datetime(year,month,day) - dt.timedelta(days=np.floor(delay))
                            t = dt.time(int(split_str[0]),minute=int(split_str[1]))
                            milktime = dt.datetime.combine(d.date(),t)
                            newRecords.append((str(cow_id),str(milktime), str(mp)))
                            delay += 0.5
                            milkPlace = True
                    tuple_list.extend(newRecords) #Add non-shifted entries to list   

                else:
                    for elem in data[:-2]:
                        if milkPlace:
                            mp = elem
                            milkPlace = False
                            newRecords = []
                        else:
                            #Split timestamp into hours & minutes
                            split_str = elem.split(':')

                            #Check for shifted values
                            if (delay%1 == 0):
                                if (int(split_str[0]) < 12):
                                    #print("small forbidden time value:",elem,"for TIDIG cow",cow_id)
                                    break
                            else:
                                if (int(split_str[0]) > 12):
                                    #print("large forbidden time value:",elem,"for TIDIG cow",cow_id)
                                    break
                            
                            #Construct timestamp, counting backwards for date
                            #and reading timestamp for time.
                            d = dt.datetime(year,month,day) - dt.timedelta(days=np.floor(delay))
                            t = dt.time(int(split_str[0]), minute=int(split_str[1]))
                            milktime = dt.datetime.combine(d.date(),t)
                            newRecords.append((str(cow_id),str(milktime), str(mp)))
                            delay += 0.5
                            milkPlace = True
                    tuple_list.extend(newRecords) #If no data was shifted, add to list 
            elif (status == "DRKT"):
                #Check for 2-3 initial morning milkings -> assume to be dried off
                milkPlace = True
                delay = 0.5
                entry_index = 0
                sinld = False 
                newRecords = []
                if not (len(data)==30):
                    continue #If not full columns, skip cow data assuming something's wrong
                for elem in data[:-2]:
                    if milkPlace:
                        mp = int(elem)
                        milkPlace = False
                    else:
                        
                        #Split time into hours & minutes
                        split_str = elem.split(':')

                        #Check for shifted values
                        if (delay%1 == 0):
                            if (int(split_str[0]) < 12):
                                #print("small forbidden time value:",elem,"for cow",cow_id)
                                if (entry_index == 1):
                                    sinld = True
                                else:
                                    break
                        else:
                            if (int(split_str[0]) > 12):
                                #print("large forbidden time value:",elem,"for cow",cow_id)
                                break

                        if (sinld):
                            #Construct timestamp, counting backwards for date
                            #following the dry-off scheme for a maximum of 3 entries
                            if (entry_index == 1):
                                d = dt.datetime(year,month,day) - dt.timedelta(days=3)
                                t = dt.time(int(split_str[0]),minute=int(split_str[1]))
                                milktime = dt.datetime.combine(d.date(),t)
                                newRecords.append((str(cow_id),str(milktime), str(mp)))
                                delay += 0.5
                                milkPlace = True 
                            elif (entry_index == 2):
                                d = dt.datetime(year,month,day) - dt.timedelta(days=5)
                                t = dt.time(int(split_str[0]),minute=int(split_str[1]))
                                milktime = dt.datetime.combine(d.date(),t)
                                newRecords.append((str(cow_id),str(milktime), str(mp)))
                                delay += 0.5
                                milkPlace = True 
                            else:
                                break

                        else:
                            #Construct timestamp, counting backwards for date
                            #and reading timestamp for time.
                            d = dt.datetime(year,month,day) - dt.timedelta(days=np.floor(delay))
                            t = dt.time(int(split_str[0]),minute=int(split_str[1]))
                            milktime = dt.datetime.combine(d.date(),t)
                            newRecords.append((str(cow_id),str(milktime), str(mp)))
                            delay += 0.5
                            milkPlace = True
                        entry_index += 1
                tuple_list.extend(newRecords) #Add non-shifted data to list
            else:
                milkPlace = True
                delay = 0.5
                newRecords = []
                if not (len(data)==30):
                    continue #If not full columns, skip cow data assuming something's wrong
                for elem in data[:-1]:
                    if milkPlace:
                        mp = int(elem)
                        milkPlace = False
                    else:
                        #Split time into hours & minutes
                        split_str = elem.split(':')
                        
                        #Check for shifted values
                        if (delay%1 == 0):
                            if (int(split_str[0]) < 12):
                                #print("small forbidden time value:",elem,"for cow",cow_id)
                                break
                        else:
                            if (int(split_str[0]) > 12):
                                #print("large forbidden time value:",elem,"for cow",cow_id)
                                break
                            
                        #Construct timestamp, counting backwards for date
                        #and reading timestamp for time.
                        d = dt.datetime(year,month,day) - dt.timedelta(days=np.floor(delay))
                        t = dt.time(int(split_str[0]),minute=int(split_str[1]))
                        milktime = dt.datetime.combine(d.date(),t)
                        newRecords.append((str(cow_id),str(milktime), str(mp)))
                        delay += 0.5
                        milkPlace = True
                tuple_list.extend(newRecords) #Add non-shifted data to list 
        n_line += 1 #Count rows in for loop
    return tuple_list
 
    

a = readAvkastfile('Avkastn 14 dag 200907.txt') #, first_upload=True) First file uploaded? set true to upload all entries
c = readMjolkplatsfile('Mjölkplats 200907.txt')
for i in range(len(c)):
    print(c[i])