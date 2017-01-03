from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from newspaper import Article
import gnp
import pickle
import urllib2
from pandas.io.data import DataReader
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from googlefinance import getQuotes
import UpdateManager
import MonteCarlo
import CIBDatabase
from collections import OrderedDict
from dateutil import rrule
from optionchain import OptionChain
from yahoo_finance import Share
import math