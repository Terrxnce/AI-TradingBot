import pandas as pd
import os
from datetime import datetime

def log_trade(symbol, direction, lot, sl, tp, entry_price, result):
    """
    Append a single trade to a CSV log file.
    """
    log_path = "logs/trade_log.csv"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    trade_data = {
        "timestamp": datetime.now(),
        "symbol": symbol,
        "direction": direction,
        "lot": lot,
        "sl": sl,
        "tp": tp,
        "entry_price": entry_price,
        "result": result
    }

    df = pd.DataFrame([trade_data])
    if os.path.exists(log_path):
        df.to_csv(log_path, mode='a', header=False, index=False)
    else:
        df.to_csv(log_path, index=False)

    print(f"✅ Trade logged: {symbol} | {direction} | Result: {result}")

