import json, config
import requests
from flask import Flask, request, render_template
from binance.client import Client
from binance.enums import *


app = Flask(__name__)


trading_bots = [
    {
        'name': "Cake Bot",
        'exchange_pair': "CAKEBUSD",
        'crypto': 'CAKE',
        'hold': 100,
        'holds': True,
        'value': 200,
        'profit': 0,
        '7days': 0,
        'order_type': ORDER_TYPE_MARKET
    },
    {
        'name': "Bitcoin Bot",
        'exchange_pair': "BTCBUSD",
        'crypto': 'BTC',
        'hold': 0,
        'holds': True,
        'value': 800,
        'profit': 0,
        '7days': 0,
        'order_type': ORDER_TYPE_MARKET
    }
]


client = Client(config.API_KEY, config.API_SECRET)


# Adding bot
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
def order_function(side, quantity, symbol, order_type):
    try:
        print(f"sending order {order_type} - {side} {quantity} {symbol}")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return order


# Test trading function
def test_order_function(side, quantity, symbol, order_type):
    try:
        print(f"sending order {order_type} - {side} {quantity} {symbol}")
        order = client.create_test_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return order


# Home page
@app.route('/')
def welcome():
    balances = client.get_account()['balances']

    return render_template('index.html', balances=balances)


@app.route('/bots')
def show_bots():

    for i in trading_bots:
        pair_price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + i['exchange_pair']).json()
        token_holding = client.get_asset_balance(asset=i['crypto'])
        i['value'] = round(float(pair_price['price']) * float(token_holding['free']), 2)

    return render_template('bots.html', bots=trading_bots)


# Live trade webhook
@app.route('/order', methods=['POST'])
def order():
    # Load data from post
    data = json.loads(request.data)

    order_type = ORDER_TYPE_MARKET
    
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
            if i['exchange_pair'] == data['ticker']:
                allowence += i['hold']
                i['holds'] = True
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
            order_response = order_function(side, round(quantity - 0.001, 3), exchange, order_type)
        else:
            order_response = True
    elif data['ticker'] == 'BTCBUSD':
        if quantity > 0:
            order_response = order_function(side, round(quantity - 0.000001, 6), exchange, order_type)
        else:
            order_response = True
    elif data['ticker'] == 'BNBBUSD':
        if quantity > 0:
            order_response = order_function(side, round(quantity - 0.0001, 4), exchange, order_type)
        else:
            order_response = True

    # if True != order_response:
    #     return {
    #         "code": "success",
    #         "message": "order executed"
    #     }
    # else:
    #     if float(client.get_asset_balance(asset="BUSD")['free']) > 10:
    #         order()
    #     else:
    #         return {
    #             "code": "error",
    #             "message": "not enought funds"
    #         }

    if float(client.get_asset_balance(asset="BUSD")['free']) > 10 and side == "BUY":
        order()
    else:
        if order_response:
            return {
                "code": "success",
                "message": "order executed"
            }
        else:
            return {
                "code": "error",
                "message": "not enought funds"
            }
    


@app.route('/ordertest', methods=['POST'])
def ordertest():
    # Load data from post
    data = json.loads(request.data)

    order_type = ORDER_TYPE_MARKET
    
    # Check for security phrase
    if data['passphrase'] != config.WEBHOOK_PHRASE:
        return {
            "code": "error",
            "message": "Nice try, invalid passphrase"
        }

    # Check for buy or for sell
    side = data['strategy']['order_action'].upper()

    
    # Buy case
    if side == "BUY":
        allowence = 0
        for i in trading_bots:
            if i['exchange_pair'] == data['ticker'] and i['holds'] == False:
                allowence += i['hold']
                i['holds'] = True
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
            order_response = test_order_function(side, round(quantity - 0.001, 3), exchange, order_type)
        else:
            order_response = True
    elif data['ticker'] == 'BTCBUSD':
        if quantity > 0:
            order_response = test_order_function(side, round(quantity - 0.000001, 6), exchange, order_type)
        else:
            order_response = True
    elif data['ticker'] == 'BNBBUSD':
        if quantity > 0:
            order_response = test_order_function(side, round(quantity - 0.0001, 4), exchange, order_type)
        else:
            order_response = True


    if order_response == {}:
        return {
            "code": "success",
            "message": "order executed"
        }
    elif order_response:
        return {
            "code": "error",
            "message": "Bot already traded in"
        }


# Parallax page
@app.route('/parallax')
def parallax():
    return render_template('parallax.html')


@app.route('/managebot', methods=['POST'])
def manage_bot():
    # Load data from post
    data = json.loads(request.data)


    # Check request
    if data['task'] == 'update':
        allowance = 100
        for i in trading_bots:
            if i['name'] == data['name']:
                i['hold'] = data['hold']
                allowance -= data['hold']

        for i in trading_bots:
            if i['name'] != data['name']:
                i['hold'] = int(allowance / (len(trading_bots) - 1))


    elif data['task'] == 'create':
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


@app.route('/stoploss', methods=['POST'])
def stoploss():
    # Load data from post
    data = json.loads(request.data)

    return ()