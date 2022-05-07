import numpy as np
import logging

class PriceMapper(object):
    def __init__(self, amount_range, price_range, mapping_function):

        self.amounts = amount_range
        self.prices = price_range
        self.function = mapping_function

    def get_amount(self, price):
        if self.function == 'linear':
            return self.linear(price)
        elif self.function == 'exponential':
            return self.exponential(price)
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




