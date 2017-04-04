#==================================================================================================================================
# IMPORTS
#==================================================================================================================================

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from newspaper import Article
import gnp
import csv
import pickle
import requests
from bs4 import BeautifulSoup
from pandas_datareader.data import DataReader
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from googlefinance import getQuotes
import UpdateManager
import MonteCarlo
import CIBDatabase
from Portfolio import historical_values, get_historical_price, get_historical_value, get_value
from collections import OrderedDict
from dateutil import rrule
#from optionchain import OptionChain
from yahoo_finance import Share
import math
from flask_sqlalchemy import SQLAlchemy
from flask_user import UserManager, UserMixin, SQLAlchemyAdapter
from flask_login import login_user, LoginManager, login_required, logout_user

#==================================================================================================================================
# CONFIGURATION
#==================================================================================================================================

#FLASK CONFIGURATION
app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
TICKERS = []
with open('./SP500.csv', 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='|')
    for row in reader:
        TICKERS.append("$" + row[0])

#==================================================================================================================================
# USER AUTHENTICATION SETUP
#==================================================================================================================================

app.config['SQLALCHEMY_DATABASE_URI']  = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="CIBerkeley",
    password="CIBSpring2017",
    hostname="CIBerkeley.mysql.pythonanywhere-services.com",
    databasename="CIBerkeley$default",
)
app.config['TESTING'] = False

