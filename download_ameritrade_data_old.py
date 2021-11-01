from td.client import TDClient
import smtplib
import pandas
from datetime import datetime, timedelta, date, time
import yfinance as finance
import json

ACCOUNT_NUMBER = 'XXXXXXXXX'
CLIENT_ID='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
REDIRECT_URI='http://localhost'

credentialsLocation = 'path/to/ameritrade/credentials/'
holdingsLocation = '/path/to/holdings/file'
textLocation = '/path/to/text/file'
beancountLocation = '/path/to/beancount/file'

TDSession = TDClient(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI, credentials_path=credentialsLocation)

TDSession.login()

#orders = TDSession.get_orders_path(account=ACCOUNT_NUMBER, from_entered_time="2021-04-13", to_entered_time="2021-05-18")
orders = TDSession.get_orders_path(account=ACCOUNT_NUMBER)
balance = (TDSession.get_accounts(account=ACCOUNT_NUMBER, fields=[]))['securitiesAccount']['currentBalances']
balance = float(balance['cashBalance']) + float(balance['moneyMarketFund'])
holdingsFile = open(holdingsLocation, 'r+')
content = holdingsFile.read().replace('\'', '\"')
holdings = json.loads(content)
holdingsFile.close()

bodyFile = open(textLocation, 'r')
text = str(bodyFile.read())
bodyFile.close()

def add_to_holdings(symbol, quantity, date, action):
    done = False
    for num in range(0, len(holdings)):
        previousDate = holdings[num][2]
        if len(holdings) == 0:
            break
        if holdings[num][0] == symbol and orderType == "BUY":
            previousQuantity = holdings[num][1]
            holdings[num] = [symbol, previousQuantity + quantity, previousDate, date]
            done = True
        elif holdings[num][0] == symbol and orderType == "SELL":
            previousQuantity = holdings[num][1]
            holdings[num] = [symbol, previousQuantity - quantity, previousDate, date]
            done = True
    if not done:
        if orderType == "BUY":
            holdings.append([symbol, quantity, date, str(None)])
        else:
            holdings.append([symbol, -quantity, date, str(None)])

def time_in_range(start, end, x):
    #return True
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end

raw_df = pandas.DataFrame(orders)
orders_df = pandas.DataFrame([])
try:
    orders_df = raw_df.loc[raw_df['status'] == 'FILLED']
except KeyError:
    pass

#orders_df = orders_df.reindex(index=orders_df.index[::-1])
processed_orders = []

for index, row in orders_df.iterrows():
    execute_time = datetime.time(datetime.strptime(row['enteredTime'].split('T')[1].split('+')[0], '%H:%M:%S') + timedelta(hours=-4))
    current_time = datetime.strftime(datetime.now(), '%H:%M:%S')
    hour = int((str(current_time)[:2])) - 1
    lower_time = time(hour-1, 0, 0)
    upper_time = time(hour-1, 59, 59)
    if time_in_range(lower_time, upper_time, execute_time):
        symbol = row['orderLegCollection'][0]['instrument']['symbol']
        if symbol == 'V':
            symbol = 'VISA'
        action = row['orderLegCollection'][0]['instruction']
        quantity = row['filledQuantity']
        price = row['price']
        processed_orders.append({'symbol': symbol, 'quantity': quantity, 'price': price, 'action': action})

heading = 'option \"booking_method\" \"FIFO\"'
opens = "\n\n2021-03-19 open Income:TDAmeritrade:CapitalGains"
closes = "\n"
commodities = "\n"
showPrices = False

bodyFile = open('/home/pi/.ameritrade_text', 'a')
for i in range(len(processed_orders)):
    orderType = processed_orders[i]['action']

    if orderType == 'BUY':
        symbol = processed_orders[i]['symbol']
        quantity = processed_orders[i]['quantity']
        price = processed_orders[i]['price']
        date = str(datetime.date(datetime.now()))
        add_to_holdings(symbol, quantity, date, action)

        line1 = '\n\n' + str(date) + ' * \"Buy ' + symbol + '\"'
        line2 = '\n\t' + "Assets:TDAmeritrade:Brokerage:" + symbol + '\t' + str(quantity) + " " + symbol + " {" + str(price) + " USD}"
        line3 = '\n\t' + "Assets:TDAmeritrade:Brokerage:Cash"
        text += line1 + line2 + line3
        bodyFile.write(line1 + line2 + line3)
        print(line1 + line2 + line3)
        showPrices = True

    elif orderType == 'SELL':
        symbol = processed_orders[i]['symbol']
        quantity = processed_orders[i]['quantity']
        price = processed_orders[i]['price']
        date = str(datetime.date(datetime.now()))
        add_to_holdings(symbol, quantity, date, action)

        line1 = '\n\n' + str(date) + ' * \"Sell ' + symbol + '\"'
        line2 = '\n\t' + "Assets:TDAmeritrade:Brokerage:" + symbol + '\t-' + str(quantity) + " " + symbol + " {}"
        line3 = '\n\t' + "Assets:TDAmeritrade:Brokerage:Cash" + '\t' + str(quantity * price) + ' USD'
        line4 = '\n\t' + "Income:TDAmeritrade:CapitalGains"
        text += line1 + line2 + line3 + line4
        bodyFile.write(line1 + line2 + line3 + line4)
        print(line1 + line2 + line3 + line4)
        showPrices = True

priceText = '\n'
for positions in holdings:
    openLine = '\n' + str(positions[2]) + " open Assets:TDAmeritrade:Brokerage:" + str(positions[0])
    opens += openLine
    commodityLine = '\n' + str(positions[2]) + " commodity " + str(positions[0]) + '\n\t' + "price: \"USD:yahoo/" + str(positions[0]) + "\""
    commodities += commodityLine
    if int(positions[1]) == 0:
        lastDate = positions[3]
        if positions[2] == lastDate:
            lastDate = str(datetime(int(lastDate[:4]), int(lastDate[5:7]), int(lastDate[8:])) + timedelta(days=1))[:10]
        closeLine = '\n' + str(lastDate) + " close Assets:TDAmeritrade:Brokerage:" + str(positions[0])
        closes += closeLine
    else:
        #update prices for these
        data = finance.download(tickers=str((positions[0], 'V')[positions[0] == 'VISA']), period='1ho', interval='1m')
        result = round(data.tail(1)['Close'].iloc[0], 4)
        priceText += str(datetime.now())[:10] + ' price ' + str(positions[0]) + '\t' + str(result) + ' USD\n'

pad = '\n\n' + str(datetime.date(datetime.now())) + ' pad Assets:TDAmeritrade:Brokerage:Cash Expenses:TDAmeritrade:Commissions\n' + str(datetime.date(datetime.now()) + timedelta(days=1)) + ' balance Assets:TDAmeritrade:Brokerage:Cash ' + str(balance) + ' USD'

current_time = datetime.strftime(datetime.now(), '%H:%M:%S')
hour = int((str(current_time)[:2])) - 1

if hour == 16 or showPrices:
    priceFile = open('/home/pi/finances/2021.prices', 'a')
    priceFile.write(priceText)
    priceFile.close()


holdingsFile = open(holdingsLocation, 'w')
holdingsFile.write(str(holdings))
holdingsFile.close()

textFile = open(textLocation, 'w')
textFile.write(text)
textFile.close()

beancountFile = open(beancountLocation, 'w')
beancountFile.write(heading + opens + text + pad + closes)
beancountFile.close()
