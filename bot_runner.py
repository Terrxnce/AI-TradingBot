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
from datetime import datetime, timedelta
from get_candles import get_latest_candle_data
from strategy_engine import analyze_structure
from decision_engine import evaluate_trade_decision, calculate_dynamic_sl_tp, build_ai_prompt
from broker_interface import initialize_mt5, shutdown_mt5, place_trade
from config import CONFIG
from trailing_stop import apply_trailing_stop
from position_manager import check_for_2_percent_gain
from risk_guard import can_trade
from trade_logger import log_trade
from notifier import send_trade_notification

# === Settings ===
SYMBOLS = sys.argv[1:]
if not SYMBOLS:
    print("❌ Please provide at least one symbol, e.g. `python bot_runner.py EURUSD`")
    sys.exit(1)

TIMEFRAME = mt5.TIMEFRAME_M15
DELAY_SECONDS = CONFIG.get("delay_seconds", 60 * 15)
LOT_SIZE = CONFIG.get("lot_size", 1.0)

# === Session Detection ===
def detect_session():
    hour = datetime.now().hour
    if 0 <= hour < 7:
        return "Asia"
    elif 7 <= hour < 12:
        return "London"
    elif 12 <= hour < 20:
        return "New York"
    else:
        return "Post-Market"

# === Parse AI Sentiment ===
def parse_ai_sentiment(raw_response):
    lines = raw_response.strip().splitlines()
    parsed = {
        "confidence": "N/A",
        "reasoning": "",
        "risk_note": ""
    }
    current_section = None
    buffer = []

    for line in lines:
        line = line.strip()
        if line.startswith("CONFIDENCE:"):
            parsed["confidence"] = line.split(":", 1)[-1].strip()
            current_section = None
        elif line.startswith("REASONING:"):
            current_section = "reasoning"
            buffer = [line.split(":", 1)[-1].strip()]
        elif line.startswith("RISK_NOTE:"):
            if current_section == "reasoning":
                parsed["reasoning"] = " ".join(buffer).strip()
            current_section = "risk_note"
            buffer = [line.split(":", 1)[-1].strip()]
        elif current_section:
            buffer.append(line)

    if current_section == "reasoning":
        parsed["reasoning"] = " ".join(buffer).strip()
    elif current_section == "risk_note":
        parsed["risk_note"] = " ".join(buffer).strip()

    return parsed

# === AI Sentiment ===
def get_ai_sentiment(prompt):
    try:
        print("🚀  Sending request to LLaMA3...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "openchat:latest", "prompt": prompt, "stream": False},
            timeout=180
        )
        print("🛁 Response received!")
        return response.json().get("response", "")
    except Exception as e:
        print("❌ AI sentiment fetch failed:", e)
        return ""

# === Ensure MT5 Symbol is Visible ===
def ensure_symbol_visible(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"❌ Symbol {symbol} not found.")
    if not info.visible:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"❌ Failed to activate {symbol} in Market Watch.")

