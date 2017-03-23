import pandas.io.data as web
import pandas as pd
from datetime import timedelta, datetime
import numpy as np
import math
import csv
import portfolioopt as pfopt
from collections import OrderedDict
from googlefinance import getQuotes
import json
from yahoo_finance import Share

#Supports long only for now.
class Position:
    def __init__(self,symbol,returns,direction,in_price,n_shares,returns_sp):
        #format for dates: "YYYY-MM-dd"
        self.symbol = symbol
        self.returns = returns
        self.direction = direction
        self.in_price = in_price
        self.n_shares = n_shares
        df = pd.concat([returns, returns_sp], axis=1)
        df = df.dropna(thresh=2, axis=0)
        df = df * 100
        c = df.cov()
        self.beta = c.iloc[0][1] / c.iloc[1][1]

class Portfolio:
    def __init__(self,assets,start_date,all_dates,money):
        self.start_date = start_date
        self.positions = assets
        self.symbols = [asset.symbol for asset in self.positions]
        self.returns_grid = np.array([asset.returns for asset in self.positions])
        total_amount = 0
        for asset in self.positions:
            total_amount = total_amount + asset.in_price * asset.n_shares
        self.weights = np.array([(asset.in_price * asset.n_shares)/total_amount for asset in self.positions])
        self.cash = money - total_amount
        self.initial_cash = money
        #historical
        self.historical_dates = all_dates
        self.historical_returns = np.dot(self.weights.transpose(),self.returns_grid)
        self.net_expectation = np.mean(100*self.historical_returns)
        self.covariance_matrix = np.cov(self.returns_grid*100)
        self.net_variance = np.dot(self.weights.T,np.dot(self.covariance_matrix,self.weights))
        #actual
        self.daily_values, self.values_dict = calculate_values(assets,start_date,total_amount)

    def get_asset_allocation(self):
        total_amount = 1082 #FIX THIS
        symbols = self.symbols
        weights = []
        symbols.append("Cash")
        for asset in self.positions:
            print asset.symbol
            total_amount += float(json.loads(json.dumps(getQuotes(asset.symbol)))[0]['LastTradePrice']) * asset.n_shares
            print total_amount
        for asset in self.positions:
            weights.append((float(json.loads(json.dumps(getQuotes(asset.symbol)))[0]['LastTradePrice']) * asset.n_shares)/total_amount)
        weights.append(1082/total_amount)
        print OrderedDict(zip(symbols, weights))
        return OrderedDict(zip(symbols, weights))

    def get_shares(self):
        shares = []
        for pos in self.positions:
            shares.append(pos.n_shares)
        sym = self.symbols
        sym.append("Cash")
        shares.append(self.cash)
        return OrderedDict(zip(sym, shares))
    def get_values(self):
        return self.values_dict
    def get_beta(self):
        beta_pos = [pos.beta for pos in self.positions]
        return np.dot(beta_pos,self.weights)
    def get_correlation_matrix(self):
        return np.corrcoef(self.returns_grid)
    def get_sharpe_ratio(self):
        return self.net_expectation/math.sqrt(self.net_variance)
    def get_historical_returns(self):
        return pd.Series(self.historical_returns,index=self.historical_dates)
    def get_variance(self):
        return self.net_variance
    def get_historical_expectation(self):
        return self.net_expectation
    def get_tickers(self):
        return self.symbols
    def get_cash(self):
        return self.cash
    def yearly_expected_ret(self, array):
        roll = 1
        for el in array:
            roll = roll * (1 + el / 100)
        return (roll - 1)*100
    #ordered dictionary of forecast for expected returns: key = ticker, value = weight (out of 1)
    def get_markowitz_analysis(self,forecasts=0):
        start_index = len(self.historical_returns) - 253
        end_index = len(self.historical_returns) - 1
        return_grid = 100 * self.returns_grid[:, start_index:end_index].T
        returns = pd.DataFrame(return_grid)
        avgs = [self.yearly_expected_ret(returns[col]) for col in returns.columns]
        cov_mat = pd.DataFrame(np.cov(return_grid.T))
        if forecasts == 0:
            avg_rets = pd.Series(avgs, index=returns.columns)
        else:
            avg_rets = pd.Series(forecasts.values(), index=returns.columns)
        w_opt = pfopt.tangency_portfolio(cov_mat, avg_rets, allow_short=False)
        ret_opt = (w_opt * avg_rets).sum()
        std_opt = (w_opt * returns).sum(1).std()

        smallest_target = max(min(avg_rets), 0)
        biggest_target = max(avg_rets)
        target_returns = np.arange(smallest_target, biggest_target, .0005)
        X = []
        Y = []
        for yi in target_returns:
            w = pfopt.markowitz_portfolio(cov_mat, avg_rets, yi)
            ret = (w * avg_rets).sum()
            std = (w * returns).sum(1).std()
            Y.append(ret)
            X.append(std)
        #coefs = np.polyfit(Y,X,2) #highest power first
        curve = {"risks":X,"returns":Y,"min_return":smallest_target,"max_return":biggest_target}
        tangency_port = {'weights': dict(w_opt),'X':std_opt,'Y':ret_opt}
        return {"tangency_port":tangency_port,"curve":curve}

    def compile_portfolio(self):
        in_prices = []
        directions = []
        shares = []
        for i in range(len(self.positions)):
            in_prices.append(self.positions[i].in_price)
            directions.append(self.positions[i].direction)
            shares.append(self.positions[i].n_shares)
        compilation = Portfolio_Compiled(self.symbols,shares,self.start_date,in_prices,directions,self.historical_dates,self.cash)
        return compilation

    def get_alpha(self):
        df = pd.DataFrame.from_csv("/home/CIBerkeley/CIBWebsite/returns_data.csv")
        prices_market = list(df['^GSPC'])[len(df)-252:len(df)]
        Rm = 1
        for rm in prices_market:
            Rm = Rm * (1 + rm)
        Rm = Rm - 1
        risk_free_rate = .007
        yearAgo = datetime.today() - timedelta(days=365)
        returns_cib = (9000 - get_historical_value(yearAgo)) / get_historical_value(yearAgo)
        beta = self.get_beta()
        alpha = returns_cib - risk_free_rate - (Rm - risk_free_rate) * beta
        return alpha

    #backtested for now. will link to actual account history after a while of trading.
    def get_information_ratio(self):
        df = pd.DataFrame.from_csv("/home/CIBerkeley/CIBWebsite/returns_data.csv")
        returns_market = np.array(df.iloc[-254:-1]["^GSPC"]*100)
        returns_port = self.historical_returns[-254:-1]*100
        print(np.mean(returns_port))
        print(np.mean(returns_market))
        sd_diff = np.std(returns_port-returns_market)
        exp_diff = np.mean(returns_port)-np.mean(returns_market)
        return exp_diff/sd_diff

    def get_exposures(self,weights):
        returns_factors = pd.DataFrame.from_csv("/home/CIBerkeley/CIBWebsite/returns_data.csv")
        returns_factors = 100 * returns_factors.loc[:,["XLY", "XLP", "XLE", "XLF", "XLV", "XLI", "XLB", "XLK", "XLU"]]
        returns_factors["Intercept"] = np.ones(len(returns_factors))
        A = np.array(returns_factors)
        grid = self.returns_grid.T
        w = []
        for symb in self.symbols:
            if symb != "Cash":
                w.append(weights[symb])
        w = np.array(w).T
        Y = grid.dot(w) * 100
        beta = np.linalg.lstsq(A, Y)[0]
        beta = list(beta[0:-1])
        factors = ["Consumer Discretionary","Consumer Staples","Energy","Financials","Healthcare","Industrials","Materials",\
                   "Technology","Utilities"]
        return OrderedDict(zip(factors, beta))

