import pandas as pd

def makeTable(inputHtmlText):
	return pd.read_html(inputHtmlText)