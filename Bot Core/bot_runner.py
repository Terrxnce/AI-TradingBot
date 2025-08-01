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
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from get_candles import get_latest_candle_data
from strategy_engine import analyze_structure
from decision_engine import evaluate_trade_decision, calculate_dynamic_sl_tp, build_ai_prompt
from broker_interface import initialize_mt5, shutdown_mt5, place_trade
import importlib
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
import config
from trailing_stop import apply_trailing_stop
from position_manager import check_for_partial_close, close_trades_at_4pm
from risk_guard import can_trade
from trade_logger import log_trade
from session_utils import detect_session
from news_guard import get_macro_sentiment, should_block_trading
from profit_guard import check_and_lock_profits
from error_handler import safe_mt5_operation, validate_trade_parameters, performance_monitor
from performance_metrics import performance_metrics
from notifier import send_bot_online_notification, send_trading_complete_notification, send_bot_offline_notification
import json 



from datetime import time as dt_time

def reload_config():
    """Dynamically reload configuration from config.py"""
    try:
        importlib.reload(config)
        config_data = config.CONFIG
        
        # Validate required config fields
        required_fields = [
            "min_score_for_trade", "lot_size", "delay_seconds",
            "partial_close_trigger_percent", "full_close_trigger_percent",
            "allowed_trading_window"
        ]
        
        missing_fields = [field for field in required_fields if field not in config_data]
        if missing_fields:
            print(f"⚠️ Missing required config fields: {missing_fields}")
            print("⚠️ Using default values where possible")
        
        return config_data
    except Exception as e:
        print(f"⚠️ Failed to reload config: {e}")
        return config.CONFIG


# === Settings ===
SYMBOLS = sys.argv[1:]
if not SYMBOLS:
    print("❌ Please provide at least one symbol, e.g. `python bot_runner.py EURUSD`")
    sys.exit(1)

TIMEFRAME = mt5.TIMEFRAME_M15
def get_current_config():
    """Get current configuration (reloaded each time)"""
    return reload_config()

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

