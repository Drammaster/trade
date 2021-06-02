import json, config

import requests
from math import floor
from flask import Flask, request, render_template
from binance.client import Client
from binance.enums import *

app = Flask(__name__)

trading_bots = [
    {
        'name': "Cake Bot",
        'exchange_pair': "CAKEBUSD",
        'crypto': 'CAKE',
        'hold': 23,
        'holds': False,
        'initial': 200,
        'profit': 0,
        '7days': 0,
    },
    {
        'name': "Bitcoin Bot",
        'exchange_pair': "BTCBUSD",
        'crypto': 'BTC',
        'hold': 77,
        'holds': False,
        'initial': 800,
        'profit': 0,
        '7days': 0,
    }
]

client = Client(config.API_KEY, config.API_SECRET)

def add_bot(new_bot):

    balances = client.get_account()['balances']

    wallet_total = 0 #Wallet total in USD
    for i in balances:
        if i['free'] != "0.00000000":
            if i['free'] != "0.00":
                if i['asset'] != "BUSD":
                    price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + i['asset'] + "BUSD").json()
                    wallet_total += float(price['price']) * float(i['free'])
                else:
                    price = i['free']
                    wallet_total += float(price)
                print(i, price)

    for x in trading_bots:
        x['hold'] = wallet_total * (x['hold'] / 100) #Change bot holds to amount

    wallet_total += new_bot['hold'] #Add new Bots hold

    trading_bots.append(new_bot) #Add new Bot

    for x in trading_bots:
        x['hold'] = (x['hold'] / wallet_total) * 100   #Change bot holds to %


# Live trading function
def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    try:
        print(f"sending order {order_type} - {side} {quantity} {symbol}")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return order

# Test trading function
def testorder(side, quantitytest, symbol, order_type=ORDER_TYPE_MARKET):
    try:
        print(f"sending order {order_type} - {side} {quantitytest} {symbol}")
        order = client.create_test_order(symbol=symbol, side=side, type=order_type, quantity=quantitytest)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return order

# Home page
@app.route('/')
def welcome():
    balances = client.get_account()['balances']

    for i in trading_bots:
        price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + i['exchange_pair']).json()
        i['profit'] = i['initial'] - (price['price'] * client.get_asset_balance(asset='BTC'))

    return render_template('index.html', balances=balances, bots=trading_bots)

# Live trade webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    # Load data from post
    data = json.loads(request.data)
    
    # Check for security phrase
    if data['passphrase'] != config.WEBHOOK_PHRASE:
        return {
            "code": "error",
            "message": "Nice try, invalid passphrase"
        }

    side = data['strategy']['order_action'].upper()

    
    # Buy case
    if side == "BUY":
        allowence = 0
        for i in trading_bots:
            if i['exchange_pair'] == data['ticker'] and i['holds'] == False:
                allowence += i['hold']
                i['holds'] = True
            # elif i['exchange_pair'] == data['ticker']:
            #     i['holds'] = True
            #     print(i)
            assets = client.get_asset_balance(asset="BUSD")
            price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + data['ticker']).json()
            quantity = float(((float(assets['free'])*(allowence/100)) / float(price['price']))*0.9995)

    # Sell case
    elif side == "SELL":
        for i in trading_bots:
            if i['exchange_pair'] == data['ticker']:
                i['holds'] = False
        assets = client.get_asset_balance(asset=data['crypto'])
        quantity = float(assets['free'])

    exchange = data['ticker']
    if data['ticker'] == 'CAKEBUSD':
        if quantity > 0:
            order_response = order(side, round(quantity - 0.001, 3), exchange)
        else:
            order_response = True
    elif data['ticker'] == 'BTCBUSD':
        if quantity > 0:
            order_response = order(side, round(quantity - 0.000001, 6), exchange)
        else:
            order_response = True
    elif data['ticker'] == 'BNBBUSD':
        if quantity > 0:
            order_response = order(side, round(quantity - 0.0001, 4), exchange)
        else:
            order_response = True

    if order_response:
        return {
            "code": "success",
            "message": "order executed"
        }
    else:
        if float(client.get_asset_balance(asset="BUSD")['free']) > 10:
            webhook()
        else:
            return {
                "code": "error",
                "message": "not enought funds"
            }

# Test trade webhook
@app.route('/test', methods=['POST'])
def test():
    data = json.loads(request.data)
    
    if data['passphrase'] != config.WEBHOOK_PHRASE:
        return {
            "code": "error",
            "message": "Nice try, invalid passphrase"
        }

    side = data['strategy']['order_action'].upper()
    quantity = data['strategy']['order_contracts']
    exchange = data['ticker']
    order_response = testorder(side, quantity, exchange)

    if order_response:
        return {
            "code": "success",
            "message": "order executed"
        }
    else:
        print("order failed")

        return {
            "code": "error",
            "message": "order failed"
        }

@app.route('/set', methods=['POST'])
def initial():
    # Load data from post
    data = json.loads(request.data)

    # Check for security phrase
    if data['passphrase'] != config.WEBHOOK_PHRASE:
        return {
            "code": "error",
            "message": "Nice try, invalid passphrase"
        }
    
    side = data['strategy']['order_action'].upper()

    
    # Buy case
    if side == "BUY":
        allowence = 100
        for i in trading_bots:
            if i['exchange_pair'] != data['ticker'] and i['holds'] == True:
                allowence -= i['hold']
        assets = client.get_asset_balance(asset="BUSD")
        price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + data['ticker']).json()
        quantity = float(((float(assets['free'])*(allowence/100)) / float(price['price']))*0.9995)
    
    return({
        'Status': client.get_account_status(),
        'Snapshot': client.get_account_snapshot(),
        'Fees': client.get_my_trades(symbol="CAKEBUSD")
        })

# Home page
@app.route('/parallax')
def parallax():
    return render_template('parallax.html')


@app.route('/createbot', methods=['POST'])
def create_bot():
    # Load data from post
    data = json.loads(request.data)

    name = data['name']
    exchange_pair = data['exchange_pair']
    hold = data['hold']

    new_bot = {
        'name': name,
        'exchange_pair': exchange_pair,
        'hold': hold,
        'holds': False
    }

    add_bot(new_bot)

    return({
        'Message': "success",
        'Bots': trading_bots
    })
