import json, config
import time
import requests
from flask import Flask, request
from binance.client import Client
from binance.enums import *
from binance.websockets import BinanceSocketManager

app = Flask(__name__)

trading_bots = [
    {
        "name": "CAKE Long Bot",
        "bot_id": "001",
        "broker":"Binance",
        "exchange_pair": "CAKEUSDT",
        "strategy": {
            "strategy": "long",
            "base_order_size": 50,
            "order_type": "MARKET"
        },
        "take_profit": {
            "using": True,
            "target_profit": 2.0,
            "trailing_deviation": 0.0
        },
        "has_active_deal": False,
        "price": 0,
        "tokens": 0,
        "highest": 0,
        "mark": False
    },
    {
        "name": "CAKE Short Bot",
        "bot_id": "002",
        "broker": "Binance",
        "exchange_pair": "CAKEUSDT",
        "strategy": {
            "strategy": "short",
            "base_order_size": 50,
            "order_type": "MARKET"
        },
        "take_profit": {
            "using": False,
            "target_profit": 1.013,
            "trailing_deviation": 1
        },
        "has_active_deal": False,
        "price": 0,
        "tokens": 0,
        "highest": 0,
        "mark": False
    }
]

#Binance
client = Client(config.API_KEY, config.API_SECRET)

def process_message_trade_long(msg):
    socket_variable = float(msg['p'])
    # print(msg['p'])
    if socket_variable >= float(trading_bots[0]['price']) * trading_bots[0]['take_profit']['target_profit'] or trading_bots[0]['mark'] == True:
        trading_bots[0]['mark'] = True
        if socket_variable > trading_bots[0]['highest']:
            trading_bots[0]['highest'] = socket_variable
        if socket_variable <= (float(trading_bots[0]['price']) * trading_bots[0]['take_profit']['target_profit']) * (trading_bots[0]['take_profit']['trailing_deviation'] - 0.001) or trading_bots[0]['highest'] * trading_bots[0]['take_profit']['trailing_deviation'] >= socket_variable:
            binance_socket_close_long()
            print('Entry price: ', str(trading_bots[0]['price']))
            print('Exit price: ', str(socket_variable))

    if socket_variable < trading_bots[0]['highest']:
        print('Mark reached: ', trading_bots[0]['mark'], 'Highest point: ',trading_bots[0]['highest'])


def process_message_trade_short(msg):
    socket_variable = float(msg['p'])
    # print(msg['p'])
    if socket_variable <= float(trading_bots[1]['price']) / trading_bots[1]['take_profit']['target_profit'] or trading_bots[1]['mark'] == True:
        trading_bots[1]['mark'] = True
        if socket_variable < trading_bots[1]['highest']:
            trading_bots[1]['highest'] = socket_variable
        if socket_variable >= (float(trading_bots[1]['price']) / trading_bots[1]['take_profit']['target_profit']) / (trading_bots[1]['take_profit']['trailing_deviation'] - 0.001) or trading_bots[1]['highest'] / trading_bots[1]['take_profit']['trailing_deviation'] <= socket_variable:
            binance_socket_close_short()
            print('Entry price: ', str(trading_bots[1]['price']))
            print('Exit price: ', str(socket_variable))
    
    if socket_variable < trading_bots[1]['highest']:
        print('Mark reached: ', trading_bots[1]['mark'], 'Highest point: ',trading_bots[1]['highest'])


# Live trading function
def order_function(side, quantity, symbol, order_type):
    try:
        print(f"sending order {order_type} - {side} {quantity} {symbol}")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return order


def binance_socket_start_long():
    global bm
    bm = BinanceSocketManager(client)
    # start any sockets here, i.e a trade socket
    bm.start_trade_socket(trading_bots[0]['exchange_pair'], process_message_trade_long)
    # then start the socket manager
    bm.start()


