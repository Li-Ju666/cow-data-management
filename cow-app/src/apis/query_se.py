from src.lib.dbmanager.dbinit import connect_se
import datetime
from pandas import DataFrame as df
from itertools import compress
import os
import pytz


################################# helper functions ###########################################
# return a quoted string
cur_timezone = pytz.timezone('Europe/Berlin')
def quote(x):
    return '"' + x + '"'


# function to query all cows with valid time ranges and required status
def cowQuery(cow_id, grp, stats, start_date, end_date):
    db = connect_se()

    raw_records = []
    start_date = datetime.datetime.strptime(start_date, "%y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%y-%m-%d")

    localStart = (start_date - datetime.timedelta(days=7)).strftime("%y-%m-%d")
    localEnd = end_date.strftime("%y-%m-%d")
    cur = db.cursor()

    statement = 'SELECT cowID, insertDate, stat, grp FROM CowInfo WHERE insertDate > ' + \
                quote(localStart) + ' AND insertDate <= ' + quote(localEnd)
    # print(statement)
    cur.execute(statement)
    raw_records = cur.fetchall()
    cur.close()

    # convert tuple to list
    raw_records = list(map(list, raw_records))

    # filter cow id
    if cow_id:
        raw_records = list(filter(lambda x: x[0] in cow_id, raw_records))
    # filter status
    raw_records = list(filter(lambda x: x[2] in stats, raw_records))
    # filter group
    if grp:
        raw_records = list(filter(lambda x: x[3] in grp, raw_records))

    # drop group info of all records
    raw_records = list(map(lambda x: x[:3], raw_records))

    # define function to get date intersection of valid range of record and requested date range
    def DateInsectWithRequested(x):
        x[2] = x[1] + datetime.timedelta(days=7)
        x[1], x[2] = dateIntersect(x[1], x[2], start_date.date(), end_date.date())
        return x

    #  get date intersection of valid range of record and requested date range
    raw_records = list(map(DateInsectWithRequested, raw_records))
    # for each cow, merge all requested valid days
    cow_dateRange = {}
    for record in raw_records:
        if cow_dateRange.get(record[0]):
            cow_dateRange[record[0]] += (getDays(record[1], record[2]))
        else:
            cow_dateRange[record[0]] = getDays(record[1], record[2])

    # function to generate a list of days to several ranges
    def daysToRanges(l):
        if not l:
            return []
        l = sorted(list(set(l)))
        # print(l)
        ranges = []
        step = datetime.timedelta(days=1)
        start = l[0]
        last = l[0]
        for day in l:
            if day <= last + step:
                last = day
                continue
            else:
                ranges.append([start, last])
                start = day
                last = day
        ranges.append([start, last])
        return ranges

    # dictionary: key-cowid, value-a list of ranges requested
    cow_dateRange = {k: daysToRanges(v) for k, v in cow_dateRange.items()}
    return cow_dateRange


# query tags with valid ranges
def tagQuery(cow_id, grp, stats, start_date, end_date):
    db = connect_se()
    cows = cowQuery(cow_id, grp, stats, start_date, end_date)

    # fetch reference table for tags
    results = []
    for i in cows:
        # print(cow_dateRange[i])
        statement = 'SELECT * FROM Mapping WHERE cowID = ' + str(i) + " ORDER BY startDate"
        cur = db.cursor()
        cur.execute(statement)
        refs = list(map(list, cur.fetchall()))
        # results += [tagRangeInsect(r, t) for r in cow_dateRange[i] for t in refs]
        results += refsMerge(refs)
        cur.close()
    returnValue = []
    for rec in results:
        insecStart, insecEnd = dateIntersect(datetime.datetime.strptime(start_date, "%y-%m-%d").date(),
                                             datetime.datetime.strptime(end_date, "%y-%m-%d").date(),
                                             rec[2], rec[3])
        if insecStart < insecEnd:
            returnValue.append((rec[0], rec[1], insecStart, insecEnd))
    return returnValue


def refsMerge(refs):
    tagRanges = refs
    results = []
    if tagRanges:
        cur_tag = "Init"
        for record in tagRanges:
            if record[1] != cur_tag:
                results.append(record)
                cur_tag = record[1]
            elif record[2] <= results[-1][3]:
                results[-1][3] = record[3]
            else:
                results.append(record)
            # print(results[-1], flush=True)
    return results



# get the insersection of two date ranges
def dateIntersect(start1, end1, start2, end2):
    # print(start1, end1, start2, end2)
    latest_start = max(start1, start2)
    earliest_end = min(end1, end2)
    return latest_start, earliest_end


# get all days within a data range
def getDays(start, end):
    days = []
    step = datetime.timedelta(days=1)
    current = start
    while current <= end:
        days.append(current)
        current += step
    return days


