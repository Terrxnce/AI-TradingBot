import sys
import time
import MetaTrader5 as mt5
from get_candles import get_latest_candle_data
from strategy_engine import analyze_structure
from decision_engine import evaluate_trade_decision
from broker_interface import initialize_mt5, shutdown_mt5, place_trade
import requests

# === Get symbols from command line ===
SYMBOLS = sys.argv[1:]  # Get all passed symbols, e.g. EURUSD GBPUSD

if not SYMBOLS:
    print("❌ Please provide at least one symbol, e.g. `python bot_runner.py EURUSD GBPUSD`")
    sys.exit(1)

TIMEFRAME = mt5.TIMEFRAME_M15
LOT_SIZE = 0.1
SL_PIPS = 50
TP_PIPS = 100
DELAY_SECONDS = 60 * 15


# === Get AI Sentiment from local Ollama ===
def get_ai_sentiment(prompt):
    try:
        print("🛰️  Sending request to LLaMA3...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3:latest", "prompt": prompt, "stream": False},
            timeout=180
        )
        print("📡 Response received!")
        return response.json().get("response", "")
    except Exception as e:
        print("❌ AI sentiment fetch failed:", e)
        return ""


# === Main Loop ===
def ensure_symbol_visible(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"❌ Symbol {symbol} not found.")
    if not info.visible:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"❌ Failed to activate {symbol} in Market Watch.")

def run_bot():
    initialize_mt5()
    try:
        while True:
            for symbol in SYMBOLS:
                print(f"\n⏳ Analyzing {symbol}...")
                ensure_symbol_visible(symbol)

                candles = get_latest_candle_data(symbol, TIMEFRAME)
                ta_signals = analyze_structure(candles)
                print("🔍 TA Signals:", ta_signals)

                prompt = f"Summarize the current market bias for {symbol} based on recent economic news."
                ai_sentiment = get_ai_sentiment(prompt)
                print("🧠 AI Sentiment:", ai_sentiment.strip())

                decision = evaluate_trade_decision(ta_signals, ai_sentiment)
                print("📈 Trade Decision:", decision)

                if decision in ["BUY", "SELL"]:
                    place_trade(symbol, decision, lot=LOT_SIZE)

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
