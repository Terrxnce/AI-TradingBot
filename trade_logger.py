import csv
import os
from datetime import datetime

def log_trade(symbol, action, lot, sl, tp, price, result="EXECUTED"):
    filename = "trade_log.csv"
    file_exists = os.path.isfile(filename)

    with open(filename, mode="a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "symbol", "action", "lot", "price", "sl", "tp", "result"])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            action,
            lot,
            round(price, 5),
            round(sl, 5),
            round(tp, 5),
            result
        ])