db = SQLAlchemy(app)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)

    # User information
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='0')
    first_name = db.Column(db.String(100), nullable=False, server_default='')
    last_name = db.Column(db.String(100), nullable=False, server_default='')
    votes = db.Column(db.String(255), nullable=False, server_default='')
    ownership = db.Column(db.String(255), nullable=False, server_default= '')
    username = db.Column(db.Unicode(255), nullable=False, server_default=u'', unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')

    def __init__(self, first, last, votes, ownership, username, password):
        self.username = username
        self.first_name = first
        self.last_name = last
        self.votes = votes
        self.ownership = ownership
        self.password = password
        self.active = True

    def __repr__(self):
        return '%r' % self.username

# Setup Flask-User
db_adapter = SQLAlchemyAdapter(db, User)        # Register the User model
user_manager = UserManager(db_adapter, app)     # Initialize Flask-User
login_manager = LoginManager()

@app.login_manager.unauthorized_handler
def unauthorized():
    return redirect('/login')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect('/')

#==================================================================================================================================
# HELPER FUNCTIONS
#==================================================================================================================================

def getReturns(initialPrice, finalPrice):
    return round(((finalPrice - initialPrice) / initialPrice) * 100, 2)

def getVolData(ticker_list, v_type_list, end_date = datetime(2014, 10, 1).date(), number_of_days = 199):
    vol_types = {'iv30d': 'ivmean30', 'iv60d': 'ivmean60', 'iv90d': 'ivmean90', 'iv120d': 'ivmean120', 'iv150d': 'ivmean150', 'iv270d': 'ivmean270', 'iv360d': 'ivmean360', 'iv720d': 'ivmean720', 'iv1080d': 'ivmean1080',
             'cls10dHv': 'hv10', 'cls20dHv': 'hv20', 'cls60dHv': 'hv60', 'cls120dHv': 'hv120', 'cls150dHv': 'hv150', 'cls180Hv': 'hv180'}
    vols = []
    result = OrderedDict()
    for i in range(len(ticker_list)):
        i_type = v_type_list[i]
        relevant_vols = CIBDatabase.get_vol_range(ticker_list[i], end_date, number_of_days)
        dates = [d['date'] for d in relevant_vols]
        if (i_type in vol_types):
            db_vol_type = vol_types[i_type]
        else:
            raise ValueError('Invalid volatility type passed in.')
        vols.append([d[db_vol_type] for d in relevant_vols])
    i = 0
    for date in dates:
        result[date.strftime("%m-%d-%Y")] = [vols[0][i] * 10, vols[1][i] * 10]
        i += 1
    print result
    return result

#==================================================================================================================================
# FLASK STATIC VIEW FUNCTIONS
#==================================================================================================================================

@app.route('/', methods=['GET', 'POST'])
def index():
	return render_template('index.html')

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/marketSearch', methods = ['POST', 'GET'])
@login_required
def marketSearch():
    if request.method == 'POST':
        ticker = request.form["ticker"]
        return redirect(url_for('market', ticker=ticker))
    return render_template('marketSearch.html')

@app.route('/analyst')
def analyst():
	return render_template('analyst.html')

@app.route('/farallon')
def farallon():
	return render_template('farallon.html')

@app.route('/teams')
def teams():
	return render_template('teams.html')

@app.route('/blog')
@login_required
def blog():
	return render_template('blog.html')

@app.route("/market/<ticker>")
@login_required
def market(ticker):
    fundamentalsDict = getFundamental(ticker)
    valuesYear = OrderedDict()
    today = datetime.today()
    yearAgo = today - timedelta(days=255)
    reader = DataReader(ticker,  'yahoo', yearAgo, today).as_matrix()
    for row in reader:
        valuesYear[row[0]] = row[5]
    ticker=ticker.upper()
    valuesMonth = OrderedDict(valuesYear.items()[-30:])
    valuesWeek = OrderedDict(valuesYear.items()[-7:])
    return render_template("market.html",
										 fundamentalsDict=fundamentalsDict,
										 valuesWeek=valuesWeek,
										 valuesMonth=valuesMonth,
										 valuesYear=valuesYear,
										 ticker=ticker)
@app.route('/apply', methods = ['POST', 'GET'])
def apply():
    if request.method == 'POST':
        first = str(request.form['first'].encode('utf-8'))
        last = str(request.form['last'].encode('utf-8'))
        major = str(request.form['major'].encode('utf-8'))
        gpa = str(request.form['gpa'].encode('utf-8'))
        email = str(request.form['email'].encode('utf-8'))
        try:
            exception = request.form['meetings'].encode('utf-8')
            meetings = "Yes"
        except:
            meetings = "No"
        referral = str(request.form['referral'].encode('utf-8'))
        concept = str(request.form['concept'].encode('utf-8'))
        contribution = str(request.form['contribution'].encode('utf-8'))
        pickle.dump([first, last, major, gpa, email, meetings, referral, concept, contribution], open("pickleApplications.txt","a"))
        print first, last, major, gpa, email, meetings, referral, concept, contribution
        with open('applications.csv', 'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([first, last, major, gpa,
                            email,  meetings,
                            referral, concept, contribution])
        return render_template('congrats.html')

    return render_template('apply.html')

@app.route('/terminal')
@login_required
def terminal():
    dateObj = datetime.today()
    start_date = dateObj - timedelta(days=500)
    trading_days = list(reversed(NYSE_tradingdays(start_date, dateObj)))
    return render_template("terminal.html", tradingDates = trading_days[1:], searchData = SEARCH_DATA, graphData = {})

