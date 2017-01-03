import Portfolio
from dateutil import rrule
import datetime
import math
import numpy as np
import pandas as pd

#Monte Carlo API:
# (1) call monte_carlo_simulation(mu,sigma,n_trials,horizon) where horizon is in months, n_trials the number of experiments, mu and sigma the statistics of your portfolio
# (2) call MonteCarlo_statistics(perf) where perf is returned by the previous call. Plot the historical perfs of the few quantiles versus the trading days also returned by the previous function.
# (3) interactively pull probas from probability_of_perf(final_perf,goal,upside=True)

class Simulation:
    #weights and forecasts are optional ordered dictionaries with tickers as keys
    def __init__(self,portfolio,horizon=48,n_trials=1000, weights = 0, forecasts = 0):
        self.horizon = horizon
        self.n_trials = n_trials
        if weights != 0:
            weights = np.array(weights.values())
            covariance_matrix = np.cov(portfolio.returns_grid)
            self.sigma = math.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
            if forecasts == 0:
                hist_returns = np.dot(weights.transpose(), portfolio.returns_grid)
                self.mu = np.mean(hist_returns)
            else:
                forecasts = np.array(forecasts.values())/252
                self.mu = weights.dot(forecasts)
        else:
            self.sigma = math.sqrt(portfolio.net_variance)
            if forecasts == 0:
                self.mu = portfolio.net_expectation
            else:
                forecasts = np.array(forecasts.values())/252
                self.mu = portfolio.weights.dot(forecasts)

        self.trading_days, self.returns = monte_carlo_simulation(self.mu, self.sigma, self.n_trials, self.horizon)
        self.final,self.stats,self.perf_series_quartile1,self.perf_series_quartile2,self.perf_series_quartile3 = MonteCarlo_statistics(self.returns)
        self.mean = self.stats[0]['mean']
        self.max = self.stats[0]['max']
        self.min = self.stats[0]['min']
        self.std = self.stats[0]['std']
        self.quartile1 = self.stats[0]['25%']
        self.quartile2 = self.stats[0]['50%']
        self.quartile3 = self.stats[0]['75%']


    #Asking what is the probability to perform better than a given goal or worst than a given limit
    #simply the cdf of the distribution of final performance obtained from monte carlo simulation
    #upside is for better than goal; if false assume proba of doing worst than goal
    def probability_of_perf(self,goal,upside=True):
        ordered_perfs = self.final[0].sort(inplace=False)
        if upside is True:
            p = ordered_perfs[ordered_perfs >= goal].count()/(ordered_perfs.count()+1)
        else:
            p = ordered_perfs[ordered_perfs <= goal].count()/(ordered_perfs.count()+1)
        return p

    def get_trading_days(self):
        return self.trading_days

    def get_full_perf_quartile(self,quartile):
        if quartile == 1:
            #25%
            return self.perf_series_quartile1
        elif quartile == 2:
            #median
            return self.perf_series_quartile2
        elif quartile == 3:
            #75%
            return self.perf_series_quartile3

    def get_min(self):
        return self.min
    def get_max(self):
        return self.max
    def get_mean(self):
        return self.mean
    def get_std(self):
        return self.std
    def get_first_q(self):
        return self.quartile1
    def get_second_q(self):
        return self.quartile2
    def get_third_q(self):
        return self.quartile3

    def get_max_drawdown_first_q(self):
        min(pd.Series(self.quartile1).pct_change()[1:]) * 100

    def get_max_drawdup_first_q(self):
        max(pd.Series(self.quartile1).pct_change()[1:]) * 100

    def get_max_drawdown_second_q(self):
        min(pd.Series(self.quartile2).pct_change()[1:]) * 100

    def get_max_drawdup_second_q(self):
        max(pd.Series(self.quartile2).pct_change()[1:]) * 100

    def get_max_drawdown_third_q(self):
        min(pd.Series(self.quartile3).pct_change()[1:]) * 100

    def get_max_drawdup_third_q(self):
        max(pd.Series(self.quartile3).pct_change()[1:]) * 100


