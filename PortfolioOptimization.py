from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from time import sleep
from PIL import Image
import pandas as pd

"""
winpty python
from PortfolioOptimization import *
main(cib_portfolio)
"""

cib_portfolio = [('FCG', 21.7), ('AMD', 12.9), ('ABDE', 19.3), ('DSKE', 13.1), ('ACM', 20.8), ('CASH', 12.2)]

def scroll_to_element(driver, element):
    try:
        driver.execute_script("return arguments[0].scrollIntoView();", element)

    except Exception as e:
        print 'error scrolling down web element', e

def inputPortfolio(port, removals, driver):
	needsNormalize = False
	for i in range(len(port)):
		if (i % 10 == 1 and i != 1):
			linkSpan = driver.find_element_by_class_name('add-rows')
			link = linkSpan.find_element_by_tag_name('a')
			link.click()
		if (port[i][0] == 'CASH' or port[i][0] == 'CASH-X'):
			needsNormalize = True
			removals[i] = True
			continue
		sym = driver.find_element_by_id('symbol' + str(i+1))
		sym.clear()
		sym.send_keys(port[i][0])
		alloc = driver.find_element_by_id('allocation' + str(i+1) + '_1')
		alloc.clear()
		alloc.send_keys(str(port[i][1]))
	return removals

def normalize(driver):
	gear = driver.find_element_by_id('allocationOptionsButton1')
	gear.click()
	linkDiv = driver.find_element_by_id('allocation-menu-1')
	linkList = linkDiv.find_elements_by_tag_name('a')
	link = linkList[1] #assert link.text == 'Normalize'
	link.click()

def strFindAll(s, substr):
	results = []
	found = s.find(substr)
	while (found != -1):
		results.append(found)
		found = s.find(substr, found+1)

def searchAndDropItem(symbol, port, removals, driver):
	#find position in list
	pos = -1
	for i in range(len(port)):
		if (port[i][0] == symbol):
			pos = i
			break
	if (pos == -1):
		print(err_msg + 'is not in portfolio list. Something is wrong.')
		return None
	#drop item from portfolio assets in site
	if (removals[pos]):
		return False #item already removed(?)

	removals[pos] = True
	sym = driver.find_element_by_id('symbol' + str(pos+1))
	sym.clear()
	alloc = driver.find_element_by_id('allocation' + str(pos+1) + '_1')
	alloc.clear()
	#clean up mess
	normalize(driver)

	return True
	

def handleError(err_msg, port, removals, driver):
	isUnknown = (err_msg.find('Unknown symbol') != -1)
	isRiskFreeNA = (err_msg.find('Risk free') != -1)
	if (isUnknown):
		#get unknown symbol
		unknown = err_msg[16:]
		removed = searchAndDropItem(unknown, port, removals, driver)

	if (isRiskFreeNA):
		naStart = err_msg.find('(') + 1
		naEnd = err_msg.find(')')
		na = err_msg[naStart:naEnd]
		if (na == 'CASHX'):
			na = 'CASH'
		removed = searchAndDropItem(na, port, removals, driver)

	if (isUnknown == False and isValidRange == False):
		#Unhandled error
		print("Unhandled error: " +  err_msg)
		return False

	return removed

def inputTime(start, end, driver):
	if (start < 1985 or start > 2016 or end < 1985 or end > 2017):
		return False
	#Set start year
	start_year_box = driver.find_element_by_id('startYear_chosen')
	b_box = start_year_box.find_elements_by_tag_name('b')[0]
	b_box.click()
	start_year_box = driver.find_element_by_id('startYear_chosen')
	ul = start_year_box.find_elements_by_tag_name('ul')[0]
	li_items = ul.find_elements_by_tag_name('li')
	li_index = start - 1985
	li_items[li_index].click()

	#Set end year
	end_year_box = driver.find_element_by_id('endYear_chosen')
	b_box = end_year_box.find_elements_by_tag_name('b')[0]
	b_box.click()
	end_year_box = driver.find_element_by_id('endYear_chosen')
	ul = end_year_box.find_elements_by_tag_name('ul')[0]
	li_items = ul.find_elements_by_tag_name('li')
	li_index = end - 1985
	#scroll to top of dropdown because selection is kinda buggy
	for i in range(32):
		b_box.send_keys(u'\ue013')
	li_items[li_index].click()
	
	return True

