import time
from pandas import read_csv
import numpy
from src.lib.dbinit import connect

def readData(filename):
    data = read_csv(filename, sep=",")
    return numpy.array(data)

def insert(fileName, Insertor):
    start = time.time()
    ## data read
    data = readData(fileName)

    ## connect to sql server
    positiondb = connect()
    #
    ## data preparation
    insertor = Insertor()
    tableName = insertor.type
    vals = insertor.convert(data)
    # return vals
    ## data insertion
    insertStart = time.time()
    insertor.insert(positiondb, vals)
    positiondb.close()

    # time test
    print("Total time: ", time.time()-start)
    print("Insertion time: ", time.time()-insertStart)