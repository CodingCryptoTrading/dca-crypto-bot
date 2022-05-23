import numpy as np
import logging
import matplotlib.pyplot as plt

class PriceMapper(object):
    def __init__(self, amount_range, price_range, mapping_function, coin, pairing, n_points=1000):

        self.amounts = amount_range
        self.prices = price_range
        self.function = mapping_function
        self.coin = coin
        self.pairing = pairing

        self.check_inputs()

        self.n_points = n_points

    def check_inputs(self):

        if len(self.prices) != 2:
            error_string = 'PRICE_RANGE should be a list of 2 elements: min and max price.'
            raise Exception(error_string)
        if len(self.amounts) != 2:
            error_string = 'AMOUNT should be a list of 2 elements: min and max amount.'
            raise Exception(error_string)
        if self.function not in ['linear', 'exponential', 'constant']:
            error_string = 'Valid mapping functions are: "linear" and "exponential".'
            raise Exception(error_string)


    def plot(self):
        # increase upper limit to show in the graph
        upperlimit_price = self.prices[1] + 0.1*self.prices[1]
        upperlimit_amount = self.amounts[1] + 0.1 * self.amounts[1]
        x = np.linspace(0,upperlimit_price, num=self.n_points)
        y = []
        for i in x:
            y.append(self.get_amount(i))

        plt.rcParams.update({'font.size': 12})

        fig, ax = plt.subplots()

        color_text_lines = '#6c6c72'

        plt.axvline(x=self.prices[1], color='#da6517', linestyle='--', linewidth=0.8)
        plt.plot(x,y, '-', color='#6f7a8f', linewidth=1.1)


        plt.title(f'{self.coin} | Buy Conditions',
                  color=color_text_lines)
        ax.ticklabel_format(useOffset=False, style='plain')
        plt.ylabel(f"Amount {self.pairing}", color=color_text_lines)
        plt.xlabel(f"Price {self.coin}", color=color_text_lines)


        ax.grid('on', linestyle='--', linewidth=0.5, alpha = 0.5)
        ax.xaxis.set_tick_params(size=0)
        ax.yaxis.set_tick_params(size=0)
        ax.tick_params(axis='y', colors=color_text_lines)
        ax.tick_params(axis='x', colors=color_text_lines)

        # ax.spines['bottom'].set_color('#6c6c72')
        # ax.spines['left'].set_color('#6c6c72')

        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)

        plt.xlim([0, upperlimit_price])
        plt.ylim([0, upperlimit_amount])

        leg = plt.legend(['Buy limit', 'Amount'])
        leg.get_frame().set_linewidth(0.0)
        for text in leg.get_texts():
            text.set_color(color_text_lines)

        plt.tight_layout()

        plt.savefig(f'trades/graph_{self.coin}_buy_conditions.png')
        plt.close()


    def get_amount(self, price):
        if self.function == 'linear':
            return self.linear(price)
        elif self.function == 'exponential':
            return self.exponential(price)
        elif self.function == 'constant':
            return self.constant(price)
        else:
            error_string = 'Unrecognized mapping function'
            logging.error(error_string)
            raise Exception(error_string)

    def linear(self, price):
        # storing variables in letters for readability
        A = self.amounts[0]
        B = self.amounts[1]

        C = self.prices[0]
        D = self.prices[1]

        if price < C:
            amount = B
        elif price > D:
            amount = 0
        else:
            amount = B + ( (B - A) / (D - C)) * (C - price)
        return amount

    def exponential(self, price):
        # storing variables in letters for readability
        A = self.amounts[0]
        B = self.amounts[1]

        C = self.prices[0]
        D = self.prices[1]

        r = (np.log(A) - np.log(B)) / ( D - C)
        k = A * np.exp(- D * r)

        if price < C:
            amount = B
        elif price > D:
            amount = 0
        else:
            amount = k * np.exp(r * price)
        return amount

    def constant(self, price):
        # storing variables in letters for readability
        A = self.amounts[0]
        B = self.amounts[1]

        C = self.prices[0]
        D = self.prices[1]

        if price < C:
            amount = 0
        elif price > D:
            amount = 0
        else:
            amount = B
        return amount



