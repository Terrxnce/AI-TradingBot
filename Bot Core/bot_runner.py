# ------------------------------------------------------------------------------------
# 🤖 bot_runner.py — Main Trading Bot Loop (Multi-Timeframe + AI Sentiment + Dynamic SL/TP)
#
# 👨‍💻 Author: Terrence Ndifor (Terry)
# 📂 Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

# Standard library imports
import sys
import os
import time
import json
import importlib
import argparse
from datetime import datetime, timedelta, time as dt_time, timezone

# Third-party imports
import MetaTrader5 as mt5
import requests

# Local imports - add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))

# Core bot modules
from get_candles import get_latest_candle_data
from strategy_engine import analyze_structure
from decision_engine import (
    evaluate_trade_decision, 
    calculate_dynamic_sl_tp, 
    calculate_atr_sl_tp_with_validation, 
    build_ai_prompt
)
from broker_interface import initialize_mt5, shutdown_mt5, place_trade

# Configuration and utilities
import config
from shared.settings import get_user_paths
from shared.time_align import next_boundary_utc, sleep_until, now_utc

# Trading modules (updated for new profit protection system)
# from trailing_stop import apply_trailing_stop  # Replaced by profit_protection_manager
# from position_manager import close_trades_at_4pm  # Replaced by profit_protection_manager
from risk_guard import can_trade
from trade_logger import log_trade
from session_utils import detect_session
from news_guard import get_macro_sentiment, should_block_trading
# from equity_cycle_manager import check_equity_cycle, is_trades_paused  # REMOVED - replaced by profit_protection_manager

# New unified profit protection system
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from profit_protection_manager import run_protection_cycle, mark_new_trade_opened, is_drawdown_blocked, get_protection_status

# Error handling and monitoring
from error_handler import safe_mt5_operation, validate_trade_parameters, performance_monitor
from performance_metrics import performance_metrics
from notifier import (
    send_bot_online_notification, 
    send_trading_complete_notification, 
    send_bot_offline_notification
)

# Logging utilities
from shared.logging_utils import (
    get_logger, log_error, log_warning, log_success, log_info, 
    log_trade_decision, log_trade_execution
)

def reload_config():
    """Dynamically reload configuration from config.py"""
    logger = get_logger()
    
    try:
        importlib.reload(config)
        config_data = config.CONFIG
        
        # Validate required config fields (old profit management fields removed for D.E.V.I)
        required_fields = [
            "lot_size", "delay_seconds",
            "allowed_trading_window"
        ]
        
        missing_fields = [field for field in required_fields if field not in config_data]
        if missing_fields:
            log_warning(f"Missing required config fields: {missing_fields}", "config_reload", logger)
            log_warning("Using default values where possible", "config_reload", logger)
        
        return config_data
    except Exception as e:
        log_error(e, "config_reload", logger)
        return config.CONFIG


# === Settings ===
parser = argparse.ArgumentParser()
parser.add_argument("symbols", nargs="+", help="Symbols to trade, e.g. EURUSD USDJPY")
parser.add_argument("--user-id", dest="user_id", required=True)
parser.add_argument("--align", choices=["off", "quarter", "interval"], default="quarter",
                    help="off: run now; quarter: 00/15/30/45; interval: use --interval-sec")
parser.add_argument("--interval-sec", type=int, default=900, help="Interval when --align=interval")
parser.add_argument("--timeframe", default="M15", help="Timeframe hint for alignment")
args = parser.parse_args()
SYMBOLS = args.symbols
USER_ID = args.user_id
USER_PATHS = get_user_paths(USER_ID)

TIMEFRAME = mt5.TIMEFRAME_M15
def get_current_config():
    """Get current configuration (reloaded each time)"""
    return reload_config()

def is_pm_session():
    now = datetime.now().time()
    return dt_time(17, 0) <= now <= dt_time(21, 0)


