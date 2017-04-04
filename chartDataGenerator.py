import json

def generateJsonData(valuesDict, filename):
	"""
	Use to generate the data for FusionCharts to minimize redudant templating operations.
	Works for: day, value in dailyValuesWeek, dailyValuesMonth, dailyValues3Month, dailyValuesYear
			 : ticker, weight in pieData
	Filename naming convention: 'chartData_' + dict name. e.g. filename='chartData_dailyValuesWeek'
	"""
	array = []
	for label, value in valuesDict.iteritems():
		dataPoint = {'label' : label, 'value' : value}
		array.append(dataPoint)
	fullFillname = filename + '.json'
	with open(fullFillname, 'w', encoding="utf-8") as outfile:
		json.dump(array, outfile)