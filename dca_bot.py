from utils.timing import *
from utils.exchange import *
from utils.stats_and_plots import *
from utils.mail_notifier import Notifier

import ccxt
import logging
import time
from dateutil.relativedelta import relativedelta
import pandas as pd
from pathlib import Path


class Dca(object):
    def __init__(self, cfg_path, api_path):
        # create logger
        log_file = Path('trades/log.txt')
        log_file.parent.mkdir(parents=True, exist_ok=True)
        register_logger(log_file=log_file)
        logging.info('Program started. Initializing variables...')

        # loads local configuration
        cfg = load_config(cfg_path)
        api = load_config(api_path)

        # Store cfg
        self.cfg = cfg

        # initialize notifier
        if self.cfg['SEND_NOTIFICATIONS']:
            self.notify = Notifier(self.cfg)

        try:
            self.exchange = connect_to_exchange(self.cfg, api)
        except Exception as e:
            if self.cfg['SEND_NOTIFICATIONS']:
                self.notify.critical(e, "lunching the both running")
            raise e

        # Show balance
        try:
            logging.info("Getting your balance from the exchange:")
            balance = get_non_zero_balance(self.exchange, sort_by='total')
            logging.info("\n" + balance.to_string())
        except Exception as e:
            logging.warning("Balance checking failed: " + type(e).__name__ + " " + str(e))

        # Store coin info into a local variable
        self.coin = {}
        for coin in cfg['COINS']:
            self.coin[coin.upper()] = cfg['COINS'][coin]

        self.order_book = {}
        self.coin_to_buy = []
        self.next_order = []

        # create trade folder and define csv filepath (for orders)
        self.csv_path = Path('trades/orders.csv')
        if Path(self.csv_path).is_file():
            self.df_orders = read_csv_custom(self.csv_path)
        else:
            self.df_orders = pd.DataFrame()

        # define csv filepath for stats
        self.stats_path = Path('trades/stats.csv')
        if Path(self.stats_path).is_file():
            self.df_stats = read_csv_custom(self.stats_path)
        else:
            self.df_stats = pd.DataFrame([], columns=['Coin', 'N', 'Quantity', 'AvgPrice', 'TotalCost', 'ROI', 'ROI%'])
            self.df_stats.set_index(['Coin'], inplace=True)

        # define json filepath (for orders)
        self.json_path = Path('trades/orders.json')

        # define path for order_book (next_purchases)
        self.order_book_path = Path('trades/next_purchases.csv')

        # Get the 'SCHEDULE' time for each coin
        self.initialize_order_book()

        # get retry times for errors
        self.retry_for_funds, self.retry_for_network = retry_info()

        # Check coin limits
        check_cost_limits(self.exchange, self.coin)

        if self.cfg['SEND_NOTIFICATIONS']:
            info = 'DCA bot has just been started'
            self.notify.info(info)

        logging.info('Everything up and running!')

        while True:

            logging.info('Initializing next order...')
            self.find_next_order()

            # do not check funds if last attempt failed due to insufficient Funds
            if not isinstance(self.coin[self.coin_to_buy]['LASTERROR'], ccxt.InsufficientFunds):
                self.check_funds()

            self.wait()

            self.buy()

    def find_next_order(self):
        """
        Find (and set) the closest coin to buy.
        Also, write to disk the order_book. The order_book is required to identify the correct bi-weekly purchase time
        in case the bot is restarted.
        """
        # first element is the coin, second element the time
        self.next_order = min(self.order_book.items(), key=lambda x: x[1])
        self.coin_to_buy = self.next_order[0]

        # Also, write to disk the order_book
        ordered_order_book = dict(sorted(self.order_book.items(), key=lambda item: item[1]))
        df = pd.DataFrame([ordered_order_book]).T.rename_axis('Coin').rename(columns={0: 'Purchase Time'})
        cycle = []
        for coin in df.index:
            cycle.append(self.coin[coin]['CYCLE'].lower())
        df['Cycle'] = cycle
        df.to_csv(self.order_book_path)

    def check_funds(self):
        """
        Check if there is sufficient money for the next purchase
        """
        cost = self.coin[self.coin_to_buy]['AMOUNT']
        pairing = self.coin[self.coin_to_buy]['PAIRING']
        try:
            balance = self.exchange.fetch_balance()
        except:
            balance = []
            logging.warning("Balance checking failed.")

        if balance:
            if cost > balance['free'][pairing]:
                logging.warning(f"Insufficient funds for the next {self.coin_to_buy} purchase. Top up your account!")
                if self.cfg['SEND_NOTIFICATIONS']:
                    next_purchase = self.next_order[1].strftime('%d %b %Y at %H:%M')
                    self.notify.warning_funds(self.coin_to_buy,
                                              next_purchase,
                                              pairing,
                                              cost,
                                              balance['free'][pairing])

    def wait(self):
        """
        wait for the next purchase
        """
        time_remaining = (self.next_order[1] - datetime.datetime.today()).total_seconds()
        if time_remaining < 0:
            time_remaining = 0
        logging.info(f"Next purchase: {self.next_order[0]} ({self.coin[self.next_order[0]]['AMOUNT']} "
                     f"{self.coin[self.next_order[0]]['PAIRING']}) on {self.next_order[1].strftime('%Y-%m-%d %H:%M')}."
                     f"\nTime remaining: {int(time_remaining)} s")

        time.sleep(time_remaining)

    def buy(self):
        order = self.execute_order(self.coin_to_buy)
        # print and save order info:
        if order:
            store_json_order(self.json_path, order)
            df = order_to_dataframe(order, self.coin_to_buy)
            string_order = f"Bought {df['filled'][0]} {self.coin_to_buy} at price {df['price'][0]} {self.coin[self.coin_to_buy]['PAIRING']} (Cost = {df['cost'][0]} {self.coin[self.coin_to_buy]['PAIRING']})"
            logging.info("-> " + string_order)
            self.df_orders = pd.concat([self.df_orders, df]).reset_index(drop=True)
            self.df_orders.index.names = ['N']
            self.df_orders.to_csv(self.csv_path)
            plot_purchases(self.coin_to_buy, self.df_orders, self.coin[self.coin_to_buy]['PAIRING'])
            self.df_stats = calculate_stats(self.coin_to_buy, self.df_orders, self.df_stats, self.stats_path)
            if self.cfg['SEND_NOTIFICATIONS']:
                next_purchase = self.coin[self.coin_to_buy]['SCHEDULE'].strftime('%d %b %Y at %H:%M')
                self.notify.success(df,
                                    self.coin[self.coin_to_buy]['CYCLE'],
                                    next_purchase,
                                    datetime.datetime.now().strftime('%d %b %Y at %H:%M'),
                                    self.coin[self.coin_to_buy]['PAIRING'],
                                    self.df_stats.loc[self.coin_to_buy])

    def execute_order(self, coin):
        type_order = 'market'
        side = 'buy'
        symbol = self.coin[coin]['SYMBOL']
        price = None
        try:
            if 'binance' in self.exchange.id:
                # this order strategy should take care of everything (precision and lot size)
                params = {
                    'quoteOrderQty': self.coin[coin]['AMOUNT'],
                    }
                order = self.exchange.create_order(symbol, type_order, side, self.coin[coin]['AMOUNT'], price, params)
            else:
                # In case the above is not available on the exchange use the following
                amount = get_quantity_to_buy(self.exchange, self.coin[coin]['AMOUNT'], symbol)
                order = self.exchange.create_order(symbol, type_order, side, amount, price)
            self.update_next_datetime(coin)
            # reset error variable
            self.coin[coin]['LASTERROR'] = []
            self.coin[coin]['ERROR_ATTEMPT'] = 0
            return order
        # Network errors: these are non-critical errors (recoverable)
        except (ccxt.DDoSProtection, ccxt.ExchangeNotAvailable,
                ccxt.InvalidNonce, ccxt.RequestTimeout, ccxt.NetworkError) as e:
            self.handle_recoverable_errors(coin, e)
            # send only on first occurrence
            if self.cfg['SEND_NOTIFICATIONS'] and self.coin[coin]['ERROR_ATTEMPT'] == 1:
                # if there is a network error, it is likely that this message will not be transmitted
                self.notify.error(coin, self.retry_for_network[self.coin[coin]['CYCLE']], e)
        except ccxt.InsufficientFunds as e:  # This is an ExchangeError but we will treat it as recoverable
            self.handle_recoverable_errors(coin, e)
            # send only on first occurrence
            if self.cfg['SEND_NOTIFICATIONS'] and self.coin[coin]['ERROR_ATTEMPT'] == 1:
                self.notify.error(coin, self.retry_for_funds[self.coin[coin]['CYCLE']], e)
        # Not recoverable errors (Exchange errors):
        except ccxt.ExchangeError as e:
            logging.error(type(e).__name__ + ' ' + str(e))
            if self.cfg['SEND_NOTIFICATIONS']:
                when = f"attempting to purchase <strong>{coin}</strong>"
                self.notify.critical(e, when)
            raise e
        except Exception as e:  # raise all other exceptions
            logging.error(type(e).__name__ + ' ' + str(e))
            when = f"attempting to purchase <strong>{coin}</strong>"
            if self.cfg['SEND_NOTIFICATIONS']:
                self.notify.critical(e, when)
            raise e
        return False

    def handle_recoverable_errors(self, coin, e):
        # wait (variable on cycle frequency) and retry
        retry_after = self.get_retry_time(coin, e)
        self.update_next_datetime(coin, retry_after=retry_after)
        if retry_after:
            error_msg = f"{type(e).__name__} {str(e)}\nNext attempt will be in {retry_after} s"
            logging.warning(error_msg)
        else:
            error_msg = f"{type(e).__name__} {str(e)}\nToo many attempts. Skipping this iteration."
            logging.error(error_msg)
        self.coin[coin]['LASTERROR'] = e

    def get_retry_time(self, coin, error):
        """
        For a given error get the appropriate retry time for the next buy attempt.
        It also sets STATUS variable
        Args:
            coin: coin to update (str)
            error: error returned during buy time
        """
        self.coin[coin]['ERROR_ATTEMPT'] += 1

        if isinstance(error, ccxt.InsufficientFunds):
            max_attempt = self.retry_for_funds[self.coin[coin]['CYCLE']][0]
            if self.coin[coin]['ERROR_ATTEMPT'] <= max_attempt:
                retry_time = self.retry_for_funds[self.coin[coin]['CYCLE']][1]
                return retry_time
            else:
                # too many attempts, skip this buying iteration
                self.coin[coin]['ERROR_ATTEMPT'] = 0
                return False
        elif isinstance(error, (ccxt.DDoSProtection, ccxt.ExchangeNotAvailable, ccxt.InvalidNonce, ccxt.RequestTimeout, ccxt.NetworkError)):
            max_attempt = self.retry_for_network[self.coin[coin]['CYCLE']][0]
            if self.coin[coin]['ERROR_ATTEMPT'] <= max_attempt:
                retry_time = self.retry_for_network[self.coin[coin]['CYCLE']][1]
                return retry_time
            else:
                # too many attempts, skip this buying iteration
                self.coin[coin]['ERROR_ATTEMPT'] = 0
                return False

    def update_next_datetime(self,coin,retry_after=False):
        """
        For a given coin, update the next buy time and the order book
        Args:
            coin: coin to update (str)
            retry_after: time in seconds to wait for the next buy attempt (in case previous failed)
        """
        if retry_after:  # this means that an error occurred
            self.order_book[coin] = datetime.datetime.today() + datetime.timedelta(seconds=retry_after)
        else:
            if self.coin[coin]['CYCLE'].lower() == 'minutely':  # only for testing purpose
                self.coin[coin]['SCHEDULE'] = self.coin[coin]['SCHEDULE'] + datetime.timedelta(minutes=1)
            elif self.coin[coin]['CYCLE'].lower() == 'daily':
                self.coin[coin]['SCHEDULE'] = self.coin[coin]['SCHEDULE'] + datetime.timedelta(days=1)
            elif self.coin[coin]['CYCLE'].lower() == 'bi-weekly':
                self.coin[coin]['SCHEDULE'] = self.coin[coin]['SCHEDULE'] + datetime.timedelta(days=14)
            elif self.coin[coin]['CYCLE'].lower() == 'weekly':
                self.coin[coin]['SCHEDULE'] = self.coin[coin]['SCHEDULE'] + datetime.timedelta(days=7)
            elif self.coin[coin]['CYCLE'].lower() == 'monthly':
                self.coin[coin]['SCHEDULE'] = self.coin[coin]['SCHEDULE'] + relativedelta(months=1)
            # update the order book:
            self.order_book[coin] = self.coin[coin]['SCHEDULE']

    def initialize_order_book(self):
        """
        Initialize the schedule time for each coin depending on current time and config settings. Also, initialize the order_book
            coin: coin to update (str)
            retry_after: time in seconds to wait for the next buy attempt (in case previous failed)
        """
        for coin in self.coin:
            if self.coin[coin]['CYCLE'].lower() == 'minutely':

                # only for testing purpose
                if not self.cfg['TEST']:
                    error_string = 'Cycle "minutely" is only available in TEST mode.'
                    logging.error(error_string)
                    raise Exception(error_string)

                # this is for testing mode only, buy every minute starting from now!
                self.coin[coin]['SCHEDULE'] = datetime.datetime.now()

            elif self.coin[coin]['CYCLE'].lower() == 'daily':
                at_time = get_hour_minute(self.coin[coin]['AT_TIME'])
                scheduled_datetime = datetime.datetime.combine(datetime.date.today(),
                                                               datetime.time(at_time[0], at_time[1]))
                # Check if scheduled datetime has passed
                if scheduled_datetime < datetime.datetime.today():
                    scheduled_datetime = scheduled_datetime + datetime.timedelta(days=1)    # Add one day
                self.coin[coin]['SCHEDULE'] = scheduled_datetime

            elif 'weekly' in self.coin[coin]['CYCLE'].lower():
                at_time = get_hour_minute(self.coin[coin]['AT_TIME'])
                on_weekday = get_on_weekday(self.coin[coin]['ON_WEEKDAY'])
                today = datetime.date.today()
                today + datetime.timedelta((on_weekday - today.weekday()) % 7)
                scheduled_datetime = datetime.datetime.combine(today + datetime.timedelta((on_weekday - today.weekday()) % 7),
                                                               datetime.time(at_time[0], at_time[1]))
                if scheduled_datetime < datetime.datetime.today():
                    # if 'bi-weekly' in self.coin[coin]['CYCLE']:
                    #     scheduled_datetime = scheduled_datetime + datetime.timedelta(days=14)
                    # else:
                    # the above block is commented. In this way you wait 1 week in the worst case scenario even
                    # for the bi-weekly
                    scheduled_datetime = scheduled_datetime + datetime.timedelta(days=7)

                # we have a little complication with the bi-weekly cycle. We have to consult the order_book (if exists)
                # to decide which week to use (in case the bot was restarted)
                if 'bi-weekly' in self.coin[coin]['CYCLE'].lower() and self.order_book_path.exists():
                    df = read_csv_custom(self.order_book_path)
                    previously = None
                    for cn in df.index:
                        if cn == coin and df.loc[cn]['Cycle'] == 'bi-weekly':
                            previously = df.loc[cn]['Purchase Time']
                    if previously:
                        previously = datetime.datetime.strptime(previously, '%Y-%m-%d %H:%M:%S')
                        if previously == scheduled_datetime + datetime.timedelta(days=7):
                            scheduled_datetime = previously
                self.coin[coin]['SCHEDULE'] = scheduled_datetime

            elif self.coin[coin]['CYCLE'].lower() == 'monthly':
                at_time = get_hour_minute(self.coin[coin]['AT_TIME'])
                on_day = get_on_day(self.coin[coin]['ON_DAY'])
                today = datetime.datetime.today()
                scheduled_datetime = datetime.datetime.combine(datetime.datetime(today.year, today.month, on_day),
                                                               datetime.time(at_time[0], at_time[1]))
                if scheduled_datetime < datetime.datetime.today():
                    scheduled_datetime = scheduled_datetime + relativedelta(months=1)
                self.coin[coin]['SCHEDULE'] = scheduled_datetime

            else:
                error_string = 'Cycle not recognized. Valid cycle strings are: "daily", "weekly", ' \
                               '"bi-weekly" and "monthly".'
                logging.error(error_string)
                raise Exception(error_string)

        for coin in self.coin:
            # create the order book
            self.order_book[coin] = self.coin[coin]['SCHEDULE']

            # Define symbol variable
            self.coin[coin]['SYMBOL'] = coin + self.coin[coin]['PAIRING']

            # set the error variables
            self.coin[coin]['LASTERROR'] = []
            self.coin[coin]['ERROR_ATTEMPT'] = 0


if __name__ == "__main__":


    #
    # api_test_selector = 'TEST' if cfg['TEST'] else 'REAL'
    #
    # exchange_id = cfg['EXCHANGE']
    # exchange_class = getattr(ccxt, exchange_id)
    # exchange = exchange_class({
    #     'apiKey': api[exchange_id.upper()][api_test_selector]['APIKEY'],
    #     'secret': api[exchange_id.upper()][api_test_selector]['SECRET'],
    #     'enableRateLimit': True,
    #     'options': {'adjustForTimeDifference': True}
    # })
    # if 'TEST' in api_test_selector:
    #     print(f"Connected to {exchange_id} in TEST mode!")
    #     exchange.set_sandbox_mode(True)
    # else:
    #     print(f"Connected to {exchange_id}!")
    #     #are_you_sure_to_continue()
    #
    # # Show balance
    # print("Getting your balance from the exchange:")
    # print(get_non_zero_balance(exchange, sort_by='total'))

    cfg_path = 'config/config_example.yml'
    api_path = 'auth/API_keys_example.yml'

    # Run the bot
    Dca(cfg_path, api_path)
