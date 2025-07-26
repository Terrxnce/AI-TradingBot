# ------------------------------------------------------------------------------------
# 🤖 bot_runner.py — Main Trading Bot Loop (Multi-Timeframe + AI Sentiment + Dynamic SL/TP)
#
# 👨‍💻 Author: Terrence Ndifor (Terry)
# 📂 Project: Smart Multi-Timeframe Trading Bot
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
from position_manager import check_for_partial_close, close_trades_at_4pm
from risk_guard import can_trade
from trade_logger import log_trade
from session_utils import detect_session
from news_guard import get_macro_sentiment
from profit_guard import check_and_lock_profits
import json 



from datetime import time as dt_time

# === Settings ===
SYMBOLS = sys.argv[1:]
if not SYMBOLS:
    print("❌ Please provide at least one symbol, e.g. `python bot_runner.py EURUSD`")
    sys.exit(1)

TIMEFRAME = mt5.TIMEFRAME_M15
DELAY_SECONDS = CONFIG.get("delay_seconds", 60 * 15)
LOT_SIZE = CONFIG.get("lot_size", 1.0)

def is_pm_session():
    now = datetime.now().time()
    return dt_time(17, 0) <= now <= dt_time(21, 0)

# === Parse AI Sentiment ===
def parse_ai_sentiment(raw_response):
    lines = raw_response.strip().splitlines()
    parsed = {"confidence": "N/A", "reasoning": "", "risk_note": ""}
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