#FLASK ROUTE CALCULATE FUNCTION
@app.route('/calculate/<query>', methods = ['POST', 'GET'])
@login_required
def calculate(query):
	query = query.replace("_s", " ").replace("_f", "/")
	queryType = ""
	words = query.split(" ")
	for word in words:
		if word == 'graph':
			queryType = 'graph'
		if word == 'closing':
			queryType = 'closing price'
		if word == 'fundamentals':
			queryType = 'fundamentals'
		if word == 'options':
			queryType = 'options chain'

	if queryType == 'closing price':
		ticker = words[5]
		date = words[7]
		price = getClosingPrice(ticker, date)
		return jsonify(type='closing', ticker=ticker, date=date, price = price)

	if queryType == 'fundamentals':
		ticker = words[4]
		fundamentals = getFundamentals(ticker)
		return jsonify(type='fundamentals',ticker=ticker,ebitda=fundamentals['ebitda'],bookValue=fundamentals['bookValue'],marketCap=fundamentals['marketCap'])

	if queryType == 'options chain':
		ticker = words[5]
		puts, calls = getOptionsChain(ticker)
		return jsonify(type ='options chain', puts = puts,calls=calls)

	graphType = ""
	prefix = ""
	if queryType == 'graph':
		ticker = words[7]
		dateOne = words[9]
		dateTwo = words[11]
		for word in words:
			if word == 'Price':
				graphType = 'Trading Price'
				prefix = "$"
			if word == 'Volume':
				graphType = 'Trading Volume'
			if word == 'Volatility':
				graphType = 'Historical Volatility'
		temp = getGraphData(graphType, ticker, dateOne, dateTwo)
		final = []
		for day, value in temp.iteritems():
			final.append({'label' : day, 'ticker' : ticker, 'value' : value})
		final = list(reversed(final))
		labelStep = len(final) // 5
		return jsonify(type='graph', labelStep=labelStep, prefix=prefix, graphType=graphType, ticker=ticker, data = final, dates = [dateOne, dateTwo])
	result = "Bad query"
	return jsonify(data = result)

#VOLATILITY CALCULATIONS
def perc_change(price_list):
 return [(v / price_list[abs(i-1)])-1 for i, v in enumerate(price_list)]

def variance(price_list):
 perc = perc_change(price_list)
 avg = average(perc)
 return [(x - avg)**2 for x in perc]

def average(x):
 return sum(x)/len(x)

# HELPER FUNCTIONS
def getFundamental(ticker):
    dates = ['2016-4','2016-3','2016-2','2016-1', '2015-4', '2015-3', '2015-2', '2015-1']
    resultsDict = OrderedDict()
    for date in dates:
        url = "http://www.streetinsider.com/stock_lookup.php?q=" + ticker + "&financials=income&yq=" + date
    	text = requests.get(url,
                        headers = {'User-Agent': 'Mozilla/5.0'},
                        params={'type':'upcoming'}).text
    	soup = BeautifulSoup(text)
    	data = soup.findAll('td')
    	#resultsDict[date] = { 'r&d' : data[8].children.next(),
    						  #'eps' : data[24].children.next(),
    						  #'netIncome' : data[21].children.next(),
    						  #'netSales' : data[1].children.next() }
        resultsDict = {'2015-1' : {'r&d' : 0.18, 'eps' : 0.18, 'netIncome' : 0.18, 'netSales' : 0.18},
        '2015-2' : {'r&d' : 0.18, 'eps' : 0.18, 'netIncome' : 0.18, 'netSales' : 0.18},
        '2015-3' : {'r&d' : 0.18, 'eps' : 0.18, 'netIncome' : 0.18, 'netSales' : 0.18},
        '2015-4' : {'r&d' : 0.18, 'eps' : 0.18, 'netIncome' : 0.18, 'netSales' : 0.18},
        '2016-1' : {'r&d' : 0.18, 'eps' : 0.18, 'netIncome' : 0.18, 'netSales' : 0.18},
        '2016-2' : {'r&d' : 0.18, 'eps' : 0.18, 'netIncome' : 0.18, 'netSales' : 0.18},
        '2016-3' : {'r&d' : 0.18, 'eps' : 0.18, 'netIncome' : 0.18, 'netSales' : 0.18},
        '2016-4' : {'r&d' : 0.18, 'eps' : 0.18, 'netIncome' : 0.18, 'netSales' : 0.18}

        }
    return resultsDict

def getClosingPrice(ticker, date):
	dateObj = datetime.strptime(date, '%m/%d/%y')
	reader = DataReader(ticker[1:],  'yahoo', dateObj, dateObj)
	return round(reader['Close'][0], 2)

