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

credentialsFile = '/path/to/credentials'
beancountPricesFile = '/path/to/prices/file'

TDSession = TDClient(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI, credentials_path=credentialsFile)

TDSession.login()

priceText = ''
positions = TDSession.get_accounts(account=ACCOUNT_NUMBER, fields=['positions'])
for position in positions['securitiesAccount']['positions']:
    symbol = position['instrument']['symbol']
    if symbol != 'MMDA1':
        price = TDSession.get_quotes([symbol])[symbol]['lastPrice']
        if symbol == 'V':
            symbol = 'VISA'
        priceText += str(datetime.now())[:10] + ' price ' + str(symbol) + '\t' + str(price) + ' USD\n'

priceFile = open(beancountPricesFile, 'a')
priceFile.write(priceText)
priceFile.close()