def get_historical_price(ticker, date):
    prev = date - timedelta(days=1)
    prevStr = prev.strftime("%Y-%m-%d")
    dateStr = date.strftime("%Y-%m-%d")
    return float(Share(ticker).get_historical(prevStr, dateStr)[0]['Adj_Close'])

def get_historical_value(query_date):
    assetValDict = OrderedDict()
    queryStr = query_date.strftime("%m/%d/%y")
    with open('/home/CIBerkeley/CIBWebsite/PortfolioValue.csv') as csvfile:
        reader = csv.reader(csvfile)
        reader.next()
        for row in reader:
            if row:
                date = row[0]
                day_value = float(row[1]) + float(row[2])
                assetValDict[date] = day_value
    if queryStr in assetValDict:
        return assetValDict[queryStr]
    else:
        return assetValDict.values()[0]

def get_value():
    assetValDict = OrderedDict()
    with open('/home/CIBerkeley/CIBWebsite/PortfolioValue.csv') as csvfile:
        reader = csv.reader(csvfile)
        reader.next()
        for row in reader:
            if row:
                date = row[0]
                day_value = float(row[1]) + float(row[2])
                assetValDict[date] = day_value
    return assetValDict.values()[-1]

def historical_values(query_start_date):
    assetValDict = OrderedDict()
    with open('/home/CIBerkeley/CIBWebsite/PortfolioValue.csv') as csvfile:
        reader = csv.reader(csvfile)
        reader.next()
        for row in reader:
            if row:
                print row
                date = row[0]
                day_value = float(row[1]) + float(row[2])
                assetValDict[date] = day_value

	portfolio_start_date = datetime.strptime(assetValDict.keys()[0], "%m/%d/%y")
	portfolio_start_value = assetValDict.values()[0]
	portfolioValDict = OrderedDict()
	d = query_start_date
	today = datetime.today() - timedelta(hours=7) #COULD BE SOURCE OF ERROR AROUND DAYLIGHT SAVINGS
	while d <= today:
		if d < portfolio_start_date:
			portfolioValDict[d.strftime("%m/%d/%y")] = portfolio_start_value
		else:
			portfolioValDict[d.strftime("%m/%d/%y")] = assetValDict[d.strftime("%m/%d/%y")]
		d += timedelta(days=1)
	return portfolioValDict

