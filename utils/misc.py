import logging
import sys, os
import json
import yaml
import pandas as pd


def load_config(file):
    with open(file) as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def register_logger(log_file=None, stdout=True):
    log = logging.getLogger()  # root logger
    for hdlr in log.handlers[:]:  # remove all old handlers
        log.removeHandler(hdlr)

    handlers = []

    formatter = logging.Formatter("%(asctime)s %(levelname)s%(message)s",
                                  "%Y-%m-%d %H:%M:%S")

    if stdout:
        handlers.append(logging.StreamHandler(stream=sys.stdout))

    if log_file is not None:
        handlers.append(logging.FileHandler(log_file))

    for h in handlers:
        h.setFormatter(formatter)

    logging.basicConfig(handlers=handlers)

    logging.addLevelName(logging.INFO, '')
    logging.addLevelName(logging.ERROR, 'ERROR ')
    logging.addLevelName(logging.WARNING, 'WARNING ')

    logging.root.setLevel(logging.INFO)


def read_csv_custom(filepath):
    try:
        # we had to add engine since on PI was giving segmentation fault
        df = pd.read_csv(filepath, index_col=0, engine='python')
    except:
        df = pd.read_csv(filepath, index_col=0)
    return df


def store_json_order(filename, order):
    """
    Save order into local json file
    """
    if not os.path.exists(filename):
        data = []
    else:
        # 1. Read file contents
        with open(filename, "r") as file:
            data = json.load(file)
    # 2. Update json object
    data.append(order)

    # 3. Write json file
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)


def are_you_sure_to_continue():
    while True:
        query = input('You are going to make real purchases, do you want to continue? [y/n]: ')
        Fl = query[0].lower()
        if query == '' or not Fl in ['y', 'n', 'yes', 'no']:
            print('Please answer with yes or no!')
        else:
            break
    if Fl == 'y':
        return
    if Fl == 'n':
        quit()


def float_to_float_sf(x, sf=3):
    """
    Converts float to string with one significant figure
    while refraining from scientific notation

    inputs:
        x: input float to be converted to string (float)
        sf: significant_figures
    """

    import numpy as np

    # Get decimal exponent of input float
    exp = int(f"{x:e}".split("e")[1])

    # Get rid of all digits after the first significant figure
    x_fsf = round(round(x*10**-exp, sf-1) * 10**exp, 12)

    # Get rid of scientific notation and convert to string
    x_str = np.format_float_positional(x_fsf)

    # Return string output
    return x_str


def round_price(x):
    if x == 0:
        x = '0'
    elif abs(x) < 1:
        # use 3 significant digits:
        x = float_to_float_sf(x, sf=3)
    else:
        x = '{:.2f}'.format(x)
    return x



