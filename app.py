import json, config
from flask import Flask, request
from binance.client import Client
from binance.enums import *

app = Flask(__name__)

#Binance
client = Client(config.API_KEY, config.API_SECRET)


@app.route('/binance_futures_BNBUSDT', methods=['POST'])
def binance_futures_long():
    # Load data from post
    # data = json.loads(request.data)

    client.futures_change_leverage(symbol="BNBUSDT", leverage=75)
    client.futures_change_margin_type(symbol="BNBUSDT", marginType='CROSSED')

    for i in client.futures_account()['positions']:
        if i['symbol'] == "BNBUSDT":
            return(i)

@app.route('/binance_futures_trade', methods=['POST'])
def binance_futures_trade():
    # Load data from post
    data = json.loads(request.data)

    if data['side'] == 'LONG':
        takeProfit = float(data['close']) + ((float(data['close']) * 0.15) / 75)
        takeProfit = round(takeProfit, 2)

        client.futures_create_order(symbol="BNBUSDT", side=SIDE_BUY, positionSide='LONG', type=ORDER_TYPE_MARKET,  quantity=10, isolated=False)
        client.futures_create_order(symbol="BNBUSDT", side=SIDE_SELL, type=FUTURE_ORDER_TYPE_LIMIT, quantity=10, positionSide='LONG', price=takeProfit, timeInForce=TIME_IN_FORCE_GTC)
    
    elif data['side'] == 'SHORT':
        client.futures_cancel_all_open_orders(symbol="BNBUSDT")
        client.futures_create_order(symbol="BNBUSDT", side=SIDE_SELL, positionSide='LONG', type=ORDER_TYPE_MARKET,  quantity=10, isolated=False)
    
    return("Done")


# Home page
# @app.route('/')
# def welcome():
#     balances = client.get_account()['balances']

#     return render_template('index.html', balances=balances, trading_bots=trading_bots)
