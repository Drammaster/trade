import json, config
from flask import Flask, request, render_template
from binance.client import Client
from binance.enums import *

app = Flask(__name__)


#Binance
client = Client(config.API_KEY, config.API_SECRET)


@app.route('/binance_futures_trade', methods=['POST'])
def binance_futures_trade():
    # Load data from post
    data = json.loads(request.data)

    # Check for security phrase
    if data['passphrase'] != config.WEBHOOK_PHRASE:
        return {
            "code": "error",
            "message": "Nice try, invalid passphrase"
        }

    if data['side'] == 'LONG':
        if data['action'] == "OPEN":
            if data['using_roe'] == True:
                takeProfit = float(data['close']) + ((float(data['close']) * data['profit']) / data['leverage'])
            else:
                takeProfit = float(data['close']) + (float(data['close']) * (data['profit']/100))
            takeProfit = round(takeProfit, 2)

            client.futures_create_order(symbol=data['exchange_pair'], side=SIDE_BUY, positionSide='LONG', type=ORDER_TYPE_MARKET,  quantity=data['volume'], isolated=False)
            client.futures_create_order(symbol=data['exchange_pair'], side=SIDE_SELL, type=FUTURE_ORDER_TYPE_LIMIT, quantity=data['volume'], positionSide='LONG', price=takeProfit, timeInForce=TIME_IN_FORCE_GTC)
        
        if data['action'] == "CLOSE":
            client.futures_cancel_all_open_orders(symbol=data['exchange_pair'])
            client.futures_create_order(symbol=data['exchange_pair'], side=SIDE_SELL, positionSide='LONG', type=ORDER_TYPE_MARKET,  quantity=data['volume'], isolated=False)

    elif data['side'] == 'SHORT':
        if data['action'] == "OPEN":
            if data['using_roe'] == True:
                takeProfit = float(data['close']) + ((float(data['close']) * data['profit']) / data['leverage'])
            else:
                takeProfit = float(data['close']) + (float(data['close']) * (data['profit']/100))
            takeProfit = round(takeProfit, 2)

            client.futures_create_order(symbol=data['exchange_pair'], side=SIDE_BUY, positionSide='SHORT', type=ORDER_TYPE_MARKET,  quantity=data['volume'], isolated=False)
            client.futures_create_order(symbol=data['exchange_pair'], side=SIDE_SELL, type=FUTURE_ORDER_TYPE_LIMIT, quantity=data['volume'], positionSide='SHORT', price=takeProfit, timeInForce=TIME_IN_FORCE_GTC)
        
        if data['action'] == "CLOSE":
            client.futures_cancel_all_open_orders(symbol=data['exchange_pair'])
            client.futures_create_order(symbol=data['exchange_pair'], side=SIDE_SELL, positionSide='SHORT', type=ORDER_TYPE_MARKET,  quantity=data['volume'], isolated=False)

    return("Done")


# Home page
@app.route('/')
def welcome():

    return render_template('index.html')