############################### Query functions #############################################
# mapping query function
def refQuery(cow_id):
    refs = tagQuery([cow_id],[], ['REDO','INSEM','DRÄKT','SKAUT','SINLD','RÅMLK','TIDIG'],
                    "00-01-01", datetime.datetime.now(cur_timezone).strftime("%y-%m-%d"))
    return list(map(lambda x: x[1:], refs))


# position query function
# arg1 = cow_id: [int], arg2 = group_no: [int], arg3 = status: [string], arg4 = position_type: [string],
# arg5 = start_date: string (yy-mm-dd), arg6 = end_date: string(yy-mm-dd), arg7 = start_time:string(hour:min:sec),
# arg8 = end_time:string(hour:min:sec), arg9 = periodic:bool
# return value: a list of tuples, each tuple is consisted of (filename, number of rows)
# TODO: add parameter before start_date -> tag_strs
def positionQuery(cow_id, grp, stats, types, tags, start_date, end_date, start_time, end_time, periodic):
    print("Position query started")
    suffix = datetime.datetime.now(cur_timezone).strftime("%Y-%m-%d-%H:%M:%S")
    path = "result_files/"
    if tags:
        start = datetime.datetime.strptime(start_date, "%y-%m-%d")
        end = datetime.datetime.strptime(end_date, "%y-%m-%d")
        tagRanges = list(map(lambda x: ("NA", x.replace(" ", ""), start, end), tags))
        print("Tag formatted")
    else:
        tagRanges = tagQuery(cow_id, grp, stats, start_date, end_date)
    queryDict = {}
    queryDict['FA'] = 'measure_time'
    queryDict['PA'] = 'start_time'
    queryDict['PAA'] = 'measure_time'
    queryDict['PC'] = 'start_time'
    db = connect_se()
    query_result = []
    for pType in types:
        num_rows = 0
        filename = pType + suffix + '.csv'
        # filenames.append(filename)
        try:
            f = open(path+filename)
            f.close()
            os.remove(path+filename)
        except IOError:
            print("No old files exist")
        if not tagRanges:
            f = open(path+filename, "w")
            f.write("No records fetched")
        else:
            f = open(path+filename, "w")
            for tag in tagRanges:
                start = tag[2].strftime("%y-%m-%d")
                end = tag[3].strftime("%y-%m-%d")
                f.write("  ".join([str(tag[0]), str(tag[1]), start, end])+"\n")
        f.close()

        for tag in tagRanges:
            start = tag[2].strftime("%y-%m-%d")
            end = tag[3].strftime("%y-%m-%d")
            if periodic:
                statement = 'SELECT * FROM ' + pType + ' WHERE tag_str = ' + quote(tag[1]) + \
                            ' AND date(' + queryDict[pType] + \
                            ') between ' + quote(start) + ' and ' + quote(end) + \
                            ' AND time(' + queryDict[pType] + \
                            ') between ' + quote(start_time) + ' and ' + quote(end_time)
            else:
                statement = 'SELECT * FROM ' + pType + ' WHERE tag_str = ' + quote(tag[1]) + \
                            ' AND ' + queryDict[pType] + \
                            ' between' + quote(start + ' ' + start_time) + ' and ' + quote(end + ' ' + end_time)
            # print(statement)
            cur = db.cursor()
            cur.execute(statement)
            tmp = cur.fetchall()
            result = list(map(lambda x: [tag[0]] + list(x), tmp))
            data = df(result)
            if data.empty:
                continue
            else:
                num_rows += len(data.index)
                data.to_csv(path+filename, index=False, header=False, mode='a')
        query_result.append((filename, num_rows)) #list of tupile
    return query_result


########### info query function #################

# arg1 = cow_id: [int], arg2 = group_no: [int], arg3 = status: [string]
# arg4 = start_date: string (yy-mm-dd), arg5 = end_date: string(yy-mm-dd)
# arg6 = fields: [string] - ["stat", "lakt", ...]
# args7 = dateType: Int