def getGraphData(graphType, ticker, dateOne, dateTwo):
	dateOneObj = datetime.strptime(dateOne, '%m/%d/%y')
	dateTwoObj = datetime.strptime(dateTwo, '%m/%d/%y')
	if graphType == 'Trading Price':
		reader = DataReader(ticker[1:],  'yahoo', dateOneObj, dateTwoObj).as_matrix()
		closingPrices = []
		for row in reader:
			closingPrices.append(row[5])
		dateObj = datetime.today()
		start_date = dateObj - timedelta(days=500)
		trading_days = list(reversed(NYSE_tradingdays(start_date, dateObj)))
		return OrderedDict(zip(trading_days, closingPrices))
	if graphType == 'Trading Volume':
		reader = DataReader(ticker[1:],  'yahoo', dateOneObj, dateTwoObj).as_matrix()
		volumes = []
		for row in reader:
			volumes.append(row[4])
		dateObj = datetime.today()
		start_date = dateObj - timedelta(days=500)
		trading_days = list(reversed(NYSE_tradingdays(start_date, dateObj)))
		return OrderedDict(zip(trading_days, volumes))
	if graphType == 'Historical Volatility':
		reader = DataReader(ticker[1:],  'yahoo', dateOneObj, dateTwoObj).as_matrix()
		prices = []
		for row in reader:
			prices.append(row[5])
		volatilities = []
		for i in range(0, len(prices) - 10):
			var = variance(prices[i:1+10])
			vol = math.sqrt(average(var))
			volatilities.append(vol)
		dateObj = datetime.today()
		start_date = dateObj - timedelta(days=500)
		trading_days = list(reversed(NYSE_tradingdays(start_date, dateObj)))
		return OrderedDict(zip(trading_days, volatilities))

def getOptionsChain(ticker):
	# query = "NASDAQ:" + ticker[1:]
	# oc = OptionChain(query)
	# return oc.puts, oc.calls
    print("getOptionsChain() is currently broken because it's missing the optionchain module")
    return None #No optionchain module found!!!

def getFundamentals(ticker):
	share = Share(ticker[1:])
	result = {}
	result['bookValue'] = share.get_book_value()
	result['marketCap'] = share.get_market_cap()
	result['ebitda'] = share.get_ebitda()
	return result

def NYSE_tradingdays(a,b):
    rs = rrule.rruleset()
    rs.rrule(rrule.rrule(rrule.DAILY, dtstart=a, until=b))
    # Exclude weekends and holidays
    rs.exrule(rrule.rrule(rrule.WEEKLY, dtstart=a, byweekday=(rrule.SA,rrule.SU)))
    rs.exrule(NYSE_holidays(a, b))

    days = []
    for row in rs:
    	days.append(row.strftime("%m/%d/%y"))
    return days

def NYSE_holidays(a, b):
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

#PREPARE DATA FOR JAVASCRIPT (EVENTUALLY THIS WILL BE DONE DIFFERENTLY)
dateObj = datetime.today()
start_date = dateObj - timedelta(days=500)
trading_days = list(reversed(NYSE_tradingdays(start_date, dateObj)))

#PREPARE THE COMPLETE.LY DICTIONARY OBJECT
SEARCH_DATA = OrderedDict()
for ticker in TICKERS:
	SEARCH_DATA["Show me closing price for " + str(ticker) + " on "] = trading_days[1:]
	SEARCH_DATA["Show me graph of Trading Price for " + str(ticker) + " from "] = trading_days[1:]
	SEARCH_DATA["Show me graph of Trading Volume for " + str(ticker) + " from "]  = trading_days[1:]
	SEARCH_DATA["Show me graph of Historical Volatility for " + str(ticker) + " from "] = trading_days[1:]
SEARCH_DATA["Show me graph of Historical Volatility for "] = TICKERS
SEARCH_DATA["Show me graph of Trading Volume for "] = TICKERS
SEARCH_DATA["Show me graph of Trading Price for "] = TICKERS
SEARCH_DATA["Show me options chain for "] = TICKERS
SEARCH_DATA["Show me fundamentals for "] = TICKERS
SEARCH_DATA["Show me closing price for "] = TICKERS
SEARCH_DATA["Show me graph of "] = ["Trading Price ", "Trading Volume ", "Historical Volatility "]
SEARCH_DATA["Show me "] = ["graph", "closing price", "fundamentals","options chain"]
SEARCH_DATA[""] = ["Show me ", "Clear", "Print"]

