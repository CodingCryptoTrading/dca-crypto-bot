import matplotlib.pyplot as plt
from utils.misc import *


def plot_purchases(coin, df_orders, pairing):
    prices = df_orders['price'][df_orders['coin'] == coin].values
    costs = df_orders['cost'][df_orders['coin'] == coin].values
    # Calculate the weighted average
    avg = (prices * costs).sum() / costs.sum()

    plt.rcParams.update({'font.size': 12})

    fig, ax = plt.subplots()

    color_text_lines = '#6c6c72'

    plt.plot(prices, '-o', color='#6f7a8f', mfc='#d0aa93', linewidth=0.4, markersize=9)
    plt.axhline(y=avg, color='#da6517', linestyle='-', linewidth=0.8)

    plt.title(f'{coin} | Average {round_price(avg)} {pairing}',
              color=color_text_lines)
    ax.ticklabel_format(useOffset=False, style='plain')
    plt.ylabel(pairing, color=color_text_lines)
    plt.xlabel('Purchases', color=color_text_lines)
    plt.xticks([], [])

    # ax.grid('on', linestyle='--', linewidth=0.5, alpha = 0.5)
    ax.xaxis.set_tick_params(size=0)
    ax.yaxis.set_tick_params(size=0)
    ax.tick_params(axis='y', colors=color_text_lines)


    # ax.spines['bottom'].set_color('#6c6c72')
    # ax.spines['left'].set_color('#6c6c72')

    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()

    plt.savefig(f'trades/graph_{coin}.png')
    plt.close()


def calculate_stats(coin, df_orders, df_stats, stats_path):
    '''
    Given the df_orders calculate stats and append to df_stats,
        also, save to disk the stat df
    '''
    prices = df_orders['price'][df_orders['coin'] == coin].values
    costs = df_orders['cost'][df_orders['coin'] == coin].values
    # fees = df_orders['fee'][df_orders['coin'] == coin].values

    # Calculate the weighted average
    avg = (prices * costs).sum() / costs.sum()
    # Total asset accumulated
    fills = df_orders['filled'][df_orders['coin'] == coin].values
    total_asset = fills.sum()
    # Total cost:
    total_cost = costs.sum()

    # ROI
    roi = 100 * (prices[-1] - avg) / prices[-1]
    # Gain/Loss:
    gain = roi * total_cost / 100

    df_stats.loc[coin] = [len(prices), total_asset, avg, total_cost, gain, roi]
    # save stats to disk
    df_stats.to_csv(stats_path)
    return df_stats
    