def infoQuery(cow_id, grp, stats, start_date, end_date, fields, type):
    print("Info query started", flush=True)
    path = "result_files/"
    suffix = datetime.datetime.now(cur_timezone).strftime("%Y-%m-%d-%H:%M:%S")
    db = connect_se()

    # function to get statement for each type
    def getStatement(type, start, end):
        if type == 0:
            statement = "SELECT * FROM CowInfo WHERE "\
                        "insertDate between " + quote(start) + " and " + quote(end)
        elif type == 1:
            statement = "SELECT * FROM CowInfo" + \
                        " INNER JOIN HealthInfo ON CowInfo.cowID = HealthInfo.cowID" \
                        " AND CowInfo.insertDate = HealthInfo.insertDate" + \
                        " WHERE HealthInfo.insertDate between " + quote(start) + " and " + quote(end)
            return statement
        else:
            statement = "SELECT * FROM CowInfo" + \
                        " INNER JOIN InsemInfo ON CowInfo.cowID = InsemInfo.cowID" \
                        " AND CowInfo.insertDate = InsemInfo.insertDate" + \
                        " WHERE InsemInfo.insertDate between " + quote(start) + " and " + quote(end)
        return statement
    start_date = datetime.datetime.strptime(start_date, "%y-%m-%d")

    start_date = (start_date - datetime.timedelta(days=7)).strftime("%y-%m-%d")
    statement = getStatement(type, start_date, end_date)
    cur = db.cursor()
    cur.execute(statement)
    results = cur.fetchall()
    cur.close()

    # results = list(map(list, results))
    if cow_id:
        results = list(filter(lambda x: x[0] in cow_id, results))
    if grp:
        results = list(filter(lambda x: x[3] in grp, results))
    results = list(filter(lambda x: x[4] in stats, results))
    allfields = ["cowID", "insertDate", "resp", "grp", "stat", "lakt", "kalvn_date"]
    fieldnames = [[], ["cowID", "insertDate", "7dag", "100dag", "handelse_day", "comments"],
                  ["cowID", "insertDate", "gp", "avsinad", "insem_date", "sedan_insem", "insem_tjur", "forv_kalvn", "tid_ins",
                   "tid_mellan"]]
    fieldnames = list(map(lambda x: allfields + x, fieldnames))
    mask = [True, True] + fields + [False] + [True] * 20
    fieldnames = list(compress(fieldnames[type], mask))

    def filterAndTrans(x):
        x = list(compress(x, mask))
        x = [a.strftime("%y-%m-%d") if isinstance(a, datetime.date) else a for a in x]
        return x

    requested = list(map(filterAndTrans, results))
    prefix = ["info", "health", "insem"]
    filename = prefix[type] + suffix + ".csv"
    data = df(requested)
    if data.empty:
        text_file = open(path + filename, "w")
        text_file.write("No records fetched")
        text_file.close()
    else:
        data.to_csv(path+filename, index=False, header=fieldnames)
    return [(filename, len(data.index))]


############## milk query function ###########################
######## TOBE Verified!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
def milkQuery(cow_id, grp, stats, start_date, end_date, type):
    path = "result_files/"
    suffix = datetime.datetime.now(cur_timezone).strftime("%Y-%m-%d-%H:%M:%S")
    db = connect_se()
    requested_types = []
    if type[0]:
        requested_types.append("production")
    if type[1]:
        requested_types.append("station")
    print("Parameters into query function{}".format(requested_types), flush=True)
    return_value = []

    start_date = datetime.datetime.strptime(start_date, "%y-%m-%d")
    start_date = (start_date - datetime.timedelta(days=7)).strftime("%y-%m-%d")
    for recordType in requested_types:
        cur = db.cursor()

        statement = "SELECT * FROM CowInfo INNER JOIN MilkInfo ON CowInfo.cowID = MilkInfo.cowID" \
                    " AND CowInfo.insertDate = MilkInfo.insertDate WHERE recordType = {}" \
                    " AND MilkInfo.insertDate between {} and {}".format(quote(recordType),
                                                                        quote(start_date), quote(end_date))
        # print(statement, flush=True)
        cur.execute(statement)
        results = cur.fetchall()
        cur.close()

        # filter data
        if cow_id:
            results = list(filter(lambda x: x[0] in cow_id, results))
        if grp:
            results = list(filter(lambda x: x[3] in grp, results))
        results = list(filter(lambda x: x[4] in stats, results))

        headers = ["cowID", "insertDate", "recordType", "data"]
        # drop fields from cow info
        results = list(map(lambda x: x[7:], results))

        data = df(results)
        filename = recordType + suffix + ".csv"
        if data.empty:
            text_file = open(path + filename, "w")
            text_file.write("No records fetched")
            text_file.close()
        else:
            data.to_csv(path+filename, index=False, header=headers)
        return_value.append((filename, len(data.index)))
    return return_value


############## direct query function #########################


def directQuery(statement):
    db = connect_se()
    cur = db.cursor()
    try:
        cur.execute(statement)
    except Exception as e:
        return str(e)
    path = "result_files/"
    filename = "result.csv"
    result = cur.fetchall()

    result = df(result)
    if result.empty:
        text_file = open(path + filename, "w")
        text_file.write("No records fetched")
        text_file.close()
    else:
        result.to_csv(path+filename, header=False, index=False)
    return filename