#==================================================================================================================================
# FLASK DYNAMIC VIEW FUNCTIONS
#==================================================================================================================================

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        user = User.query.filter(User.username == request.form['text']).first()
        if user:
            password = user.password
            if request.form['password'] == password:
                login_user(user)
                return redirect(url_for('portal'))
        return render_template('login.html', clean = False)
    return render_template('login.html', clean = True)



@app.route('/live', methods=['POST', 'GET'])
def live():
    #PULLING PORTFOLIO DATA
    #assetDict = {'ACM' : 55, 'ADBE' : 13, 'AMD': 87, 'DSKE': 119, 'FCG' : 82}
    #cash = 1082
    #todayValue = cash
    #for asset, quantity in assetDict.iteritems():
    #    todayValue += float(getQuotes(asset)[0]['LastTradePrice']) * quantity
    return jsonify(109.09)



@app.route('/portal', methods=['POST', 'GET'])
@login_required
def portal():
    #CHECK IF SIGNING INTO THE SETTINGS PAGE
    if request.method == 'POST':
        if request.form['text'] == 'CIBPM' and request.form['password'] == 'CIBProjectManager':
            return redirect(url_for('settings'))

    #PULL PORTFOLIO AND HISTORICAL DATA
    CIBPortfolio = UpdateManager.pull_old_portfolios()[0].uncompile()
    tickers = CIBPortfolio.get_tickers()
    assetAllocation = CIBPortfolio.get_asset_allocation()
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    weekAgo = today - timedelta(days=7)
    monthAgo = today - timedelta(days=28)
    threeMonthAgo = today - timedelta(days=86)
    yearAgo = today - timedelta(days=365)

    #PREPARE THE MAIN PERFORMANCE GRAPH
    dailyValuesWeek = historical_values(weekAgo)
    dailyValuesMonth = historical_values(monthAgo)
    dailyValues3Month = historical_values(threeMonthAgo)
    dailyValuesYear = historical_values(yearAgo)

    #PREPARE TODAY'S RETURNS AND VALUE
    todayReturn = get_value() - get_historical_value(yesterday) / get_historical_value(yesterday)
    todayValue = get_value()

    #PREPARE THE ASSET ALLOCATION PIE CHART
    pieChartData = OrderedDict()
    for ticker in tickers:
        pieChartData[ticker] = assetAllocation[ticker]

    #PREPARE THE ASSET PERFORMANCE TABS
    dailyReturns, weeklyReturns, monthlyReturns = {}, {}, {}
    for ticker in tickers:
        if ticker != "Cash":
            priceNow = float(getQuotes(ticker)[0]['LastTradePrice'])
            priceYesterday = get_historical_price(ticker, yesterday)
            priceWeekAgo = get_historical_price(ticker, weekAgo)
            priceMonthAgo = get_historical_price(ticker, monthAgo)
            dailyReturns[ticker] = getReturns(priceYesterday, priceNow)
            weeklyReturns[ticker] = getReturns(priceWeekAgo, priceNow)
            monthlyReturns[ticker] = getReturns(priceMonthAgo, priceNow)

    #PREPARE THE FUND METRICS TAB
    #ytd, mtd = CIBPortfolio.find_YTD_and_monthly_performances()
    ytd = getReturns(get_historical_value(yearAgo), 9000)
    alpha = round(CIBPortfolio.get_alpha(), 2)
    beta = round(CIBPortfolio.get_beta(), 2)
    variance = round(CIBPortfolio.get_variance(), 2)
    sharpe = round(CIBPortfolio.get_sharpe_ratio(), 2)
    information = round(CIBPortfolio.get_information_ratio(), 2)
    fundMetrics = {"todayValue" : todayValue, "todayReturn" : todayReturn,"ytd" : ytd, "alpha" : alpha, "beta" : beta, "variance" : variance, "sharpe" : sharpe, "information" : information}

    #SHOW MOST RECENT EQUITY REPORTS
    equityReports = {'chipotle.pdf' : ["CHIPOTLE MEXICAN GRILL, INC.", "Chipotle Mexican Grill, Inc. is an American fast-food chain of restaurants specializing in Mexican food."],
                    'gilead.pdf' : ["GILEAD SCIENCES", "Gilead Sciences is a research based biopharmaceutical company that discovers, develops, and commercializes medicines primarily in the areas known as 'breakthrough therapies'."],
                    'salesforce.pdf' : ["SALESFORCE.COM INC.", "Salesforce.com Inc is a Customer Relationship Management (CRM) platform for businesses."],
                    'ebs.pdf' : ["EMERGENT BIOSOLUTIONS", "EBS is a specialty biopharmaceutical company that develops, manufactures, and sells specialized products to healthcare providers and governments."],
                    'underarmour.pdf' : ["UNDER ARMOUR INC.", "Under Armour Inc. (UA) is an international athletic apparel, footwear, and accessories distributor."]}

    #RETURN FINAL TEMPLATE
    return render_template('portal.html', metrics=fundMetrics, equityReports=equityReports, dailyValuesYear=dailyValuesYear, dailyValues3Month=dailyValues3Month, dailyValuesMonth=dailyValuesMonth, dailyValuesWeek=dailyValuesWeek, portfolio=CIBPortfolio, pieData=pieChartData, daily=dailyReturns, weekly=weeklyReturns, monthly=monthlyReturns)


