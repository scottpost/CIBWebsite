import datetime
import sqlite3 as lite

# Todo: change primary key to an int!!
volatility_table_structure = '(Time TEXT PRIMARY KEY, Hv10 TEXT, Hv20 TEXT, \
                              Hv30 TEXT, Hv60 TEXT, Hv90 TEXT, Hv120 TEXT, \
                              Hv150 TEXT, Hv180 TEXT, IvMean10 TEXT, \
                              IvMean20 TEXT, IvMean30 TEXT, IvMean60 TEXT, \
                              IvMean90 TEXT, IvMean120 TEXT, IvMean150 TEXT, \
                              IvMean180 TEXT, IvMean270 TEXT, IvMean360 TEXT, \
                               IvMean720 TEXT, IvMean1080 TEXT)'

con = lite.connect('/home/CIBerkeley/CIBWebsite/cib_data_v2.db')

def vol_table_name(ticker):
    return ticker + '_VOLATILITY'

# Todo: change so primary key is an integer
# def datetime_to_integer(dt_time):
    # Todo(anyone): assert dt_time is a datetime
    # return 10000*dt_time.year + 100*dt_time.month + dt_time.day

"""
Method that inserts equity google results into a table.
"""
def vol_day_insert(volatility_info):
    ticker = volatility_info[0]
    time = volatility_info[1]
    hv10 = volatility_info[2]
    hv20 = volatility_info[3]
    hv30 = volatility_info[4]
    hv60 = volatility_info[5]
    hv90 = volatility_info[6]
    hv120 = volatility_info[7]
    hv150 = volatility_info[8]
    hv180 = volatility_info[9]
    ivmean10 = volatility_info[9 + 11]
    ivmean20 = volatility_info[9 + 11 + 4]
    ivmean30 = volatility_info[9 + 11 + (2 * 4)]
    ivmean60 = volatility_info[9 + 11 + (3 * 4)]
    ivmean90 = volatility_info[9 + 11 + (4 * 4)]
    ivmean120 = volatility_info[9 + 11 + (5 * 4)]
    ivmean150 = volatility_info[9 + 11 + (6 * 4)]
    ivmean180 = volatility_info[9 + 11 + (7 * 4)]
    ivmean270 = volatility_info[9 + 11 + (8 * 4)]
    ivmean360 = volatility_info[9 + 11 + (9 * 4)]
    ivmean720 = volatility_info[9 + 11 + (10 * 4)]
    ivmean1080 = volatility_info[9 + 11 + (11 * 4)]

    table_formatted = vol_table_name(ticker)
    params = (str(time), str(hv10), str(hv20), str(hv30), str(hv60), str(hv90),\
              str(hv120), str(hv150), str(hv180), str(ivmean10), str(ivmean20),\
              str(ivmean30), str(ivmean60), str(ivmean90), str(ivmean120),\
              str(ivmean150), str(ivmean180), str(ivmean270), str(ivmean360),\
              str(ivmean720), str(ivmean1080))

    db_create_insert(table_formatted,
                     volatility_table_structure,
                     "INSERT INTO {} VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     params,
                     ticker_for_debug=ticker)

def db_create_insert(table_formatted, table_structure, insert_str, params, ticker_for_debug):
    # Use con for column persistance.
    with con:
        cur = con.cursor()
        # Check if table exists, if not create it.
        cur.execute("CREATE TABLE IF NOT EXISTS {} {}".format(table_formatted, table_structure, params, ))
        try:
           cur.execute(insert_str.format(table_formatted), params)
        except lite.IntegrityError as err:
            print("Possible duplicate insertion of " + ticker_for_debug + " into " + table_formatted + ': ' + str(err))

"""
Method that returns all volatility info in db for a stock
"""
def get_all_vol_info(ticker):
    table_name = vol_table_name(ticker)
    with con:
        cur = con.cursor()
        cur.execute('SELECT * FROM {tn}'.format(tn=table_name))
        rows = cur.fetchall()
        fmt_rows = []
        for row in rows:
            date = row[0]
            try:
                vol_values = [float(x) for x in row[1:]]
            except:
                print("Skipping this example because of incomplete data")
                continue
            keys = ['hv10', 'hv20', 'hv30' ,'hv60', 'hv90', 'hv120', \
                        'hv150', 'hv180', 'ivmean10', 'ivmean20', 'ivmean30', \
                        'ivmean60', 'ivmean90', 'ivmean120', 'ivmean150', \
                        'ivmean180', 'ivmean270', 'ivmean360', 'ivmean720', \
                        'ivmean1080']
            row_dict = dict(zip(keys, vol_values))
            # Todo(anyone): refactor so it returns a datetime instead.  Cleaner.
            # will also have to refactor news_sentiment_day_insert to take a datetime.
            row_dict['date'] = datetime.datetime.strptime(date,"%Y-%m-%d").date()
            fmt_rows.append(row_dict)
        return fmt_rows

def get_available_vol_dates(ticker):
    all_vol_info = get_all_vol_info(ticker)
    datetimes = [x['date'] for x in all_vol_info]
    datetimes.sort()
    return {'max':max(datetimes), 'min':min(datetimes), 'all':datetimes}

'''
Returns number_of_days volatility info ending at end_date
'''
def get_vol_range(ticker, end_date, number_of_days):
    # Todo: this is very, very inneficient
    all_data = get_all_vol_info(ticker)
    end_index = -1
    for i in range(len(all_data)):
        if all_data[i]['date'] == end_date:
            end_index = i
            break
    if end_index < 0:
        assert("Date does not exist")
    return all_data[end_index - number_of_days + 1:end_index+1]

'''
Returns num related tickers using relation_type
'''
def get_related_tickers(tickers, relation_type, num):
    # Todo: implement
    hardcoded_temp_list = ['AAPL', 'GOOGL', 'JPM', 'WDC', 'AMZN', 'QCOM', 'BIP', 'NDAQ', 'GE', 'USB', 'IBM']
    return hardcoded_temp_list[0:num]