def calculate_values(assets,start_date,first_amount):
    tickers = [asset.symbol for asset in assets]
    n_shares = [asset.n_shares for asset in assets]
    prices = web.DataReader(tickers, 'google', start_date)['Close']
    dates = [d.to_datetime() for d in prices.index]
    values = []
    values.append(first_amount)
    for i in range(len(prices)):
        if i != 0:
           values.append(np.dot(prices.iloc[[i]], n_shares)[0])
    return values, OrderedDict(zip(dates, values))

class Portfolio_Compiled:
    def __init__(self,tickers,shares,start_date,in_prices,directions,all_dates,money):
        self.tickers = tickers
        self.shares = shares
        self.start_date = start_date
        self.in_prices = in_prices
        self.directions = directions
        self.historical_dates = all_dates
        self.cash = money

    def uncompile_and_update(self,df):
        positions = []
        for i in range(len(self.tickers)):
                pos = Position(self.tickers[i],df[self.tickers[i]],self.directions[i],self.in_prices[i],self.shares[i],df['^GSPC'])
                positions.append(pos)
        portfolio = Portfolio(positions,self.start_date,self.historical_dates,self.cash)
        return portfolio

    def uncompile(self):
        df = pd.DataFrame.from_csv("/home/CIBerkeley/CIBWebsite/returns_data.csv")
        positions = []
        for i in range(len(self.tickers)):
                pos = Position(self.tickers[i],df[self.tickers[i]],self.directions[i],self.in_prices[i],self.shares[i],df['^GSPC'])
                positions.append(pos)
        portfolio = Portfolio(positions,self.start_date,self.historical_dates,self.cash)
        return portfolio