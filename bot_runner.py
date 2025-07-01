# ------------------------------------------------------------------------------------
# 🤖 bot_runner.py — Main Trading Bot Loop (Multi-Timeframe + AI Sentiment + Dynamic SL/TP)
#
# 👨‍💻 Author: Terrence Ndifor (Terry)
# 📂 Project: Smart Multi-Timeframe Trading Bot
#
# 🔁 This script continuously runs your trading bot:
#    • Fetches candles from MetaTrader 5 for each symbol
#    • Performs full technical analysis (structure, FVG, OB, BOS, etc.)
#    • Evaluates EMA trend and market condition on selected timeframe
#    • Sends TA signals to a local LLaMA3 AI for macroeconomic sentiment
#    • AI returns directional bias (bullish, bearish, neutral) with reasoning
#    • Combines TA + AI sentiment to decide: BUY, SELL, or HOLD
#    • Automatically calculates SL/TP dynamically
#    • Places trade via MetaTrader5 interface (if conditions are met)
#
# 🛠️ Configurable via `config.py`:
#    • Lot size, SL/TP logic, EMA threshold by timeframe
#    • Timeframe used for technical analysis (M15, H1, H4, etc.)
#    • Delay between bot cycles (in seconds)
#    • Minimum technical score threshold for valid trades
#
# ▶️ Usage Example:
#     python bot_runner.py EURUSD XAUUSD US30 GOLD
#
# 🔄 Loops every X minutes and analyzes each pair in sequence
# 🧠 Uses local Ollama instance with "openchat:latest" for LLM reasoning
# ------------------------------------------------------------------------------------


import sys
import time
import MetaTrader5 as mt5
import requests
from get_candles import get_latest_candle_data
from strategy_engine import analyze_structure
from decision_engine import evaluate_trade_decision, calculate_dynamic_sl_tp
from broker_interface import initialize_mt5, shutdown_mt5, place_trade
from config import CONFIG

# === Settings ===
SYMBOLS = sys.argv[1:]  # Run like: python bot_runner.py EURUSD GBPUSD

if not SYMBOLS:
    print("❌ Please provide at least one symbol, e.g. `python bot_runner.py EURUSD GBPUSD`")
    sys.exit(1)

TIMEFRAME = mt5.TIMEFRAME_H1  # or mt5.TIMEFRAME_H4, mt5.TIMEFRAME_M30, etc.
LOT_SIZE = CONFIG.get("lot_size", 0.1)
DELAY_SECONDS = CONFIG.get("delay_seconds", 60 * 15)

# === Get AI Sentiment from local Ollama ===
def get_ai_sentiment(prompt):
    try:
        print("🛰️  Sending request to LLaMA3...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "openchat:latest", "prompt": prompt, "stream": False},
            timeout=180
        )
        print("📡 Response received!")
        return response.json().get("response", "")
    except Exception as e:
        print("❌ AI sentiment fetch failed:", e)
        return ""

# === Ensure Symbol Visibility ===
def ensure_symbol_visible(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"❌ Symbol {symbol} not found.")
    if not info.visible:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"❌ Failed to activate {symbol} in Market Watch.")

# === Main Bot Loop ===
def run_bot():
    initialize_mt5()
    try:
        while True:
            for symbol in SYMBOLS:
                print(f"\n⏳ Analyzing {symbol}...")
                ensure_symbol_visible(symbol)

                candles = get_latest_candle_data(symbol, TIMEFRAME)
                ta_signals = analyze_structure(candles, timeframe=TIMEFRAME)
                print("🔍 TA Signals:", ta_signals)

                prompt = f"""
                You are an expert trading assistant. Your job is to evaluate market bias based on technical analysis and macro sentiment.

                Symbol: {symbol}
                Recent Technical Signals:
                {ta_signals}

                1. Analyze the market's likely short-term direction.
                2. Identify if technicals and fundamentals agree or contradict.
                3. Clearly label the sentiment as: bullish, bearish, or neutral.
                4. State your confidence level (low, medium, high).
                5. Provide a brief rationale for your sentiment."""


                ai_sentiment = get_ai_sentiment(prompt)
                print("🧠 AI Sentiment:", ai_sentiment.strip())

                decision = evaluate_trade_decision(ta_signals, ai_sentiment)
                print("📈 Trade Decision:", decision)

                if decision in ["BUY", "SELL"]:
                    price = candles.iloc[-1]['close']
                    try:
                        sl, tp = calculate_dynamic_sl_tp(price, decision, candles)
                        print(f"🎯 Dynamic SL: {sl} | TP: {tp}")
                        place_trade(symbol, decision, lot=LOT_SIZE, sl=sl, tp=tp)
                    except Exception as err:
                        print(f"❌ SL/TP calculation error: {err}")

            print(f"⏲️ Waiting {DELAY_SECONDS / 60} minutes...")
            time.sleep(DELAY_SECONDS)

    except KeyboardInterrupt:
        print("🛑 Bot stopped by user.")
    except Exception as e:
        print(f"❌ Unhandled error: {e}")
    finally:
        shutdown_mt5()

if __name__ == "__main__":
    run_bot()