@app.route('/risk', methods=['POST', 'GET'])
@login_required
def risk():
    #PULLING PORTFOLIO DATA
    CIBPortfolio = UpdateManager.pull_old_portfolios()[0].uncompile()
    tickers = CIBPortfolio.get_tickers()

    #PREPARE THE COVARIANCE MATRIX HEATMAP
    heatMapData = []
    correlationVector = []
    matrix = CIBPortfolio.get_correlation_matrix()
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            correlationVector.append(matrix[i][j])
    i = 0
    for ticker1 in tickers:
        for ticker2 in tickers:
            heatMapData.append([ticker1, ticker2, round(correlationVector[i], 2)])
            i += 1

    #PREPARE THE MULTIFACTOR MODEL
    sampleWeights = {}
    weightsDict = CIBPortfolio.get_asset_allocation()
    del weightsDict["Cash"]
    #CHECK IF CHANGING THE WEIGHTS
    if request.method == 'POST':
        weightsDict = {}
        for ticker in tickers:
            try:
                weightsDict[ticker] = float(request.form[ticker])
            except:
                continue
        multifactorData = CIBPortfolio.get_exposures(weightsDict)
        for index, exposure in multifactorData.iteritems():
            multifactorData[index] = round(exposure, 3)
    else:
        for key, value in weightsDict.iteritems():
            weightsDict[key] = round(value, 3)
        multifactorData = CIBPortfolio.get_exposures(weightsDict)
        for index, exposure in multifactorData.iteritems():
            multifactorData[index] = round(exposure, 3)
    numStocks = len(tickers) - 1
    equalWeight = round(1.0/numStocks, 3)
    for ticker in tickers:
        if ticker!= "Cash":
            sampleWeights[ticker] = equalWeight

    #PREPARE THE EFFICIENCY FRONTIER GRAPH
    #tangentPortfolio, curve = CIBPortfolio.get_markowitz_analysis()
    curve = {'risks':[], 'returns':[]}
    pointsDict = {}
    print curve
    xPoints = curve['risks']
    yPoints = curve['returns']

    for i in range(len(xPoints)):
        pointsDict[xPoints[i]] = yPoints[i]
    print pointsDict

    return render_template('risk.html', pointsDict=pointsDict, sampleWeights=sampleWeights, weightDict=weightsDict, heatMap=heatMapData, multifactorData=multifactorData)