def binance_socket_close_long():
    bm.close()
    if trading_bots[0]['has_active_deal'] == True:
        crypto = requests.get("https://api.binance.com/api/v3/exchangeInfo?symbol=" + trading_bots[0]['exchange_pair']).json()
        assets = client.get_asset_balance(asset=crypto['symbols'][0]['baseAsset'])
        quantity = float(assets['free'])
        if trading_bots[1]['has_active_deal'] == True:
            quantity = quantity * (trading_bots[1]['strategy']['base_order_size']/100)
        step = client.get_symbol_info(trading_bots[0]['exchange_pair'])
        stepMin = step['filters'][2]['stepSize']
        stepMinSize = 8 - stepMin[::-1].find('1')
        order_function('SELL', round(quantity - float(stepMin), stepMinSize), trading_bots[0]['exchange_pair'], ORDER_TYPE_MARKET)
        # print('SELL', round(quantity - float(stepMin), stepMinSize), trading_bots[0]['exchange_pair'], ORDER_TYPE_MARKET)
        trading_bots[0]['has_active_deal'] = False

        with open('bot1.json', 'w') as f:
            json.dump(trading_bots[0], f)


def binance_socket_start_short():
    global bm
    bm = BinanceSocketManager(client)
    # start any sockets here, i.e a trade socket
    bm.start_trade_socket(trading_bots[1]['exchange_pair'], process_message_trade_short)
    # then start the socket manager
    bm.start()


def binance_socket_close_short():
    bm.close()
    if trading_bots[1]['has_active_deal'] == True:
        crypto = requests.get("https://api.binance.com/api/v3/exchangeInfo?symbol=" + trading_bots[1]['exchange_pair']).json()
        assets = client.get_asset_balance(asset=crypto['symbols'][0]['quoteAsset'])

        price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + trading_bots[1]['exchange_pair']).json()

        if trading_bots[0]['has_active_deal'] == True:
            quantity = float(((float(assets['free'])*(trading_bots[1]['strategy']['base_order_size']/100)) / float(price['price']))*0.9995)
        else:
            quantity = float((float(assets['free']) / float(price['price']))*0.9995)

        step = client.get_symbol_info(trading_bots[1]['exchange_pair'])
        stepMin = step['filters'][2]['stepSize']
        stepMinSize = 8 - stepMin[::-1].find('1')

        order_function('BUY', round(quantity - float(stepMin), stepMinSize), trading_bots[1]['exchange_pair'], ORDER_TYPE_MARKET)
        # print('BUY', round(quantity - float(stepMin), stepMinSize), trading_bots[1]['exchange_pair'], ORDER_TYPE_MARKET)
        trading_bots[1]['has_active_deal'] = False

        with open('bot2.json', 'w') as f:
            json.dump(trading_bots[1], f)


