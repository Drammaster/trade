import json, config
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *
app = Flask(__name__)

client = Client(config.API_KEY, config.API_SECRET, tld="us")

def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    try:
        print("Sending order {order_type} - {side} {quantity} {symbol}")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        print(order)
    except Exception as e:
        print("An exception occured - {}".format(e))
        return False

    return True

@app.route('/')
def hello_world():
    return 'Hello Csaba!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = json.loads(request.data)

    if data['passhrase'] != config.WEBHOOK_PHRASE:
        return {
            "code": "error",
            "message": "Nice try, invalid passphrase"
        }

    print(data["ticker"])
    print(data["bar"])

    side = data['strategy']['order_action'].upper()
    quantity = data['strategy']['order_contracts']

    order_response = order(side, quantity, "DOGEUSD")

    if order_response:
        return{
            "code": "success",
            "message": "order success"
        }
    else: 
        print("order failed")

        return {
            "code": "error",
            "message": "order failed"
        }