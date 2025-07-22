# save_csv_from_mt5.py

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# === CONFIG ===
symbol = "GBPJPY"
timeframe = mt5.TIMEFRAME_M15
from_date = datetime(2024, 1, 1)
to_date = datetime(2024, 7, 1)
output_path = "data/GBPJPY_M15.csv"

# === CONNECT TO MT5 ===
if not mt5.initialize():
    print("MT5 Init failed:", mt5.last_error())
    exit()

# === FETCH RATES ===
rates = mt5.copy_rates_range(symbol, timeframe, from_date, to_date)
if rates is None:
    print("Failed to get data:", mt5.last_error())
    mt5.shutdown()
    exit()

# === CLEANUP ===
mt5.shutdown()

# === FORMAT DATAFRAME ===
df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")
df.rename(columns={
    "time": "Time",
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "tick_volume": "Volume"
}, inplace=True)

df = df[["Time", "Open", "High", "Low", "Close", "Volume"]]
df.to_csv(output_path, index=False)

print(f"✅ CSV saved to {output_path} with {len(df)} rows.")
