import pickle
import datetime
import pandas.io.data as web
import pandas as pd

def daily_data_update():
    df = pd.DataFrame.from_csv("./returns_data.csv")
    tickers = df.columns
    today_row = web.DataReader(tickers,'yahoo',datetime.date.today() - datetime.timedelta(days=1),datetime.date.today())['Close']
    today_row = today_row.pct_change()[1:len(today_row)]
    df = df.append(today_row)
    df.to_csv("./returns_data.csv")
    return df

def start_daily_update_process():
    latest_saved_portfolio = pull_latest_portfolio()
    df = daily_data_update()
    latest_portfolio = daily_portfolio_update(latest_saved_portfolio,df)
    update_last_portfolio(latest_portfolio)

def daily_portfolio_update(latest_saved_portfolio,return_grid):
    df = return_grid
    latest_portfolio = latest_saved_portfolio.uncompile_and_update(df)
    return latest_portfolio

def pull_latest_portfolio():
    olds = pull_old_portfolios()
    return olds[len(olds)-1]

def update_last_portfolio(latest_portfolio):
    all_portfolios = pull_old_portfolios()
    all_portfolios[len(all_portfolios)-1] = latest_portfolio.compile_portfolio()
    with open('./portfolio.txt', 'wb') as f:
        pickle.dump(all_portfolios, f)

    #use this to plot the historical performance of the fund, for whatever asset allocation
def pull_old_portfolios():
    with open('./portfolio.txt','rb') as f:
        var = pickle.load(f)
        return var

#Run everyday after market closes
start_daily_update_process()