@app.route('/simulations', methods=['POST', 'GET'])
@login_required
def simulations():
    #PULLING PORTFOLIO DATA AND CALCULATING STATISTICS
    CIBPortfolio = UpdateManager.pull_old_portfolios()[0].uncompile()
    tickers = CIBPortfolio.get_tickers()

    #RUNNING MONTE CARLO SIMULATION
    lowVals, medVals, highVals = [], [], []
    lowVals.append(10000)
    medVals.append(10000)
    highVals.append(10000)

    #HANDLE FORM REQUEST
    simulation = MonteCarlo.Simulation(CIBPortfolio)
    if request.method == 'POST':
        weightsDict = {}
        for ticker in tickers:
            weightsDict[ticker] = request.form[ticker]
        simulation = MonteCarlo.Simulation(CIBPortfolio, weightsDict)
    lowReturns, medReturns, highReturns = simulation.get_full_perf_quartile(1), simulation.get_full_perf_quartile(2), simulation.get_full_perf_quartile(3)
    dates = []
    today = datetime.today()
    future = today + timedelta(days=len(lowReturns))
    delta = future - today
    for i in range(delta.days + 1):
        tempDate = today + timedelta(days=i)
        dates.append(tempDate.strftime("%m-%d-%Y"))
    for i in range(1, len(lowReturns)):
        lowVals.append(lowReturns[i] * 10000)
        medVals.append(medReturns[i] * 10000)
        highVals.append(highReturns[i] * 10000)
    print lowReturns[:10], "Low Returns"
    print medReturns[:10], "Med Returns"
    print highReturns[:10], "High Returns"
    print dates[:10], "dates"
    return render_template('simulations.html', tickers=tickers, dates=dates, low=lowVals, mid=medVals, high=highVals)






@app.route('/research')
@login_required
def research():
    equityReports = {'chipotle.pdf' : ["Chipotle Mexican Grill, Inc.", "Chipotle Mexican Grill, Inc. is an American fast-food chain of restaurants specializing in Mexican food."],
                    'gilead.pdf' : ["Gilead Sciences", "Gilead Sciences is a research based biopharmaceutical company that discovers, develops, and commercializes medicines primarily in the areas known as 'breakthrough therapies'."],
                    'salesforce.pdf' : ["Salesforce.com Inc.", "Salesforce.com Inc is a Customer Relationship Management (CRM) platform for businesses."],
                    'ebs.pdf' : ["Emergent BioSolutions", "EBS is a specialty biopharmaceutical company that develops, manufactures, and sells specialized products to healthcare providers and governments."],
                    'underarmour.pdf' : ["Under Armour Inc.", "Under Armour Inc. (UA) is an international athletic apparel, footwear, and accessories distributor."]}

    return render_template('research.html', equityReports=equityReports)






@app.route('/IV', methods=['POST', 'GET'])
@login_required
def IV():
    labels = []
    if request.method == 'POST':
        tickerA = request.form.get('tickerA')
        tickerB = request.form.get('tickerB')
        tickerAData = request.form.get('tickerAData')
        tickerBData = request.form.get('tickerBData')
        labels.append([tickerA, tickerAData.upper()])
        labels.append([tickerB, tickerBData.upper()])
        chartData = getVolData([tickerA, tickerB], [tickerAData, tickerBData])
    else:
        labels.append(["AAPL", "IV30D"])
        labels.append(["AMZN", "IV30D"])
        chartData = getVolData(['AAPL', 'AMZN'], ['iv30d', 'iv30d'])

    return render_template('IV.html', chartData = chartData, labels=labels)