#returns statistics for the MC simulation (complete track of 75th,median,25th quartiles; final perf of mean,max,min,sd);
# returns statistics for the MC simulation (complete track of 75th,median,25th quartiles; final perf of mean,max,min,sd);
def MonteCarlo_statistics(perf):
    # equity = (1+0.01r1)(1+0.01r2)...(1+0.01rn)
    final = 1 + (perf / 100)
    final = np.prod(final, axis=1)

    final = pd.DataFrame(final)
    info = final.describe()
    quartile1 = info[0]['25%']
    quartile2 = info[0]['50%']
    quartile3 = info[0]['75%']
    index_quartile1 = final[
        (quartile1 - 0.001 * quartile1 < final) & (quartile1 + 0.001 * quartile1 > final)].first_valid_index()
    index_quartile2 = final[
        (quartile2 - 0.001 * quartile2 < final) & (quartile2 + 0.001 * quartile2 > final)].first_valid_index()
    index_quartile3 = final[
        (quartile3 - 0.001 * quartile3 < final) & (quartile3 + 0.001 * quartile3 > final)].first_valid_index()

    perf_series_quartile1 = roll_prod(perf[index_quartile1])
    perf_series_quartile2 = roll_prod(perf[index_quartile2])
    perf_series_quartile3 = roll_prod(perf[index_quartile3])
    return final, info, perf_series_quartile1, perf_series_quartile2, perf_series_quartile3


def roll_prod(array):
    new_array = [1]
    roll = 1
    for el in array:
        roll = roll * (1 + el / 100)
        new_array.append(roll)
    return new_array

#horizon in months
#about 45 seconds for 1 million trials and 4 years
def monte_carlo_simulation(mu,sigma,n_trials,horizon):
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(horizon*365/12)
    trading_days = list(NYSE_tradingdays(start_date,end_date))
    n_days = len(trading_days)
    returns = np.random.normal(mu,sigma,size=(n_trials,n_days))
    return trading_days,returns

def NYSE_tradingdays(a,b):
    rs = rrule.rruleset()
    rs.rrule(rrule.rrule(rrule.DAILY, dtstart=a, until=b))
    # Exclude weekends and holidays
    rs.exrule(rrule.rrule(rrule.WEEKLY, dtstart=a, byweekday=(rrule.SA,rrule.SU)))
    rs.exrule(NYSE_holidays(a,b))
    return rs

def NYSE_holidays(a=datetime.date.today(), b=datetime.date.today()+datetime.timedelta(days=365)):
    rs = rrule.rruleset()
    # Include all potential holiday observances
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth=12, bymonthday=31, byweekday=rrule.FR)) # New Years Day
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth= 1, bymonthday= 1))                     # New Years Day
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth= 1, bymonthday= 2, byweekday=rrule.MO)) # New Years Day
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth= 1, byweekday= rrule.MO(3)))            # Martin Luther King Day
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth= 2, byweekday= rrule.MO(3)))            # Washington's Birthday
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, byeaster= -2))                                  # Good Friday
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth= 5, byweekday= rrule.MO(-1)))           # Memorial Day
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth= 7, bymonthday= 3, byweekday=rrule.FR)) # Independence Day
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth= 7, bymonthday= 4))                     # Independence Day
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth= 7, bymonthday= 5, byweekday=rrule.MO)) # Independence Day
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth= 9, byweekday= rrule.MO(1)))            # Labor Day
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth=11, byweekday= rrule.TH(4)))            # Thanksgiving Day
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth=12, bymonthday=24, byweekday=rrule.FR)) # Christmas
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth=12, bymonthday=25))                     # Christmas
    rs.rrule(rrule.rrule(rrule.YEARLY, dtstart=a, until=b, bymonth=12, bymonthday=26, byweekday=rrule.MO)) # Christmas
    # Exclude potential holidays that fall on weekends
    rs.exrule(rrule.rrule(rrule.WEEKLY, dtstart=a, until=b, byweekday=(rrule.SA,rrule.SU)))
    return rs