def log_ai_decision(symbol, ai_data, timestamp=None):
    """
    Append AI decision to ai_decision_log.jsonl
    """
    entry = {
        "timestamp": timestamp or datetime.now().isoformat(),
        "symbol": symbol,
        "confidence": ai_data.get("confidence", "N/A"),
        "reasoning": ai_data.get("reasoning", ""),
        "risk_note": ai_data.get("risk_note", "")
    }

    try:
        with open("ai_decision_log.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"❌ Failed to write AI decision log: {e}")


# === AI Sentiment ===
def get_ai_sentiment(prompt):
    try:
        print("🚀  Sending request to LLaMA3...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "openchat:latest", "prompt": prompt, "stream": False},
            timeout=180
        )
        print("💫 Response received!")
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
            if not mt5.terminal_info() or not mt5.version():
                print("⚠️ MT5 appears disconnected. Reinitializing...")
                shutdown_mt5()
                time.sleep(2)
                initialize_mt5()

            now = datetime.now()
            current_hour = now.hour

            for sym in trade_counter:
                trade_counter[sym] = [t for t in trade_counter[sym] if (now - t).total_seconds() < 3600]

            # Check for 4PM close trades
            close_trades_at_4pm()

            for symbol in SYMBOLS:
                print(f"\n⏳ Analyzing {symbol}...")

                check_and_lock_profits()

                if CONFIG.get("restrict_usd_to_am", False):
                    keywords = CONFIG.get("usd_related_keywords", [])
                    if any(k in symbol.upper() for k in keywords):
                        time_window = CONFIG.get("allowed_trading_window", {})
                        start = time_window.get("start_hour", 9)
                        end = time_window.get("end_hour", 11)
                        if not (start <= current_hour < end):
                            print(f"⏳ Skipping {symbol} — outside {start}:00–{end}:00 window for USD-related pairs.")
                            continue

                try:
                    ensure_symbol_visible(symbol)
                except Exception as e:
                    print(f"❌ Failed to ensure symbol visibility for {symbol}: {e}")
                    continue
                time.sleep(0.5)

                info = mt5.symbol_info(symbol)
                symbol_key = symbol.upper() if info is None else info.name.upper()
                if info is None:
                    print(f"⚠️ Skipping {symbol} – could not resolve symbol info.")
                    continue

                candles_m15 = get_latest_candle_data(symbol, mt5.TIMEFRAME_M15)
                candles_h1 = get_latest_candle_data(symbol, mt5.TIMEFRAME_H1)

                ta_m15 = analyze_structure(candles_m15, timeframe=mt5.TIMEFRAME_M15)
                ta_h1 = analyze_structure(candles_h1, timeframe=mt5.TIMEFRAME_H1)
                session = detect_session()

                ta_signals = {**ta_m15, "h1_trend": ta_h1["ema_trend"], "session": session}
                ta_signals["symbol"] = symbol

                print("🕒 Current Session:", session)
                print("🔍 TA Signals:", ta_signals)

                macro_sentiment = get_macro_sentiment(symbol)
                prompt = build_ai_prompt(ta_signals=ta_signals, session_info=session, macro_sentiment=macro_sentiment)
                ai_sentiment = get_ai_sentiment(prompt)
                print("🧠 AI Response:\n", ai_sentiment.strip())

                if CONFIG.get("enable_pm_session_only", False) and not is_pm_session():
                    print(f"⏳ Skipping {symbol} — outside PM session window.")
                    continue

                decision = evaluate_trade_decision(ta_signals, ai_sentiment)
                print(f"📈 Trade Decision: {decision}")

                technical_score = 0.0
                if ta_signals.get("bos") in ["bullish", "bearish"]:
                    technical_score += 2.0
                if ta_signals.get("fvg_valid"):
                    technical_score += 2.0
                if ta_signals.get("ob_tap"):
                    technical_score += 1.5
                if ta_signals.get("rejection"):
                    technical_score += 1.0
                if ta_signals.get("liquidity_sweep"):
                    technical_score += 1.0
                if ta_signals.get("engulfing"):
                    technical_score += 0.5

                if not can_trade(ta_signals=ta_signals, ai_response_raw=ai_sentiment, call_ai_func=get_ai_sentiment, tech_score=technical_score):
                    print(f"⚠️ Skipped {symbol} — blocked by risk_guard.")
                    continue

                trade_counter.setdefault(symbol_key, [])
                trade_counter[symbol_key] = [t for t in trade_counter[symbol_key] if (now - t).total_seconds() < 3600]

                if len(trade_counter[symbol_key]) >= 2:
                    print(f"❌ Skipping {symbol_key}: 2-trade-per-hour limit reached.")
                    continue

                ai_data = parse_ai_sentiment(ai_sentiment)
                ema_trend = ta_signals.get("ema_trend", ta_signals.get("h1_trend", "N/A"))
                ai_direction = decision
                final_direction = ai_direction
                execution_source = "AI"
                override_reason = ""

                if technical_score >= CONFIG["min_score_for_trade"] and ema_trend in ["bullish", "bearish"]:
                    if ai_direction == "HOLD":
                        final_direction = "BUY" if ema_trend == "bullish" else "SELL"
                        execution_source = "technical_override"
                        override_reason = f"Technical score {technical_score} overrode AI HOLD"

                success = False
                if final_direction in ["BUY", "SELL"]:
                    try:
                        if not mt5.terminal_info() or not mt5.version():
                            print("⚠️ Reinitializing MT5 before trade placement...")
                            shutdown_mt5()
                            time.sleep(2)
                            initialize_mt5()

                        price = candles_m15.iloc[-1]["close"]
                        sl, tp = calculate_dynamic_sl_tp(price, final_direction, candles_m15)
                        lot_sizes = {k.upper(): v for k, v in CONFIG.get("LOT_SIZES", {}).items()}
                        lot = lot_sizes.get(symbol_key, CONFIG.get("lot_size", 1.0))

                        print(f"🧶 Resolved lot size for {symbol}: {lot}")
                        print(f"🎯 Dynamic SL: {sl} | TP: {tp} | Lot: {lot}")

                        success = place_trade(
                            symbol=symbol,
                            action=final_direction,
                            lot=lot,
                            sl=sl,
                            tp=tp,
                            tech_score=f"{technical_score:.1f} / 8.0",
                            ema_trend=ema_trend,
                            ai_confidence=ai_data["confidence"],
                            ai_reasoning=ai_data["reasoning"],
                            risk_note=ai_data["risk_note"]
                        )

                        if success:
                            log_trade(symbol, final_direction, lot, sl, tp, price, result="EXECUTED")
                            trade_counter[symbol_key].append(now)

                    except Exception as err:
                        print(f"❌ SL/TP or lot sizing error: {err}")
                        log_trade(symbol, final_direction, lot, sl, tp, price, result=f"FAILED: {err}")

                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "symbol": symbol,
                    "ai_decision": ai_direction,
                    "ai_confidence": ai_data["confidence"],
                    "ai_reasoning": ai_data["reasoning"],
                    "ai_risk_note": ai_data["risk_note"],
                    "technical_score": technical_score,
                    "ema_trend": ema_trend,
                    "final_direction": final_direction,
                    "executed": success,
                    "ai_override": final_direction != ai_direction,
                    "override_reason": override_reason,
                    "execution_source": execution_source
                }

                with open("ai_decision_log.jsonl", "a") as f:
                    f.write(json.dumps(log_entry) + "\n")

            apply_trailing_stop(minutes=30, trail_pips=20)
            check_for_partial_close()
            print(f"⏲ Waiting {DELAY_SECONDS / 60} minutes...")
            time.sleep(DELAY_SECONDS)

    except KeyboardInterrupt:
        print("🚑 Bot stopped by user.")
    except Exception as e:
        print(f"❌ Unhandled error: {e}")
        if "not found" in str(e).lower() or "not initialized" in str(e).lower():
            print("🔁 Attempting to reinitialize MT5...")
            shutdown_mt5()
            time.sleep(2)
            initialize_mt5()
        else:
            raise
    finally:
        shutdown_mt5()

if __name__ == "__main__":
    run_bot()

