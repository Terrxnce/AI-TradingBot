# trade_logger.py

import pandas as pd
import os

def save_trade_log(trade_log, file_path):
    """
    Save all executed trades to a CSV file.

    Args:
        trade_log (list): List of trade dicts from BacktestTradeManager
        file_path (str): Path to save the CSV
    """

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    rows = []
    for trade in trade_log:
        entry_time = trade["entry_time"]
        exit_time = trade["exit_time"]
        duration = (exit_time - entry_time).total_seconds() / 60 if entry_time and exit_time else None
        reward = abs(trade["tp"] - trade["entry_price"])
        risk = abs(trade["entry_price"] - trade["sl"])

        if trade["status"] == "won":
            pnl = reward
        elif trade["status"] == "lost":
            pnl = -risk
        else:
            pnl = 0

        rows.append({
            "entry_time": entry_time,
            "exit_time": exit_time,
            "duration_min": round(duration, 2) if duration else None,
            "direction": trade["direction"],
            "entry_price": round(trade["entry_price"], 5),
            "exit_price": round(trade["exit_price"], 5) if trade["exit_price"] else None,
            "sl": round(trade["sl"], 5),
            "tp": round(trade["tp"], 5),
            "status": trade["status"],
            "pnl": round(pnl, 5)
        })

    df = pd.DataFrame(rows)
    df.to_csv(file_path, index=False)
    print(f"📦 Trade log saved to: {file_path}")
