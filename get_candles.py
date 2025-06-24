import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime


def fetch_mt5_data(symbol="EURUSD", timeframe=mt5.TIMEFRAME_M15, bars=200):
    if not mt5.initialize():
        raise Exception("MT5 initialization failed")

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        raise Exception("Failed to fetch data from MT5")

    mt5.shutdown()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]


def get_latest_candle_data(symbol, timeframe):
    return fetch_mt5_data(symbol=symbol, timeframe=timeframe)


# Test run
if __name__ == "__main__":
    df = get_latest_candle_data("EURUSD", mt5.TIMEFRAME_M15)
    print(df.tail())