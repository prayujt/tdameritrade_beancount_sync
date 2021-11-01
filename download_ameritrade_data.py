from td.client import TDClient
import smtplib
import pandas
from datetime import datetime, timedelta, date, time
import yfinance as finance
import json
import re

ACCOUNT_NUMBER = 'XXXXXXXXX'
CLIENT_ID='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
REDIRECT_URI='http://localhost'

realizedGainsFile = ''
unrealizedGainsFile = ''

TDSession = TDClient(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI, credentials_path='/path/to/credentials/file')

TDSession.login()

balance = (TDSession.get_accounts(account=ACCOUNT_NUMBER, fields=[]))['securitiesAccount']['currentBalances']
balance = float(balance['cashBalance']) + float(balance['moneyMarketFund'])

history = pandas.read_excel(realizedGainsFile)
current = pandas.read_excel(unrealizedGainsFile)

heading = 'option \"booking_method\" \"FIFO\"'
opens = '\n\n'
closes = ''
text = '\n\n'
holdings = {}

def add_to_holdings(symbol, open_date, close_date):
    if symbol in holdings.keys():
        if toDate(open_date) < toDate(holdings[symbol][0]):
            holdings[symbol] = (open_date, holdings[symbol][1])
        if close_date == 0:
            holdings[symbol] = (holdings[symbol][0], 0)
        elif toDate(close_date) > toDate(holdings[symbol][1]):
            holdings[symbol] = (holdings[symbol][0], close_date)
    else:
        holdings[symbol] = (open_date, close_date)

def toDate(x):
    return datetime.strptime(str(x), '%Y-%m-%d')

for index, row in history.iterrows():
    open_date = str(row['Open date']).split(' ')[0]
    quantity = row['Qty']
    value = row['Adj cost']
    price = round(value / quantity, 2)
    security = row['Security']
    close_date = str(row['Close date']).split(' ')[0]
    value = row['Adj proceeds']
    profit = row['Adj gain($)']
        
    if row['Trans type'] == 'Wash Sale Adj':
        line1 = str(open_date) + ' * \"Wash sale adjustment for ' + security + '\"'    
        line2 = '\n\t' + "Income:TDAmeritrade:CapitalGains\t-" + str(profit) + ' USD'
        line3 = '\n\t' + "Assets:TDAmeritrade:Brokerage:Cash\n\n"
        
        text += line1 + line2 + line3
        continue
    
    elif row['Trans type'] == 'Sell.FIFO':
        symbol = re.search(r"\(([A-Za-z0-9_]+)\)", security).group(1)
        if symbol == 'V':
            symbol = 'VISA'

    elif row['Trans type'] == 'Sell to Close.FIFO':
        temp = security.split(' ')
        symbol = temp[0] + '-' + str(round(float(temp[4]))).split('.')[0] + '-' + str(temp[5])[0]

    else:
        break

    add_to_holdings(symbol, open_date, close_date)
    line1 = str(open_date) + ' * \"Buy ' + security + '\"'
    line2 = '\n\t' + "Assets:TDAmeritrade:Brokerage:" + symbol + '\t' + str(quantity) + " " + symbol + " {" + str(price) + " USD}"
    line3 = '\n\t' + "Assets:TDAmeritrade:Brokerage:Cash\n\n"

    line4 = str(close_date) + ' * \"Sell ' + security + '\"'
    line5 = '\n\t' + "Assets:TDAmeritrade:Brokerage:" + symbol + '\t-' + str(quantity) + " " + symbol + " {}"
    line6 = '\n\t' + "Assets:TDAmeritrade:Brokerage:Cash" + '\t' + str(value) + ' USD'
    line7 = '\n\t' + "Income:TDAmeritrade:CapitalGains\t-" + str(profit) + ' USD'

    if row['Trans type'] == 'Sell to Close.FIFO':
        line8 = '\n\t' + 'Expenses:TDAmeritrade:Commissions\n\n'
    else:
        line8 = '\n\t' + "Equity:Rounding\n\n"

    text += line1 + line2 + line3 + line4 + line5 + line6 + line7 + line8

for index, row in current.iterrows():
    open_date = str(row['Open date']).split(' ')[0]
    quantity = row['Qty']
    price = row['Adj cost per share']
    security = row['Security']
    try:
        symbol = re.search(r"\(([A-Za-z0-9_]+)\)", security).group(1)
        if symbol == 'V':
            symbol = 'VISA'
    except AttributeError:
        continue
    add_to_holdings(symbol, open_date, 0)
    line1 = str(open_date) + ' * \"Buy ' + security + '\"'
    line2 = '\n\t' + "Assets:TDAmeritrade:Brokerage:" + symbol + '\t' + str(quantity) + " " + symbol + " {" + str(price) + " USD}"
    line3 = '\n\t' + "Assets:TDAmeritrade:Brokerage:Cash\n\n"

    text += line1 + line2 + line3

for symbol in holdings.keys():
    opens += '\n' + str(holdings[symbol][0]) + " open Assets:TDAmeritrade:Brokerage:" + str(symbol)
    if holdings[symbol][1] != 0:
        closes += '\n' + str(holdings[symbol][1]) + " close Assets:TDAmeritrade:Brokerage:" + str(symbol)
        
pad = '\n\n' + str(datetime.date(datetime.now())) + ' pad Assets:TDAmeritrade:Brokerage:Cash Equity:Rounding\n' + str(datetime.date(datetime.now()) + timedelta(days=1)) + ' balance Assets:TDAmeritrade:Brokerage:Cash ' + str(balance) + ' USD'

fileText = heading + opens + text + pad + closes
beancountFile = open('/path/to/beancount/file', 'w')
beancountFile.write(fileText)
beancountFile.close()
