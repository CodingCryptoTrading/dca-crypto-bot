import pandas as pd
import datetime
import ccxt
import logging


class ExceededAmountLimits(Exception):
    """Raised when amount is not within the limits"""
    def __init__(self, symbol, min_, max_):
        if min_ is None:
            self.message = f"Amount for {symbol} should be less than {max_}"
        elif max_ is None:
            self.message = f"Amount for {symbol} should be greater than {min_}"
        else:
            self.message = f"Amount for {symbol} should be comprise between {min_} and {max_} (excluding extreme values)"
        super().__init__(self.message)


def check_cost_limits(exchange, coins):
    """Check if the cost is within the exchange limits (min and max)"""
    exchange.load_markets()

    for coin in coins:
        symbol = coins[coin]['SYMBOL']
        cost = coins[coin]['AMOUNT']
        market = exchange.market(symbol)
        if type(cost) is dict:
            min_ = market['limits']['cost']['min']
            max_ = market['limits']['cost']['max']
            if (min_ is not None and cost['RANGE'][0] <= min_) or (max_ is not None and cost['RANGE'][1] >= max_):
                raise ExceededAmountLimits(symbol, min_, max_)
        else:
            min_ = market['limits']['cost']['min']
            max_ = market['limits']['cost']['max']
            if (min_ is not None and cost <= min_) or (max_ is not None and cost >= max_):
                raise ExceededAmountLimits(symbol, min_, max_)

def get_non_zero_balance(exchange, sort_by='total', ascending=False ):
    """Get non zero balance (total,free and used). Use "sort_by" to sort
        according to the type of balance"""
    balance = exchange.fetch_balance()
    coin_name = []
    coin_list = []
    for key in balance['total']:
        if balance['total'][key] > 0:
            coin_list.append(balance[key])
            coin_name.append(key)
    df = pd.DataFrame.from_records(coin_list)
    df.index = coin_name
    # sort df
    if df.shape[0] > 0:
        df.sort_values(sort_by, axis=0, ascending=ascending, inplace=True)
    return df


def get_price(exchange, symbol):
    exchange.load_markets()
    last_price = exchange.fetch_ticker(symbol)['last']
    return last_price


def get_quantity_to_buy(exchange, amount, symbol):
    exchange.load_markets()
    last_price = exchange.fetch_ticker(symbol)['last']
    amount = exchange.amount_to_precision(symbol, amount / float(last_price))
    return amount


def order_to_dataframe(exchange, order, coin):

    data = {'datetime (local)': datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            'datetime (exchange)': order['datetime'],
            'timestamp': order['timestamp'],
            'coin': coin,
            'symbol': order['symbol'],
            'status': order['status'],
            'filled': order['filled'],
            'price': order['average'],
            'cost': order['cost'],
            'remaining': order['remaining'],
            'fee': 'N.A.',
            'fee currency': 'N.A.',
            'fee rate': 'N.A.',
            }

    if not order['fee']:
        # some exchanges return None. Let's try to retrieve fees from the trade history
        try:
            if exchange.has['fetchOrderTrades']:
                trades = exchange.fetch_order_trades(order['id'], order['symbol'], since=None, limit=None, params={})
                fees = [trade['fee'] for trade in trades]
                # In case the order is split into multiple trades:
                fees = exchange.reduce_fees_by_currency(fees)
                order['fee'] = fees[0]  # We assume fees are paid in the same currency (may not always be true, e.g.,
                # a portion paid in BNB and a portion in USDT. We are discarding this case)
        except Exception as e:
            logging.warning(f"Couldn't retrieve fees due to: {type(e).__name__} {str(e)}")

    if order['fee']:
        if 'currency' in order['fee']:
            data['fee currency'] = order['fee']['currency']
        if 'cost' in order['fee']:
            data['fee'] = order['fee']['cost']
        if 'rate' in order['fee']:
            data['fee rate'] = order['fee']['rate']

    df = pd.DataFrame(data, index=[0])
    return df


def connect_to_exchange(cfg, api):
    """
    Connect to the exchange using the cfg info and the api (both already loaded)
    """
    api_test_selector = 'TEST' if cfg['TEST'] else 'REAL'

    exchange_id = cfg['EXCHANGE'].upper()
    if 'PASSPHRASE' in api[exchange_id][api_test_selector]:
        exchange_class = getattr(ccxt, exchange_id.lower())
        exchange = exchange_class({
            'apiKey': api[exchange_id][api_test_selector]['APIKEY'],
            'secret': api[exchange_id][api_test_selector]['SECRET'],
            'password': api[exchange_id][api_test_selector]['PASSPHRASE'],
            'enableRateLimit': True,
            'options': {'adjustForTimeDifference': True}
        })
    else:
        exchange_class = getattr(ccxt, exchange_id.lower())
        exchange = exchange_class({
            'apiKey': api[exchange_id][api_test_selector]['APIKEY'],
            'secret': api[exchange_id][api_test_selector]['SECRET'],
            'enableRateLimit': True,
            'options': {'adjustForTimeDifference': True}
        })

    if 'TEST' in api_test_selector:
        logging.info(f"Connected to {exchange_id} in TEST mode!")
        exchange.set_sandbox_mode(True)
    else:
        logging.info(f"Connected to {exchange_id}!")
        #are_you_sure_to_continue()

    return exchange
