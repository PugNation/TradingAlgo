import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ib_insync import *
from statsmodels.tsa.stattools import coint


def fetch_delayed_data(ib, ticker, duration, bar_size):
    """Fetch delayed historical data from IB API."""
    bars = ib.reqHistoricalData(
        contract=ticker,
        endDateTime='',
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1
    )
    if not bars:
        print(f"No data returned for {ticker.symbol}")
        return pd.DataFrame()
    
    data = util.df(bars)
    if 'date' in data.columns:
        data.set_index('date', inplace=True)
    return data['close']


def calculate_half_life(spread):
    """Calculate the half-life of mean reversion for the spread."""
    spread_lag = spread.shift(1).dropna()
    delta_spread = spread.diff().dropna()
    beta = np.polyfit(spread_lag, delta_spread, 1)[0]
    half_life = -np.log(2) / beta
    return max(1, half_life)  # Ensure half-life is positive

def adaptive_thresholds(spread, window=60):
    """Calculate adaptive buy/sell thresholds based on spread volatility."""
    rolling_std = spread.rolling(window).std()
    upper_threshold = rolling_std * 2
    lower_threshold = -rolling_std * 2
    return upper_threshold, lower_threshold


def calculate_hedge_ratio(y, x):
    """Calculate the hedge ratio using numpy."""
    cov_matrix = np.cov(y, x)
    hedge_ratio = cov_matrix[0, 1] / cov_matrix[1, 1]  # Covariance / Variance
    return hedge_ratio


def calculate_spread(y, x, hedge_ratio):
    """Calculate the spread between two assets."""
    return y - hedge_ratio * x

def calculate_zscore(spread, window=30):
    """Calculate the z-score for the spread."""
    rolling_mean = spread.rolling(window).mean()
    rolling_std = spread.rolling(window).std()
    zscore = (spread - rolling_mean) / rolling_std
    return zscore

def plot_strategy(zscore, spread, buy_signals, sell_signals):
    """Plot Z-Score, Spread, and Buy/Sell Signals."""
    plt.figure(figsize=(14, 7))

    # Z-Score Plot
    plt.subplot(2, 1, 1)
    plt.plot(zscore.index, zscore, label='Z-Score', color='blue')
    plt.axhline(0, color='gray', linestyle='--')
    plt.axhline(1.0, color='purple', linestyle='--', label='Sell Threshold (+1.0)')
    plt.axhline(-1.0, color='purple', linestyle='--', label='Buy Threshold (-1.0)')
    plt.scatter(buy_signals.index, buy_signals, color='green', marker='^', label='Buy Signal')
    plt.scatter(sell_signals.index, sell_signals, color='red', marker='v', label='Sell Signal')
    plt.title('Z-Score with Buy/Sell Signals')
    plt.legend()
    plt.grid(True)
     
    # Spread Plot
    plt.subplot(2, 1, 2)
    plt.plot(spread.index, spread, label='Spread', color='blue')
    plt.axhline(0, color='gray', linestyle='--')
    plt.scatter(buy_signals.index, spread[buy_signals.index], color='green', marker='^', label='Buy Signal')
    plt.scatter(sell_signals.index, spread[sell_signals.index], color='red', marker='v', label='Sell Signal')
    plt.title('Spread with Buy/Sell Signals')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()

def main():
    # Connect to Interactive Brokers
    ib = IB()
    try:
        ib.connect('127.0.0.1', 7497, clientId=1)
    except Exception as e:
        print(f"Failed to connect to IB: {e}")
        return

    # Define stocks
    ticker1 = Stock('YUM', 'SMART', 'USD')
    ticker2 = Stock('MDT', 'SMART', 'USD')

    # Fetch delayed data
    duration = "360 D"  # Longer timescale
    bar_size = "10 day"
    y_data = fetch_delayed_data(ib, ticker1, duration, bar_size)
    x_data = fetch_delayed_data(ib, ticker2, duration, bar_size)

    if y_data.empty or x_data.empty:
        print("Failed to fetch data. Exiting.")
        return

    # Align data
    combined = pd.concat([y_data, x_data], axis=1).dropna()
    combined.columns = ['Asset Y', 'Asset X']



    # Calculate hedge ratio and spread
    hedge_ratio = calculate_hedge_ratio(combined['Asset Y'], combined['Asset X'])
    spread = calculate_spread(combined['Asset Y'], combined['Asset X'], hedge_ratio)

    # Calculate half-life and Z-score
    half_life = calculate_half_life(spread)
    zscore = calculate_zscore(spread, window=int(half_life))

    # Generate adaptive thresholds
    upper_threshold, lower_threshold = adaptive_thresholds(spread, window=60)
    buy_signals = zscore[zscore < lower_threshold]
    sell_signals = zscore[zscore > upper_threshold]

    # Plot strategy
    plot_strategy(zscore, spread, buy_signals, sell_signals)


if __name__ == "__main__":
    main()