def align_if_needed():
    logger = get_logger()
    
    if args.align == "off":
        return
    interval = 900 if args.align == "quarter" else max(5, args.interval_sec or 900)
    target = next_boundary_utc(interval_sec=interval, skew_sec=3)
    log_info(f"Aligning to next boundary at {target.isoformat()} (interval={interval}s)", "alignment", logger)
    sleep_until(target)


def wait_for_new_closed_bar(symbol: str, mt5_timeframe) -> bool:
    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, 3) or []
    if not rates or len(rates) < 2:
        return False
    last_closed_epoch = rates[-2]["time"]
    last_closed_dt = datetime.fromtimestamp(last_closed_epoch, tz=timezone.utc)
    return (now_utc() - last_closed_dt) < timedelta(minutes=20)

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
        "executed": str(ai_data.get("executed", False)),  # Convert bool to string
        "ai_override": str(ai_data.get("ai_override", False)),  # Convert bool to string
        "override_reason": ai_data.get("override_reason", ""),
        "execution_source": ai_data.get("execution_source", "N/A")
    }

    if extra_fields:
        # Convert any boolean values in extra_fields to strings
        for key, value in extra_fields.items():
            if isinstance(value, bool):
                extra_fields[key] = str(value)
        entry.update(extra_fields)

    try:
        with open(USER_PATHS["logs"] / "ai_decision_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        log_success(f"AI decision logged for {symbol}", "ai_logging", logger)
    except Exception as e:
        log_error(e, "ai_logging", logger)


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
    """Main bot loop with enhanced error handling and performance monitoring"""
    logger = get_logger()
    
    # Initialize MT5 directly first
    try:
        initialize_mt5()
        log_success("MT5 initialized", "bot_initialization", logger)
    except Exception as e:
        log_error(e, "bot_initialization", logger)
        return
    
    # Verify connection with error handling
    if not safe_mt5_operation(lambda: mt5.terminal_info() and mt5.version()):
        log_error(Exception("MT5 connection verification failed"), "bot_initialization", logger)
        return
    
    # Send bot online notification
    current_config = get_current_config()
    try:
        if not current_config.get("disable_telegram", True):
            send_bot_online_notification()
        print("📤 Bot online notification sent to Telegram")
    except Exception as e:
        print(f"⚠️ Failed to send online notification: {e}")
    
    trade_counter = {}
    loop_count = 0
    print("✅ Bot started with enhanced error handling and performance monitoring")
    
    # Initialize heartbeat
    try:
        with open(USER_PATHS["state"] / "bot_heartbeat.json", "w", encoding="utf-8") as f:
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
            
            # ✅ Run D.E.V.I Profit Protection Cycle (at start of loop)
            try:
                candles_data = {}  # Will collect candle data for ATR calculations
                protection_result = run_protection_cycle(None)  # First call without candles
                
                if protection_result and protection_result.get("action") == "block_trades":
                    print(f"🛡️ Trading blocked by profit protection: {protection_result.get('reason')}")
                    protection_status = get_protection_status()
                    print(f"📊 Protection Status: Equity {protection_status['floating_equity_pct']:.2f}% | "
                          f"Partial: {protection_status['partial_done']} | "
                          f"Full: {protection_status['full_done']} | "
                          f"Blocked: {protection_status['blocked_for_drawdown']}")
                    
                    # Skip trading but continue monitoring
                    # apply_trailing_stop() - now handled by protection cycle
                    time.sleep(60)  # Shorter sleep for protection monitoring
                    continue
                
            except Exception as e:
                print(f"⚠️ Protection cycle error: {e}")
            
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
            # close_trades_at_4pm() - now handled by protection cycle session reset
            
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

                # Check news protection before analysis (manual news-only mode)
                from pathlib import Path
                import json as _json
                from shared.settings import get_current_user_paths as _gcup
                def _load_manual_news_blocks():
                    paths = _gcup()
                    if not paths:
                        return []
                    f = paths["state"] / "news_blocks.json"
                    if not f.exists():
                        return []
                    try:
                        return _json.loads(f.read_text(encoding="utf-8"))
                    except Exception:
                        return []
                from news_guard import is_trade_blocked_by_news
                news_events = _load_manual_news_blocks()
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
                    with open(USER_PATHS["logs"] / "ai_decision_log.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_entry) + "\n")
                    continue

                # Check D.E.V.I equity cycle management - NOW HANDLED BY PROTECTION CYCLE
                # check_equity_cycle()  # REMOVED - replaced by profit_protection_manager
                
                # USD time restriction check
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
                            with open(USER_PATHS["logs"] / "ai_decision_log.jsonl", "a", encoding="utf-8") as f:
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
                
                # ✅ Store candle data for profit protection ATR calculations
                candles_data[symbol] = candles_m15

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

                # Calculate technical score (will be ignored if using 8-point system)
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

                # Import the enhanced diagnostic function
                from risk_guard import get_trade_block_reason
                
                can_trade_flag, block_reason, block_details = get_trade_block_reason(
                    ta_signals=ta_signals, 
                    ai_response_raw=ai_sentiment, 
                    call_ai_func=get_ai_sentiment, 
                    tech_score=technical_score
                )
                
                if not can_trade_flag:
                    print(f"⚠️ Skipped {symbol} — {block_reason}: {block_details}")
                    # Log missed trade reason
                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "symbol": symbol,
                        "ai_decision": "BLOCKED",
                        "ai_confidence": "N/A",
                        "ai_reasoning": f"Risk management blocked trade: {block_reason}",
                        "ai_risk_note": block_details,
                        "technical_score": technical_score,
                        "ema_trend": ta_signals.get("ema_trend", "N/A"),
                        "final_direction": "BLOCKED",
                        "executed": False,
                        "ai_override": False,
                        "override_reason": "Risk guard",
                        "execution_source": "risk_block"
                    }
                    with open(USER_PATHS["logs"] / "ai_decision_log.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_entry) + "\n")
                    continue

                # Check if trades are paused due to protection system
                if is_drawdown_blocked():
                    print(f"⏸️ Skipped {symbol} — trades blocked by profit protection system.")
                    # Log missed trade reason
                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "symbol": symbol,
                        "ai_decision": "PAUSED",
                        "ai_confidence": "N/A",
                        "ai_reasoning": "Trades paused due to +2% equity cycle trigger",
                        "ai_risk_note": "Daily profit target exceeded",
                        "technical_score": technical_score,
                        "ema_trend": ta_signals.get("ema_trend", "N/A"),
                        "final_direction": "PAUSED",
                        "executed": False,
                        "ai_override": False,
                        "override_reason": "Equity cycle pause",
                        "execution_source": "protection_system_pause"
                    }
                    with open(USER_PATHS["logs"] / "ai_decision_log.jsonl", "a", encoding="utf-8") as f:
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
                    with open(USER_PATHS["logs"] / "ai_decision_log.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_entry) + "\n")
                    continue

                ai_data = parse_ai_sentiment(ai_sentiment)
                ema_trend = ta_signals.get("ema_trend", ta_signals.get("h1_trend", "N/A"))
                ai_direction = decision
                final_direction = ai_direction
                execution_source = "AI"
                override_reason = ""

                # Use tech_scoring as single source of truth for score threshold
                tech_cfg = current_config.get("tech_scoring", {})
                min_score_threshold = tech_cfg.get("min_score_for_trade", 6.0)
                
                if technical_score >= min_score_threshold and ema_trend in ["bullish", "bearish"]:
                    if ai_direction == "HOLD":
                        final_direction = "BUY" if ema_trend == "bullish" else "SELL"
                        execution_source = "technical_override"
                        override_reason = f"Technical score {technical_score} overrode AI HOLD"

                success = False
                sl_tp_result = None  # Initialize for logging
                if final_direction in ["BUY", "SELL"]:
                    # Initialize variables to prevent UnboundLocalError
                    lot = None
                    sl = None
                    tp = None
                    price = None
                    sl_tp_result = None
                    
                    try:
                        if not mt5.terminal_info() or not mt5.version():
                            print("⚠️ Reinitializing MT5 before trade placement...")
                            shutdown_mt5()
                            time.sleep(2)
                            initialize_mt5()

                        price = candles_m15.iloc[-1]["close"]
                        
                        # 📊 NEW: Use pure ATR-based SL/TP system
                        print("📊 Calculating ATR-based SL/TP...")
                        sl_tp_result = calculate_atr_sl_tp_with_validation(
                            candles_df=candles_m15,
                            entry_price=price,
                            direction=final_direction,
                            session_time=datetime.now(),
                            technical_score=technical_score,
                            symbol=symbol
                        )
                        
                        # 🛡️ ATR Validation - Block trades with insufficient risk-reward
                        if not sl_tp_result["rrr_passed"]:
                            print(f"❌ Trade BLOCKED by ATR validation: {sl_tp_result['rrr_reason']}")
                            print(f"📊 Calculated RRR: {sl_tp_result['expected_rrr']:.3f}")
                            print(f"🔍 SL: ATR × {sl_tp_result.get('sl_multiplier', 'N/A')} | TP: ATR × {sl_tp_result.get('tp_multiplier', 'N/A')}")
                            continue  # Skip this trade completely
                        
                        # Extract validated SL/TP
                        sl = sl_tp_result["sl"]
                        tp = sl_tp_result["tp"]
                        
                        # Use standard config-based lot sizing (no structure-aware adaptive sizing)
                        lot_sizes = {k.upper(): v for k, v in current_config.get("lot_sizes", {}).items()}
                        lot = lot_sizes.get(symbol_key, current_config.get("default_lot_size", 0.1))
                        print(f"📊 Using config-based lot size: {lot}")

                        print(f"🧶 Resolved lot size for {symbol}: {lot}")
                        print(f"📊 ATR-based SL: {sl} ({sl_tp_result['sl_from']}) | TP: {tp} ({sl_tp_result['tp_from']})")
                        print(f"⚖️ Expected RRR: {sl_tp_result['expected_rrr']:.3f} | ATR: {sl_tp_result['atr']:.5f}")
                        # Map new structure format to display format
                        structures = sl_tp_result['structures_found']
                        ob_count = structures.get('order_blocks', 0)
                        fvg_count = structures.get('fair_value_gaps', 0)
                        bos_count = structures.get('break_structures', 0)
                        swing_count = structures.get('swing_levels', 0)
                        print(f"🏗️ Structures found: OB={ob_count}, FVG={fvg_count}, BOS={bos_count}, Swing={swing_count}")

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
                            
                            # ✅ Mark new trade for profit protection tracking
                            try:
                                mark_new_trade_opened()
                                print("📈 Trade marked for profit protection tracking")
                            except Exception as e:
                                print(f"⚠️ Failed to mark trade for protection: {e}")

                    except Exception as err:
                        print(f"❌ SL/TP or lot sizing error: {err}")
                        print(f"🔍 Error details: {type(err).__name__}: {str(err)}")
                        
                        # Use safe values for logging if variables weren't set
                        safe_lot = lot if lot is not None else 0.0
                        safe_sl = sl if sl is not None else 0.0
                        safe_tp = tp if tp is not None else 0.0
                        safe_price = price if price is not None else 0.0
                        
                        # Log the error with more details
                        error_details = {
                            "error_type": type(err).__name__,
                            "error_message": str(err),
                            "sl_tp_result": sl_tp_result if sl_tp_result else "None",
                            "symbol": symbol,
                            "direction": final_direction
                        }
                        print(f"🔍 Error details: {error_details}")
                        
                        log_trade(symbol, final_direction, safe_lot, safe_sl, safe_tp, safe_price, result=f"FAILED: {err}")

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
                    "executed": str(success),  # Convert bool to string
                    "ai_override": str(final_direction != ai_direction),  # Convert bool to string
                    "override_reason": override_reason,
                    "execution_source": execution_source,
                    # 🧱 NEW: Structure-Aware SL/TP details with broker validation
                    "sl_tp_details": {
                        "sl": sl_tp_result.get("sl"),
                        "tp": sl_tp_result.get("tp"),
                        "expected_rrr": sl_tp_result.get("expected_rrr"),
                        "rrr_passed": str(sl_tp_result.get("rrr_passed")) if sl_tp_result.get("rrr_passed") is not None else None,  # Convert bool to string
                        "rrr_reason": sl_tp_result.get("rrr_reason"),
                        "sl_from": sl_tp_result.get("sl_from"),
                        "tp_from": sl_tp_result.get("tp_from"),
                        "session_adjustment": sl_tp_result.get("session_adjustment"),
                        "structures_found": sl_tp_result.get("structures_found"),
                        "atr": sl_tp_result.get("atr"),
                        "lot_size": sl_tp_result.get("lot_size"),
                        "confidence": sl_tp_result.get("confidence"),
                        "fallback_used": sl_tp_result.get("fallback_used"),
                        "broker_validation": sl_tp_result.get("broker_validation", {"enabled": False}),
                        "sl_source": sl_tp_result.get("sl_source", "atr"),
                        "tp_source": sl_tp_result.get("tp_source", "atr"),
                        "structure_sl_type": sl_tp_result.get("structure_sl_type", "N/A"),
                        "structure_tp_type": sl_tp_result.get("structure_tp_type", "N/A"),
                        "structure_sl_level": sl_tp_result.get("structure_sl_level", "N/A"),
                        "structure_tp_level": sl_tp_result.get("structure_tp_level", "N/A"),
                        "sl_buffer_applied": sl_tp_result.get("sl_buffer_applied", "N/A"),
                        "system": sl_tp_result.get("system", "pure_atr")
                    } if sl_tp_result is not None else None
                }

                with open(USER_PATHS["logs"] / "ai_decision_log.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")

            # apply_trailing_stop(minutes=30, trail_pips=20) - now handled by protection cycle
            # Old partial close system removed - now handled by equity cycle manager
            
            # ✅ Run second protection cycle with collected candle data for ATR trailing
            try:
                if candles_data:  # If we collected any candle data
                    run_protection_cycle(candles_data)
            except Exception as e:
                print(f"⚠️ Protection cycle with candles error: {e}")
            
            # Update heartbeat for GUI status monitoring (ALWAYS update, even if no trades)
            try:
                # Update per-user heartbeat
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
                with open(USER_PATHS["state"] / "bot_heartbeat.json", "w", encoding="utf-8") as f:
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
                print("\n📰 Reloading manually updated news data...")
                try:
                    from news_guard import refresh_news_data
                    if refresh_news_data():
                        print("✅ News data reloaded successfully")
                    else:
                        print("⚠️ News data reload failed")
                except Exception as e:
                    print(f"❌ Error reloading news data: {e}")
            
            loop_count += 1
            if args.align == "off":
                print(f"⏲ Waiting {DELAY_SECONDS / 60} minutes...")
                time.sleep(DELAY_SECONDS)
            else:
                interval = 900 if args.align == "quarter" else (args.interval_sec or 900)
                next_tick = next_boundary_utc(interval_sec=interval, skew_sec=3)
                print(f"⏲ Sleeping until next boundary {next_tick.isoformat()}")
                sleep_until(next_tick)

    except KeyboardInterrupt:
        print("🚑 Bot stopped by user.")
        # Send trading complete notification
        try:
            if not current_config.get("disable_telegram", False):
                send_trading_complete_notification()
                print("📤 Trading complete notification sent to Telegram")
            else:
                print("📵 Telegram disabled — skipping completion notification")
        except Exception as e:
            print(f"⚠️ Failed to send completion notification: {e}")

    except Exception as e:
        performance_monitor.log_error(f"Unhandled error: {e}", "run_bot")
        print(f"❌ Unhandled error: {e}")
        # Send offline notification for unexpected shutdown
        try:
            if not current_config.get("disable_telegram", False):
                send_bot_offline_notification()
                print("📤 Bot offline notification sent to Telegram")
            else:
                print("📵 Telegram disabled — skipping offline notification")
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