def log_ai_decision(symbol, ai_data, timestamp=None, extra_fields=None):
    """
    Append full AI decision to ai_decision_log.jsonl
    including technical + override metadata if available.
    """
    entry = {
        "timestamp": timestamp or datetime.now().isoformat(),
        "symbol": symbol,
        "ai_decision": ai_data.get("decision", "N/A"),
        "ai_confidence": ai_data.get("confidence", "N/A"),
        "ai_reasoning": ai_data.get("reasoning", ""),
        "ai_risk_note": ai_data.get("risk_note", ""),
        "technical_score": ai_data.get("technical_score", "N/A"),
        "ema_trend": ai_data.get("ema_trend", "N/A"),
        "final_direction": ai_data.get("final_direction", "HOLD"),
        "executed": ai_data.get("executed", False),
        "ai_override": ai_data.get("ai_override", False),
        "override_reason": ai_data.get("override_reason", ""),
        "execution_source": ai_data.get("execution_source", "N/A")
    }

    if extra_fields:
        entry.update(extra_fields)

    try:
        with open("ai_decision_log.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"✅ AI decision logged for {symbol}")
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
    # Initialize MT5 directly first
    try:
        initialize_mt5()
        print("✅ MT5 initialized")
    except Exception as e:
        print(f"❌ Failed to initialize MT5: {e}")
        return
    
    # Verify connection with error handling
    if not safe_mt5_operation(lambda: mt5.terminal_info() and mt5.version()):
        print("❌ MT5 connection verification failed")
        return
    
    # Send bot online notification
    try:
        send_bot_online_notification()
        print("📤 Bot online notification sent to Telegram")
    except Exception as e:
        print(f"⚠️ Failed to send online notification: {e}")
    
    trade_counter = {}
    loop_count = 0
    print("✅ Bot started with enhanced error handling and performance monitoring")
    
    # Initialize heartbeat
    try:
        with open("bot_heartbeat.json", "w") as f:
            initial_heartbeat = {
                "last_heartbeat": datetime.now().isoformat(),
                "bot_status": "starting",
                "current_symbols": SYMBOLS,
                "loop_count": 0,
                "last_analysis": datetime.now().isoformat(),
                "mt5_connected": True,
                "news_protection_active": False
            }
            json.dump(initial_heartbeat, f)
    except Exception as e:
        print(f"⚠️ Failed to initialize heartbeat: {e}")

    try:
        while True:
            # Reload configuration at the start of each loop
            current_config = get_current_config()
            DELAY_SECONDS = current_config.get("delay_seconds", 60 * 15)
            
            # Enhanced connection check with error handling
            if not safe_mt5_operation(lambda: mt5.terminal_info() and mt5.version()):
                print("⚠️ MT5 appears disconnected. Reinitializing with error handling...")
                shutdown_mt5()
                time.sleep(2)
                if not safe_mt5_operation(initialize_mt5):
                    print("❌ Failed to reinitialize MT5")
                    continue

            now = datetime.now()
            current_hour = now.hour

            for sym in trade_counter:
                trade_counter[sym] = [t for t in trade_counter[sym] if (now - t).total_seconds() < 3600]

            # Check for 4PM close trades
            close_trades_at_4pm()
            
            # Check for post-session management
            from post_session_manager import (
                check_post_session_partial_close,
                check_post_session_full_close,
                check_post_session_hard_exit,
                reset_post_session_state_if_needed
            )
            
            # Reset post-session state if needed
            reset_post_session_state_if_needed()
            
            # Check post-session profit management
            check_post_session_partial_close()
            check_post_session_full_close()
            check_post_session_hard_exit()

            for symbol in SYMBOLS:
                print(f"\n⏳ Analyzing {symbol}...")

                # Check news protection before analysis
                from news_guard import is_trade_blocked_by_news, get_high_impact_news
                news_events = get_high_impact_news()
                now = datetime.now()
                
                if is_trade_blocked_by_news(symbol, news_events, now):
                    print(f"🚫 Skipping {symbol} — news protection active")
                    # Log missed trade reason
                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "symbol": symbol,
                        "ai_decision": "BLOCKED",
                        "ai_confidence": "N/A",
                        "ai_reasoning": "News protection active",
                        "ai_risk_note": "High-impact news event detected",
                        "technical_score": 0.0,
                        "ema_trend": "N/A",
                        "final_direction": "BLOCKED",
                        "executed": False,
                        "ai_override": False,
                        "override_reason": "News protection",
                        "execution_source": "news_block"
                    }
                    with open("ai_decision_log.jsonl", "a") as f:
                        f.write(json.dumps(log_entry) + "\n")
                    continue

                check_and_lock_profits()

                if current_config.get("restrict_usd_to_am", False):
                    keywords = current_config.get("usd_related_keywords", [])
                    if any(k in symbol.upper() for k in keywords):
                        time_window = current_config.get("allowed_trading_window", {})
                        start = time_window.get("start_hour", 9)
                        end = time_window.get("end_hour", 11)
                        if not (start <= current_hour < end):
                            print(f"⏳ Skipping {symbol} — outside {start}:00–{end}:00 window for USD-related pairs.")
                            print(f"🕐 Current hour: {current_hour}, Window: {start}:00-{end}:00")
                            # Log missed trade reason
                            log_entry = {
                                "timestamp": datetime.now().isoformat(),
                                "symbol": symbol,
                                "ai_decision": "BLOCKED",
                                "ai_confidence": "N/A",
                                "ai_reasoning": f"Outside USD trading window {start}:00-{end}:00",
                                "ai_risk_note": "USD pairs restricted to morning session",
                                "technical_score": 0.0,
                                "ema_trend": "N/A",
                                "final_direction": "BLOCKED",
                                "executed": False,
                                "ai_override": False,
                                "override_reason": "USD time restriction",
                                "execution_source": "usd_time_block"
                            }
                            with open("ai_decision_log.jsonl", "a") as f:
                                f.write(json.dumps(log_entry) + "\n")
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

                # Enhanced data fetching with validation
                candles_m15 = safe_mt5_operation(get_latest_candle_data, symbol, mt5.TIMEFRAME_M15)
                candles_h1 = safe_mt5_operation(get_latest_candle_data, symbol, mt5.TIMEFRAME_H1)
                
                if candles_m15 is None or candles_h1 is None:
                    print(f"❌ Failed to fetch candle data for {symbol}")
                    continue

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

                if current_config.get("enable_pm_session_only", False) and not is_pm_session():
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
                    # Log missed trade reason
                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "symbol": symbol,
                        "ai_decision": "BLOCKED",
                        "ai_confidence": "N/A",
                        "ai_reasoning": "Risk management blocked trade",
                        "ai_risk_note": "Daily loss limit, drawdown, or cooldown active",
                        "technical_score": technical_score,
                        "ema_trend": ta_signals.get("ema_trend", "N/A"),
                        "final_direction": "BLOCKED",
                        "executed": False,
                        "ai_override": False,
                        "override_reason": "Risk guard",
                        "execution_source": "risk_block"
                    }
                    with open("ai_decision_log.jsonl", "a") as f:
                        f.write(json.dumps(log_entry) + "\n")
                    continue

                trade_counter.setdefault(symbol_key, [])
                trade_counter[symbol_key] = [t for t in trade_counter[symbol_key] if (now - t).total_seconds() < 3600]

                if len(trade_counter[symbol_key]) >= 2:
                    print(f"❌ Skipping {symbol_key}: 2-trade-per-hour limit reached.")
                    # Log missed trade reason
                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "symbol": symbol,
                        "ai_decision": "BLOCKED",
                        "ai_confidence": "N/A",
                        "ai_reasoning": "2-trade-per-hour limit reached",
                        "ai_risk_note": "Trade frequency limit exceeded",
                        "technical_score": technical_score,
                        "ema_trend": ta_signals.get("ema_trend", "N/A"),
                        "final_direction": "BLOCKED",
                        "executed": False,
                        "ai_override": False,
                        "override_reason": "Trade limit",
                        "execution_source": "frequency_block"
                    }
                    with open("ai_decision_log.jsonl", "a") as f:
                        f.write(json.dumps(log_entry) + "\n")
                    continue

                ai_data = parse_ai_sentiment(ai_sentiment)
                ema_trend = ta_signals.get("ema_trend", ta_signals.get("h1_trend", "N/A"))
                ai_direction = decision
                final_direction = ai_direction
                execution_source = "AI"
                override_reason = ""

                if technical_score >= current_config["min_score_for_trade"] and ema_trend in ["bullish", "bearish"]:
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
                        lot_sizes = {k.upper(): v for k, v in current_config.get("LOT_SIZES", {}).items()}
                        lot = lot_sizes.get(symbol_key, current_config.get("lot_size", 1.0))

                        print(f"🧶 Resolved lot size for {symbol}: {lot}")
                        print(f"🎯 Dynamic SL: {sl} | TP: {tp} | Lot: {lot}")

                        # Validate trade parameters before execution
                        if not validate_trade_parameters(symbol, lot, sl, tp):
                            print(f"❌ Trade parameters validation failed for {symbol}")
                            continue

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
            
            # Update heartbeat for GUI status monitoring (ALWAYS update, even if no trades)
            try:
                # Update both locations to ensure GUI can find it
                heartbeat_data = {
                    "last_heartbeat": datetime.now().isoformat(),
                    "bot_status": "running",
                    "current_symbols": SYMBOLS,
                    "loop_count": loop_count + 1,
                    "last_analysis": now.isoformat(),
                    "mt5_connected": bool(mt5.terminal_info()),
                    "news_protection_active": should_block_trading(),
                    "current_hour": now.hour,
                    "trading_window_active": current_config.get("restrict_usd_to_am", False)
                }
                
                # Update Bot Core location
                with open("bot_heartbeat.json", "w") as f:
                    json.dump(heartbeat_data, f)
                
                # Also update root location for GUI
                with open("../bot_heartbeat.json", "w") as f:
                    json.dump(heartbeat_data, f)
                    
                print(f"✅ Heartbeat updated at {now.strftime('%H:%M:%S')}")
            except Exception as e:
                print(f"⚠️ Failed to update heartbeat: {e}")
            
            # Generate performance report every 4 hours
            if now.hour % 4 == 0 and now.minute < 5:
                print("\n📊 Generating performance report...")
                report = performance_metrics.generate_performance_report()
                print("✅ Performance report generated")
            
            # Refresh news data daily (at midnight)
            if now.hour == 0 and now.minute < 5:
                print("\n📰 Refreshing news data from Forex Factory...")
                try:
                    from news_guard import refresh_news_data
                    if refresh_news_data():
                        print("✅ News data refreshed successfully")
                    else:
                        print("⚠️ News data refresh failed")
                except Exception as e:
                    print(f"❌ Error refreshing news data: {e}")
            
            loop_count += 1
            print(f"⏲ Waiting {DELAY_SECONDS / 60} minutes...")
            time.sleep(DELAY_SECONDS)

    except KeyboardInterrupt:
        print("🚑 Bot stopped by user.")
        # Send trading complete notification
        try:
            send_trading_complete_notification()
            print("📤 Trading complete notification sent to Telegram")
        except Exception as e:
            print(f"⚠️ Failed to send completion notification: {e}")
    except Exception as e:
        performance_monitor.log_error(f"Unhandled error: {e}", "run_bot")
        print(f"❌ Unhandled error: {e}")
        # Send offline notification for unexpected shutdown
        try:
            send_bot_offline_notification()
            print("📤 Bot offline notification sent to Telegram")
        except Exception as notify_e:
            print(f"⚠️ Failed to send offline notification: {notify_e}")
        if "not found" in str(e).lower() or "not initialized" in str(e).lower():
            print("🔁 Attempting to reinitialize MT5...")
            shutdown_mt5()
            time.sleep(2)
            if not safe_mt5_operation(initialize_mt5):
                print("❌ Failed to reinitialize MT5")
        else:
            raise
    finally:
        shutdown_mt5()

if __name__ == "__main__":
    run_bot()

