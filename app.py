import json, config

import requests
from math import floor
from flask import Flask, request, render_template
from binance.client import Client
from binance.enums import *

app = Flask(__name__)

client = Client(config.API_KEY, config.API_SECRET)

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
    info = client.get_account()['balances']

    return render_template('index.html', balances=info)

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
        assets = client.get_asset_balance(asset="BUSD")
        price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=CAKEBUSD").json()
        quantity = float((float(assets['free']) / float(price['price']))*0.9995)

    # Sell case
    elif side == "SELL":
        assets = client.get_asset_balance(asset="CAKE")
        quantity = float(assets['free'])

    exchange = data['ticker']
    order_response = order(side, round(quantity - 0.001, 3), exchange)

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

    return(data)