import pandas as pd
from utils.indicators import calculate_ema
from strategy_engine import analyze_structure
from decision_engine import calculate_dynamic_sl_tp
from backtest_trade_manager import BacktestTradeManager
import os

from trade_logger import save_trade_log

def load_csv_data(path, start, end):
    df = pd.read_csv(path, parse_dates=["Time"])
    df.columns = [col.lower() for col in df.columns]
    df = df[(df["time"] >= pd.to_datetime(start)) & (df["time"] <= pd.to_datetime(end))]
    df.reset_index(drop=True, inplace=True)
    print(f"📁 Loaded {len(df)} candles from CSV between {start} and {end}")
    return df

def calculate_score(signals):
    score = 0
    if signals.get("bos") in ["bullish", "bearish"]:
        score += 2
    if signals.get("fvg_valid"):
        score += 2
    if signals.get("ob_tap"):
        score += 1.5
    if signals.get("rejection"):
        score += 1
    if signals.get("liquidity_sweep"):
        score += 1
    if signals.get("engulfing"):
        score += 0.5
    return score

def run_backtest(df, window_size=300, verbose=False):
    df["ema_21"] = calculate_ema(df, 21)
    df["ema_50"] = calculate_ema(df, 50)
    df["ema_200"] = calculate_ema(df, 200)

    tm = BacktestTradeManager()  # ← multi-trade capable
    high_score_signals = 0
    skipped_due_to_sl_tp = 0

    for i in range(window_size, len(df)):
        window = df.iloc[i - window_size:i + 1]
        signals = analyze_structure(window)
        score = calculate_score(signals)

        candle = df.iloc[i]
        timestamp = candle["time"]
        direction = "buy" if signals["ema_trend"] == "bullish" else "sell" if signals["ema_trend"] == "bearish" else None

        if verbose or i % 500 == 0:
            print(f"[{timestamp}] EMA: {signals['ema_trend']} | Score: {score}")

        if score >= 5 and direction:
            high_score_signals += 1
            entry_price = candle["close"]
            try:
                sl, tp = calculate_dynamic_sl_tp(
                    price=entry_price,
                    direction=direction.upper(),
                    candles_df=window
                )
                tm.enter_trade(direction, entry_price, sl, tp, timestamp, index=i)
                print(f"✅ TRADE [{direction.upper()}] | Score: {score} | Entry: {entry_price:.5f} | SL: {sl:.5f} | TP: {tp:.5f}")
            except Exception as e:
                skipped_due_to_sl_tp += 1
                print(f"⚠️ Failed to calculate SL/TP at {timestamp}: {e}")

        tm.check_all_trades(candle)  # ← updated for multi-trade management

    print(f"\n📌 Signals with score ≥ 5 and direction: {high_score_signals}")
    print(f"✅ Executed trades: {tm.total_trades}")
    print(f"⛔ Skipped due to SL/TP failure: {skipped_due_to_sl_tp}")

    print("\n🏁 Backtest Results:")
    results = tm.get_results()
    print(results)

    # ✅ Save to file
    symbol = os.path.basename(CSV_PATH).split("_")[0]  # Extracts 'USDJPY' or 'EURUSD'
    save_trade_log(tm.trade_log, file_path=f"results/{symbol}_backtest.csv")


if __name__ == "__main__":
    CSV_PATH = "data/GBPJPY_M15.csv"
    START_DATE = "2024-01-01"
    END_DATE = "2024-07-01"
    df = load_csv_data(CSV_PATH, START_DATE, END_DATE)
    run_backtest(df, window_size=300, verbose=True)
