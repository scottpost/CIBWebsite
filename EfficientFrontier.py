from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from time import sleep
from PIL import Image

def scroll_to_element(driver, element):
    try:
        driver.execute_script("return arguments[0].scrollIntoView();", element)

    except Exception as e:
        print 'error scrolling down web element', e

driver = webdriver.Firefox()
driver.get("https://www.portfoliovisualizer.com/efficient-frontier?s=y&s=y&type=1&mode=2&startYear=2013&endYear=2016&fromOrigin=false&symbol1=FCG&allocation1_1=30.20&symbol2=AMD&allocation2_1=16.44&symbol3=ADBE&allocation3_1=25.74&symbol4=ACM&allocation4_1=27.62")
sleep(2)
submit = driver.find_element_by_id("submitButton")
scroll_to_element(driver, submit)
li = driver.find_elements_by_css_selector("li[role*='presentation']")[2].click()
driver.save_screenshot("screenshot.png")

cells = driver.find_elements_by_css_selector("td[class*='numberCell']")

data = []
length = 8
for cell in cells:
	data.append(cell.text)
data = filter(None, data)

i = 0
row = []
cur = 0
rows = []
while i < len(data):
	if cur != 7:
		row.append(data[i])
		cur += 1
	else:
		row.append(data[i])
		rows.append(row)
		row = []
		cur = 0
	i += 1
print rows




driver.quit()