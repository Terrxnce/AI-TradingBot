import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

def fetch_mt5_data(symbol="EURUSD", timeframe=mt5.TIMEFRAME_M15, bars=200):
    """
    Connects to MetaTrader 5 and retrieves historical OHLCV candle data.

    Args:
        symbol (str): Symbol to fetch (e.g., "EURUSD").
        timeframe: MT5 timeframe constant (e.g., mt5.TIMEFRAME_M15).
        bars (int): Number of bars to retrieve.

    Returns:
        pd.DataFrame: DataFrame with time, open, high, low, close, and tick_volume.
    """
    if not mt5.initialize():
        raise Exception("❌ MT5 initialization failed. Make sure MetaTrader is installed, logged in, and the symbol is valid.")

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        mt5.shutdown()
        raise Exception("❌ Failed to fetch data from MT5.")

    mt5.shutdown()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]

def get_latest_candle_data(symbol, timeframe, bars=200):
    """
    Wrapper to fetch recent candles with default 200-bar window.
    """
    return fetch_mt5_data(symbol=symbol, timeframe=timeframe, bars=bars)

def get_multi_tf_data(symbol, timeframes=[mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1]):
    data = {}
    for tf in timeframes:
        df = fetch_mt5_data(symbol, tf, bars=200)
        data[tf] = df
    return data


# === Test Mode ===
if __name__ == "__main__":
    df = get_latest_candle_data("EURUSD", mt5.TIMEFRAME_M15)
    print(df.tail())

# ------------------------------------------------------------------------------------
# 📦 get_candles.py – Live Candle Data Fetcher for MT5
#
# This module handles all price data retrieval for the trading bot.
# It connects to MetaTrader 5, pulls historical OHLCV data, and returns a
# Pandas DataFrame suitable for downstream analysis.
#
# ✅ fetch_mt5_data() – Fetches clean candle data from MT5
# ✅ get_latest_candle_data() – Used in bot_runner.py to supply live candles
#
# Fields Returned:
#   - time, open, high, low, close, tick_volume
#
# Used by: strategy_engine.py for analysis, bot_runner.py for execution
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------