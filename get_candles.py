import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

def fetch_mt5_data(symbol="EURUSD", timeframe=mt5.TIMEFRAME_H1, bars=200):
    # Initialize connection
    if not mt5.initialize():
        raise Exception("MT5 initialization failed")

    # Get rates
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        raise Exception("Failed to fetch data from MT5")

    # Shutdown connection
    mt5.shutdown()

    # Create DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]

# Test run
if __name__ == "__main__":
    df = fetch_mt5_data()
    print(df.tail())