# === Main Bot Logic ===
def run_bot():
    initialize_mt5()
    trade_counter = {}

    try:
        while True:
            now = datetime.now()

            for sym in trade_counter:
                trade_counter[sym] = [
                    t for t in trade_counter[sym]
                    if (now - t).total_seconds() < 3600
                ]
            for symbol in SYMBOLS:
                print(f"\n⏳ Analyzing {symbol}...")
                ensure_symbol_visible(symbol)
                time.sleep(0.5)  # ensure visibility is applied before querying

                info = mt5.symbol_info(symbol)
                if info is None:
                    print(f"⚠️ Skipping {symbol} – could not resolve symbol info even after ensuring visibility.")
                    symbol_key = symbol.upper()
                else:
                    symbol_key = info.name.upper()

                candles_m15 = get_latest_candle_data(symbol, mt5.TIMEFRAME_M15)
                candles_h1 = get_latest_candle_data(symbol, mt5.TIMEFRAME_H1)

                ta_m15 = analyze_structure(candles_m15, timeframe=mt5.TIMEFRAME_M15)
                ta_h1 = analyze_structure(candles_h1, timeframe=mt5.TIMEFRAME_H1)
                session = detect_session()

                ta_signals = {**ta_m15, "h1_trend": ta_h1["ema_trend"], "session": session}
                print("🕐 Current Session:", session)
                print("🔍 TA Signals:", ta_signals)

                prompt = build_ai_prompt(ta_signals=ta_signals, session_info=session, macro_sentiment="neutral")
                ai_sentiment = get_ai_sentiment(prompt)
                print("🧠 AI Response:\n", ai_sentiment.strip())

                decision = evaluate_trade_decision(ta_signals, ai_sentiment)
                print(f"📈 Trade Decision: {decision}")
                print(f"🔍 Raw decision value: [{decision}] (type: {type(decision)})")

                if not can_trade(ta_signals=ta_signals, ai_response_raw=ai_sentiment, call_ai_func=get_ai_sentiment):
                    print(f"⚠️ Skipped {symbol} — blocked by risk_guard.")
                    continue

                # 🚨 Clean and enforce 2-per-hour rule per symbol
                now = datetime.now()
                symbol_key = symbol.upper()
                trade_counter.setdefault(symbol_key, [])

                # Remove timestamps older than 1 hour
                trade_counter[symbol_key] = [
                    t for t in trade_counter[symbol_key]
                    if (now - t).total_seconds() < 3600
                ]

                # Debug print to confirm tracking
                print(f"📊 Trades on {symbol_key} in last hour: {len(trade_counter[symbol_key])}")

                # Block trade if over limit
                if len(trade_counter[symbol_key]) >= 2:
                    print(f"⛔ Skipping {symbol_key}: 2-trade-per-hour limit reached.")
                    continue


                if decision in ["BUY", "SELL"]:
                    try:
                        price = candles_m15.iloc[-1]["close"]
                        sl, tp = calculate_dynamic_sl_tp(price, decision, candles_m15)
                        lot_sizes = {k.upper(): v for k, v in CONFIG.get("LOT_SIZES", {}).items()}
                        lot = lot_sizes.get(symbol_key, CONFIG.get("lot_size", 1.0))

                        print(f"🧮 Resolved lot size for {symbol}: {lot}")
                        print(f"🎯 Dynamic SL: {sl} | TP: {tp} | Lot: {lot}")
                        print(f"🚀 Preparing to place trade: {symbol} | Direction: {decision}")

                        ai_data = parse_ai_sentiment(ai_sentiment)
                        tech_score = ta_signals.get("score", "N/A")
                        ema_trend = ta_signals.get("ema_trend", ta_signals.get("h1_trend", "N/A"))

                        success = place_trade(
                            symbol=symbol,
                            action=decision,
                            lot=lot,
                            sl=sl,
                            tp=tp,
                            tech_score=tech_score,
                            ema_trend=ema_trend,
                            ai_confidence=ai_data["confidence"],
                            ai_reasoning=ai_data["reasoning"],
                            risk_note=ai_data["risk_note"]
                        )

                        if success:
                            log_trade(symbol, decision, lot, sl, tp, price, result="EXECUTED")
                            trade_counter[symbol_key].append(now)
                            send_trade_notification(
                                symbol=symbol,
                                direction=decision,
                                entry=price,
                                sl=sl,
                                tp=tp,
                                lot=lot,
                                tech_score=tech_score,
                                ema_trend=ema_trend,
                                ai_confidence=ai_data["confidence"],
                                ai_reasoning=ai_data["reasoning"],
                                risk_note=ai_data["risk_note"]
                            )
                        else:
                            log_trade(symbol, decision, lot, sl, tp, price, result="FAILED")

                    except Exception as err:
                        print(f"❌ SL/TP or lot sizing error: {err}")
                        log_trade(symbol, decision, lot, sl, tp, price, result=f"FAILED: {err}")

            apply_trailing_stop(minutes=30, trail_pips=20)
            check_for_2_percent_gain()

            print(f"⏲ Waiting {DELAY_SECONDS / 60} minutes...")
            time.sleep(DELAY_SECONDS)

    except KeyboardInterrupt:
        print("🛑 Bot stopped by user.")
    except Exception as e:
        print(f"❌ Unhandled error: {e}")
    finally:
        shutdown_mt5()


if __name__ == "__main__":
    run_bot()