@app.route('/sentiment', methods=['POST', 'GET'])
def sentiment():
    if request.method == 'POST':
        query = request.form["query"]
        urls = []
        jsonData = gnp.get_google_news_query(query)
        stories = jsonData['stories']
        articleData = []
        session.clear()
        articleID = 0
        for story in stories:
        	urls.append(story["link"])
        for url in urls:
            article = Article(url)
            article.download()
            article.parse()
            if article.title and article.authors and article.publish_date:
                session[articleID] = url
                articleData.append([article.title, article.authors[0], article.publish_date.strftime("%D"), url, articleID])
                articleID += 1
        return render_template('sentiment.html', dirty=True, data=articleData)
    else:
        return render_template('sentiment.html', dirty=False, data="")






@app.route('/performance')
@login_required
def performance():
    assetDict = {'ACM' : 55, 'ADBE' : 13, 'AMD': 87, 'DSKE': 119, 'FCG' : 82}
    cash = 1082
    todayValue = cash
    for asset, quantity in assetDict.iteritems():
        todayValue += float(getQuotes(asset)[0]['LastTradePrice']) * quantity
    start = datetime.now() - timedelta(hours=8)
    return render_template('performance.html', initialValue=todayValue, startDate=start.strftime("%H:%M:%S"))






@app.route('/sponsorship', methods=['POST', 'GET'])
@login_required
def sponsorship():
    if request.method == 'POST':
        FROM = "cibinvestorcontact@gmail.com"
        TO = "scott.post@mac.com"

        msg = MIMEText(request.form['message'])
        msg['Subject'] = 'CIB Investor Inquiry: ' +  request.form['email']
        msg['From'] = FROM
        msg['To'] = TO

        server = smtplib.SMTP('smtp.gmail.com')
        server.starttls()
        server.login(FROM, "CIBFALL2016")
        server.sendmail(FROM, TO, msg.as_string())
        server.quit()
        return render_template('sponsorship.html')

    return render_template('sponsorship.html')






@app.route('/settings', methods=['POST', 'GET'])
@login_required
def settings():
    #PULLING PORTFOLIO DATA
    portfolioInfo = {}
    CIBPortfolio = UpdateManager.pull_old_portfolios()[0].uncompile()
    inPrices = []
    shares = []
    cash = []
    #for ticker in shares:
        #portfolioInfo[ticker] = [inPrices[ticker], shares[ticker], inPrices[ticker] * shares[ticker]]

    tickers = CIBPortfolio.get_tickers()
    #assetAllocation = CIBPortfolio.get_current_asset_allocation()

    if request.method == 'POST':
        with open('./credentials.txt','rb') as f:
            siteCredentials = pickle.load(f)
        try:
            username = request.form['text']
            password = request.form['password']
            siteCredentials[username] = password
            with open('./credentials.txt','wb') as f:
                pickle.dump(siteCredentials, f)
            return render_template('settings.html', cash=cash, portfolioInfo=portfolioInfo,  credentials=siteCredentials, positions = tickers)
        except:
            try:
                removed = request.form['remove']
                del siteCredentials[removed]
                with open('./credentials.txt','wb') as f:
                    pickle.dump(siteCredentials, f)
                return render_template('settings.html', cash=cash, portfolioInfo=portfolioInfo,  credentials=siteCredentials, positions = tickers)
            except:
                ticker = request.form['ticker']
                number = request.form['number']
                value = request.form['value']

        return render_template('settings.html', cash=cash, portfolioInfo=portfolioInfo,  credentials=siteCredentials, positions = tickers)

    with open('./credentials.txt','rb') as f:
        siteCredentials = pickle.load(f)
    return render_template('settings.html', cash=cash, portfolioInfo=portfolioInfo, credentials=siteCredentials, positions = tickers)

#==================================================================================================================================
# SOFTWARE DEVELOPMENT MODELS
#==================================================================================================================================

@app.route('/sentimentModel/<articleID>')
def sentimentModel(articleID):
    url = session[articleID]
    article = Article(url)
    article.download()
    article.parse()
    article.nlp()
    return jsonify(summary=article.summary, keywords=article.keywords, title=article.title)
