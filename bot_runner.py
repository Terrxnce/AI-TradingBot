import sys
import time
import MetaTrader5 as mt5
from get_candles import get_latest_candle_data
from strategy_engine import TechnicalAnalyzer # Updated import
# from decision_engine import evaluate_trade_decision # Will be simplified/bypassed
from broker_interface import initialize_mt5, shutdown_mt5, place_trade
import requests
import pandas as pd # For creating DataFrame from candles if needed by TA

# === PINE SCRIPT CONFIGURATION (as per user's Pine Script inputs) ===
# This should ideally be in a separate config file or UI later
DEFAULT_PINE_CONFIG = {
    'useSessionFilter': True,
    'useEMAFilter': True,
    'useOrderBlocks': True,
    'useFVGs': True,
    'respectFVGMidpoint': True,
    'useBOS': True,
    'useEngulfing': True,
    'useLiquiditySweep': True, # Master toggle for liquidity sweeps
    'checkAsiaSweep': True,    # Specific sweep check
    'checkLondonSweep': True,  # Specific sweep check
    'showTP2': True, # For TechnicalAnalyzer to potentially return TP2 level
    # Add any other inputs from Pine Script if they affect logic directly
}


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
                # candles is a list of dictionaries/namedtuples from get_latest_candle_data
                # TechnicalAnalyzer expects a pandas DataFrame
                if not candles:
                    print(f"ℹ️ No candle data fetched for {symbol}. Skipping analysis.")
                    continue

                candles_df = pd.DataFrame(candles)
                # Ensure 'time' column is datetime if TechnicalAnalyzer._ensure_datetime_index expects it
                # get_latest_candle_data already converts 'time' to datetime objects.
                # If TA expects 'time' as index, set it:
                if 'time' in candles_df.columns:
                    candles_df = candles_df.set_index('time')
                else:
                    print(f"❌ 'time' column missing in candle data for {symbol}. Skipping TA.")
                    continue


                # Initialize TechnicalAnalyzer with the DataFrame
                ta = TechnicalAnalyzer(candles_df)
                ta.set_pine_config(DEFAULT_PINE_CONFIG) # Set the Pine Script configuration

                # Get signal from the new Pine Script logic
                pine_signal_result = ta.get_pine_script_signal()
                decision = pine_signal_result.get("signal", "HOLD") # "BUY" or "HOLD"

                print(f"🌲 Pine Script Signal for {symbol}: {decision} (Reason: {pine_signal_result.get('reason')})")
                if decision == "BUY" and pine_signal_result.get('latest_signals_debug'):
                    print(f"🔍 Raw Pine Signals: {pine_signal_result['latest_signals_debug']}")


                # --- AI Sentiment (Optional - can be re-integrated later) ---
                # For now, we are focusing on the Pine Script logic.
                # prompt = f"Summarize the current market bias for {symbol} based on recent economic news."
                # ai_sentiment = get_ai_sentiment(prompt)
                # print("🧠 AI Sentiment:", ai_sentiment.strip())
                #
                # Combined Decision (Example if you want to combine later)
                # if decision == "BUY" and "bullish" in ai_sentiment.lower():
                #    final_decision = "BUY"
                # else:
                #    final_decision = "HOLD"
                # print("📈 Final Combined Decision:", final_decision)
                # decision = final_decision #

                print(f"📈 Final Trade Decision for {symbol}: {decision}")

                if decision == "BUY": # Only handling BUY based on current Pine Script translation
                    symbol_info = mt5.symbol_info(symbol) # Already fetched earlier by ensure_symbol_visible
                    if symbol_info is None:
                        print(f"❌ Could not get symbol info for {symbol} in bot_runner to calculate SL/TP. Skipping trade.")
                        continue

                    # Determine entry price based on action
                    tick = mt5.symbol_info_tick(symbol)
                    if tick is None:
                        print(f"❌ Could not get tick data for {symbol} to determine entry price for SL/TP calc. Skipping trade.")
                        continue

                    entry_price = tick.ask if decision == "BUY" else tick.bid

                    # Calculate SL and TP based on 35 pips
                    # Assuming 1 pip = 10 points for a 5-digit broker.
                    # Adjust if your definition of a pip or broker's point system is different.
                    # point_value = symbol_info.point
                    # pip_value_in_price = 35 * 10 * point_value # 35 pips

                    # More direct: for EURUSD, 35 pips = 0.0035
                    # This needs to be symbol-specific if you trade other instruments
                    # For simplicity, using a fixed offset, but ideally, this should be dynamic per symbol.
                    # Let's use a more robust way using 'point' which is the smallest price unit.
                    # If 1 pip = 0.0001 for EURUSD (4th decimal for 5-digit price)
                    # And point = 0.00001 for EURUSD
                    # Then 1 pip = 10 points.
                    # So, 35 pips = 35 * 10 * point = 350 * point

                    points_for_sl_tp = 350  # 35 pips * 10 points/pip
                    price_offset = points_for_sl_tp * symbol_info.point

                    sl_price = 0.0
                    tp_price = 0.0

                    if decision == "BUY":
                        sl_price = entry_price - price_offset
                        tp_price = entry_price + price_offset
                    elif decision == "SELL":
                        sl_price = entry_price + price_offset
                        tp_price = entry_price - price_offset

                    print(f"ℹ️ Calculated for {decision} {symbol}: Entry={entry_price:.{symbol_info.digits}f}, SL={sl_price:.{symbol_info.digits}f}, TP={tp_price:.{symbol_info.digits}f} (based on 35 pips)")

                    place_trade(symbol, decision, lot=LOT_SIZE, sl_price=sl_price, tp_price=tp_price)

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