def main(portfolio, startYear=1985, endYear=2017):

	driver = webdriver.Firefox()
	driver.get("https://www.portfoliovisualizer.com/optimize-portfolio")
	sleep(2)
	
	#Input Info
	removals = [False for i in range(len(portfolio))]
	inputPortfolio(portfolio, removals, driver)
	isValidRange = inputTime(startYear, endYear, driver)
	
	submit = driver.find_element_by_id("submitButton")
	submit.click()
	sleep(2)

	#Get errors and info
	err_boxes = driver.find_elements_by_css_selector(".alert-danger")

	#Print out any errors, such as not having ABDE's information
	if (len(err_boxes) != 0):
		print(err_boxes[0].text)
		#DO MORE ADVANCED ERROR HANDLING HERE

		#First Round Error Check - Unknown Symbols show up before risk-free-not-allowed
		err_text = err_boxes[0].text
		errs = err_text.split('\n')
		for e in errs:
			handleError(e, portfolio, removals, driver)
		
		submit = driver.find_element_by_id("submitButton")
		submit.click()
		sleep(2)
		
		#Second Round Error Check - Risk-Free Not Allowed shows up here after unknown symbols dropped
		err_boxes = driver.find_elements_by_css_selector(".alert-danger")
		if (len(err_boxes) != 0):
			print(err_boxes[0].text)
			for e in errs:
				handleError(e, portfolio, removals, driver)
		
				submit = driver.find_element_by_id("submitButton")
				submit.click()
				sleep(2)

				#Third Check - at this point, stop.
				err_boxes = driver.find_elements_by_css_selector(".alert-danger")
				if (len(err_boxes) != 0):
					print(err_boxes[0].text)
					print("Not all errors were handled!!!")
					return None

	#Print out any notes, such as invalid time ranges that get automatically adjusted by the site
	#Update: invalid time ranges now cause offending symbol to get dropped
	remaining =  [i for i in range(len(removals)) if removals[i] == False]
	for index in remaining:
		info_boxes = driver.find_elements_by_css_selector(".alert-info")
		if (len(info_boxes) != 0):
			msg = info_boxes[0].text
			print(msg[8:]) #first 8 letters contain non-unicode/irrelevant text
			split_list = msg.split('(')
			if (len(split_list) >= 2):
				bad_symbol = split_list[2][:-1]
				searchAndDropItem(bad_symbol, portfolio, removals, driver)
				submit = driver.find_element_by_id("submitButton")
				submit.click()
				sleep(2)

	#Check no errors occurred in removal (e.g. less than two assets left)
	err_boxes = driver.find_elements_by_css_selector(".alert-danger")
	if (len(err_boxes) != 0):
		print(err_boxes[0].text)
		for e in errs:
			isHandled = handleError(e, portfolio, removals, driver)
			submit = driver.find_element_by_id("submitButton")
			submit.click()
			sleep(2)
			if (isHandled == False):
				return None

	#Get Max. Sharpe Ratio Allocations
	port_allocs = driver.find_element_by_id('growthChart')
	ports = port_allocs.find_elements_by_tag_name('table')

	provided_port = ports[1]
	max_sharpe_port = ports[3]
	
	max_sharpe_alloc = pd.read_html(max_sharpe_port.get_attribute('outerHTML'))[0]

	#USE PORTFOLIO ALLOCS HERE !!!
	#Get Portfolio Growth Graph, because why not.
	chart_container = driver.find_element_by_id('chartDiv3')
	chart_tbl = chart_container.find_elements_by_tag_name('table')[0]
	chart_tbl_html = chart_tbl.get_attribute('outerHTML')
	chart_df = pd.read_html(chart_tbl_html)[0]

	#USE SCRAPED DATAFRAME HERE!!!

	####################################################################################
	#Get Metrics - Alpha, Beta, Sharpe, Sortino, Max. Drawdown, and etc.

	#Select Metrics tab
	li = driver.find_elements_by_css_selector("li[role*='presentation']")[1].click()

	#Get Metrics Table
	met_div = driver.find_element_by_id('metrics')
	met_tbl = met_div.find_elements_by_tag_name('table')[1]
	met_tbl_html = met_tbl.get_attribute('outerHTML')

	#scrape the whole table into a dataframe for more potential uses
	dfs = pd.read_html(met_tbl_html) 
	df = dfs[0]
	df.columns = ['Metric','Provided Portfolio','Max Sharpe Porfolio']

	#USE SCRAPED DATAFRAME HERE!!!

	####################################################################################
	#Get efficient frontier stuff

	#Select Efficient Frontier Tab
	li = driver.find_elements_by_css_selector("li[role*='presentation']")[2].click()

	eff_frontier_container = driver.find_element_by_id('efficientFrontier')
	#Get headers
	ef_head = eff_frontier_container.find_elements_by_tag_name('table')[3]
	ef_head_html = ef_head.get_attribute('outerHTML')
	ef_head_df = pd.read_html(ef_head_html)[0]
	#Get Data
	eff_frontier_tbl = eff_frontier_container.find_elements_by_tag_name('table')[4]
	eff_frontier_tbl_html = eff_frontier_tbl.get_attribute('outerHTML')
	eff_frontier_df = pd.read_html(eff_frontier_tbl_html)[0]
	#Clean it up a bit
	eff_frontier_df.columns = ef_head_df.columns
	eff_frontier_df = eff_frontier_df.drop('#', axis=1)

	#USE SCRAPED DATAFRAME HERE!!!

	####################################################################################
	#Get Asset Correlation Matrix

	#Select Assets Tab
	li = driver.find_elements_by_css_selector("li[role*='presentation']")[6].click()

	assets_container = driver.find_element_by_id('portfolioComponents')
	assets_tables = assets_container.find_elements_by_tag_name('table')

	port_assets_head = assets_tables[0]
	port_assets = assets_tables[1]
	
	monthly_correlations_head = assets_tables[2]
	monthly_correlations = assets_tables[3]
	mc_head_html = monthly_correlations_head.get_attribute('outerHTML')
	mc_head_df = pd.read_html(mc_head_html)[0]
	mc_html = monthly_correlations.get_attribute('outerHTML')
	mc_df = pd.read_html(mc_html)[0]
	mc_df.columns = mc_head_df.columns

	#Use mc_df (monthly correlations data frame/matrix) here!!!
	print(mc_df)
	#driver.quit()

	#Chart Scraping Note - the thing I did for the efficient frontier chart vs the other chart comparing 
	#portfolio allocations did not work for EF, because chartDiv5 (the one for EF) doesn't have the same
	#neat data for  it's graph  (probably because it's all below where it's intended to be copied from)

main(cib_portfolio, 2007, 2016)