@app.route('/ordertesting', methods=['POST'])
def ordertesting():
    # Load data from post
    data = json.loads(request.data)

    time.sleep(data['delay_seconds'])

    # Check for security phrase
    if data['passphrase'] != config.WEBHOOK_PHRASE:
        return {
            "code": "error",
            "message": "Nice try, invalid passphrase"
        }

    for i in trading_bots:
        if i['bot_id'] == data['bot_id'] :
            broker = i['broker']
            exchange_pair = i['exchange_pair']
            strategy = i['strategy']

    crypto = requests.get("https://api.binance.com/api/v3/exchangeInfo?symbol=" + exchange_pair).json()
    quoteAsset = crypto['symbols'][0]['quoteAsset']
    baseAsset = crypto['symbols'][0]['baseAsset']

    #Save buy or sell into side
    side = data['order_action'].upper()

    #If Binance trade
    if broker == 'Binance':

        time.sleep(1)
        if strategy['strategy'] == 'long':

            # Buy case
            if side == "BUY":
                assets = client.get_asset_balance(asset=quoteAsset)
                price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + exchange_pair).json()
                if trading_bots[1]['has_active_deal'] == True:
                    quantity = float(((float(assets['free'])*(strategy['base_order_size']/100)) / float(price['price']))*0.9995)
                else:
                    quantity = float((float(assets['free']) / float(price['price']))*0.9995)
                trading_bots[0]['price'] = price['price']
                
                trading_bots[0]['has_active_deal'] = True
                if trading_bots[0]["take_profit"]["using"]:
                    binance_socket_start_long()
        
            step = client.get_symbol_info(exchange_pair)
            stepMin = step['filters'][2]['stepSize']
            stepMinSize = 8 - stepMin[::-1].find('1')

            trading_bots[0]['tokens'] = round(quantity - float(stepMin), stepMinSize)

            if quantity > 0:
                if strategy['order_type'] != "":
                    order_response = order_function(side, round(quantity - float(stepMin), stepMinSize), exchange_pair, strategy['order_type'])
                    # print(side, round(quantity - float(stepMin), stepMinSize), exchange_pair, strategy['order_type'])
                    # order_response = True
                else:
                    order_response = "This bot doesn't exist"
            else:
                order_response = "No allowance"
            
            with open('bot1.json', 'w') as f:
                json.dump(trading_bots[0], f)

            if order_response == "No allowance" or order_response == "This bot doesn't exist":
                return {
                    "code": "error",
                    "message": order_response
                }
            elif order_response:
                return {
                    "code": "success",
                    "message": "order executed"
                }
            else:
                return {
                    "code": "error",
                    "message": "not enought funds"
                }
        

        elif strategy['strategy'] == 'short':
            # Sell case
            if side == "SELL":
                assets = client.get_asset_balance(asset=baseAsset)
                price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + exchange_pair).json()

                if trading_bots[0]['has_active_deal'] == True:
                    quantity = float(assets['free']) * (strategy['base_order_size']/100)
                else:
                    quantity = float(assets['free'])
                
                trading_bots[1]['price'] = price['price']

                trading_bots[1]['has_active_deal'] = True
                if trading_bots[1]["take_profit"]["using"]:
                    binance_socket_start_short()
        
            step = client.get_symbol_info(exchange_pair)
            stepMin = step['filters'][2]['stepSize']
            stepMinSize = 8 - stepMin[::-1].find('1')

            trading_bots[1]['tokens'] = round(quantity - float(stepMin), stepMinSize)

            if quantity > 0:
                if strategy['order_type'] != "":
                    order_response = order_function(side, round(quantity - float(stepMin), stepMinSize), exchange_pair, strategy['order_type'])
                    # print(side, round(quantity - float(stepMin), stepMinSize), exchange_pair, strategy['order_type'])
                    # order_response = True
                else:
                    order_response = "This bot doesn't exist"
            else:
                order_response = "No allowance"

            with open('bot2.json', 'w') as f:
                json.dump(trading_bots[1], f)

            if order_response == "No allowance" or order_response == "This bot doesn't exist":
                return {
                    "code": "error",
                    "message": order_response
                }
            elif order_response:
                return {
                    "code": "success",
                    "message": "order executed"
                }
            else:
                return {
                    "code": "error",
                    "message": "not enought funds"
                }


@app.route('/binance_close_long', methods=['POST'])
def binance_socket_long_closer():
    time.sleep(6)
    binance_socket_close_long()
    return("Socket Closed")

@app.route('/binance_close_short', methods=['POST'])
def binance_socket_short_closer():
    time.sleep(6)
    binance_socket_close_short()
    return("Socket Closed")

@app.route('/binance_futures_BNBUSDT', methods=['POST'])
def binance_futures_long():
    # Load data from post
    # data = json.loads(request.data)

    # client.futures_change_leverage(symbol="BNBUSDT", leverage=75)
    # client.futures_change_margin_type(symbol="BNBUSDT", marginType='CROSSED')
    # return(client.futures_account())
    client.futures_change_position_mode(dualSidePosition="true")

    for i in client.futures_account()['positions']:
        if i['symbol'] == "BNBUSDT":
            return(i)

@app.route('/binance_futures_trade', methods=['POST'])
def binance_futures_trade():
    # Load data from post
    data = json.loads(request.data)

    if data['side'] == 'LONG':
        takeProfit = float(data['close']) + ((float(data['close']) * 0.10) / 75)
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
