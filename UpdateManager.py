import pickle
import datetime
import pandas.io.data as web
import pandas as pd
from Portfolio import Portfolio, Position
import os

#The front end should pass p of the following format:
#list of 4 elements:
#tickers = p[0] - list
#number_shares = p[1] - list
#costs = p[2] - list

def start_manager_update_process(p,start_date):
    if os.path.isfile('/home/CIBerkeley/CIBWebsite/portfolio.txt') is False:
        # a  few requirements to set up the data pipeline
        indices  = ["^GSPC","XLY", "XLP", "XLE", "XLF", "XLV", "XLI", "XLB", "XLK", "XLU"]
        df = web.DataReader(indices,'yahoo',datetime.datetime(2010, 1, 1))['Close']
        df = df.pct_change()[1:len(df)]
        df.columns = indices
        df.to_csv("/home/CIBerkeley/CIBWebsite/returns_data.csv")
        with open('/home/CIBerkeley/CIBWebsite/portfolio.txt','wb') as f:
            pickle.dump([],f)

    latest_portfolio = manager_portfolio_update(p,start_date)
    save_new_portfolio(latest_portfolio)
    return latest_portfolio

def manager_portfolio_update(p,start_date=datetime.date.today()):
    tickers = p[0]
    number_shares = p[1]
    costs = p[2]
    old_ports = pull_old_portfolios()
    if len(old_ports) == 0:
        cash = 10000
    else:
        last_port = old_ports[-1].uncompile()
        cash = last_port.cash + last_port.daily_values[-1]
    #replace by querying some database for the current (intra day) price instead of the last closing price for value at which you sold.
    df = manager_data_update(tickers)
    df = df.dropna(thresh=len(tickers), axis=0) #this line restrict historical calculations to data points shared by all equities
    all_dates = df.index
    assets = []
    for i in range(len(tickers)):
        symbol = tickers[i]
        n_shares = number_shares[i]
        in_price = costs[i]
        returns = df[symbol]
        returns_sp = df['^GSPC']
        direction_pos = direction(n_shares)
        assets.append(Position(symbol,returns,direction_pos,in_price,n_shares,returns_sp))
    latest_portfolio = Portfolio(assets,start_date,all_dates,cash)
    return latest_portfolio

#initially load csv with one series going back at least to 2010
def manager_data_update(tickers):
    df = pd.DataFrame.from_csv("/home/CIBerkeley/CIBWebsite/returns_data.csv")
    tickers = set(tickers)
    new_tickers = list(tickers - set(df.columns))
    if len(new_tickers) > 0:
        new_columns = web.DataReader(new_tickers,'yahoo',datetime.datetime(2010, 1, 1))['Close']
        new_columns = new_columns.pct_change()[1:len(new_columns)]
        df = df.join(new_columns,how='outer')
        df.to_csv("/home/CIBerkeley/CIBWebsite/returns_data.csv")
    return df

def save_new_portfolio(latest_portfolio):
    all_portfolios = pull_old_portfolios()
    all_portfolios.append(latest_portfolio.compile_portfolio())
    with open('/home/CIBerkeley/CIBWebsite/portfolio.txt', 'wb') as f:
        pickle.dump(all_portfolios, f)

def direction(w):
    if w >= 0:
        return "long"
    else:
        return "short"

#use this to plot the historical performance of the fund, for whatever asset allocation
def pull_old_portfolios():
    with open('/home/CIBerkeley/CIBWebsite/portfolio.txt','rb') as f:
        var = pickle.load(f)
    return var