# ------------------------------------------------------------------------------------
# 🧠 decision_engine.py – Trade Decision Core
#
# This module decides whether to BUY, SELL, or HOLD based on:
#   - Technical structure (BOS, FVG, OB, Rejections, etc.)
#   - EMA trend alignment
#   - LLaMA3 AI sentiment + confidence
#
# ⚡ Override logic: If TA score is 5 or 6 and trend aligns, AI is bypassed.
# 🤝 Hybrid logic: If TA score passes threshold, AI must confirm direction.
#
# Also contains dynamic SL/TP logic based on ATR + structure.
#
# ✅ evaluate_trade_decision() – Main trade decision logic
# ✅ calculate_dynamic_sl_tp() – ATR-based SL/TP calculator
# ✅ calculate_structural_sl_tp_with_validation() – NEW: Structure-aware SL/TP with RRR validation
#
# Used by: bot_runner.py for decision execution
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------


import sys
import os
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # Add parent directory for rrr_validation_repair
from config import CONFIG, USE_8PT_SCORING  # Import new scoring flag
from ta.volatility import average_true_range
import pandas as pd
import re
import json
from datetime import datetime

# Import RRR validation system
try:
    from rrr_validation_repair import validate_and_repair_rrr
except ImportError:
    print("⚠️ Could not import RRR validation system - RRR validation will be disabled")
    validate_and_repair_rrr = None

# Import new 0-8 scoring system
try:
    from scoring.score_technical_v1_8pt import score_technical_v1_8pt, TechContext, TechScoreResult
except ImportError:
    print("⚠️ Could not import 0-8 scoring system - falling back to legacy scoring")
    score_technical_v1_8pt = None
    TechContext = None
    TechScoreResult = None

def build_ai_prompt(ta_signals: dict, macro_sentiment: str = "", session_info: str = ""):
    impulse_line = ""
    if ta_signals.get("impulse_move"):
        impulse_line = f"- Recent {ta_signals['impulse_move']} impulse detected on M15\n"

    confluence_lines = ""
    if ta_signals.get("confluence_context"):
        confluence_lines = "\n".join(f"- {line}" for line in ta_signals["confluence_context"]) + "\n"

    return f"""
You are D.E.V.I, a structure-based AI trading assistant. You specialize in high-probability intraday trades on forex and indices, using technical confluence and market timing. You do not guess — if the setup isn't clear, you HOLD.

Your logic stack includes:
- OB/FVG structure alignment
- Trend confirmation via EMA (21, 50, 200)
- Rejection zones and liquidity sweeps
- Session context (Asia/London/NY)
- Optional macro sentiment (if provided)

Here is the current signal context:

[TECHNICAL STRUCTURE]
- EMA Trend: {ta_signals.get('ema_trend')}
- BOS: {ta_signals.get('bos')}
- OB Tap: {ta_signals.get('ob_tap')}
- FVG Valid: {ta_signals.get('fvg_valid')}
- Rejection: {ta_signals.get('rejection')}
- Liquidity Sweep: {ta_signals.get('liquidity_sweep')}
- Engulfing: {ta_signals.get('engulfing')}
{impulse_line}{confluence_lines}[SESSION CONTEXT]
- Current Session: {session_info}

[MACRO CONTEXT]
- Sentiment: {macro_sentiment}

Based on this full confluence, decide whether to enter a trade. Only respond in the following format:

ENTRY_DECISION: BUY / SELL / HOLD  
CONFIDENCE: [0–10]  
REASONING: [Summarize the logic]  
RISK_NOTE: [Comment on timing, structure quality, or hesitation factors]
"""


def parse_ai_response(response: str):
    try:
        parsed = {
            'decision': 'HOLD',         # safe fallback
            'confidence': 0,
            'reasoning': 'No reasoning provided.',
            'risk_note': 'No risk note provided.'
        }

        lines = response.strip().split("\n")
        for line in lines:
            if "ENTRY_DECISION:" in line.upper():
                val = line.split("ENTRY_DECISION:")[-1].strip().upper()
                if val in ["BUY", "SELL", "HOLD"]:
                    parsed['decision'] = val
            elif "CONFIDENCE:" in line.upper():
                try:
                    parsed['confidence'] = float(line.split("CONFIDENCE:")[-1].strip())
                except ValueError:
                    parsed['confidence'] = 0
            elif "REASONING:" in line.upper():
                parsed['reasoning'] = line.split("REASONING:")[-1].strip()
            elif "RISK_NOTE:" in line.upper():
                parsed['risk_note'] = line.split("RISK_NOTE:")[-1].strip()

        # Normalize confidence to 0–10 scale
        try:
            conf = float(parsed.get('confidence', 0))
        except Exception:
            conf = 0.0
        if conf > 10:
            conf = conf / 10.0
        parsed['confidence'] = max(0.0, min(10.0, conf))
        return parsed

    except Exception as e:
        print("⚠️ Failed to parse AI response:", e)
        return {
            'decision': 'HOLD',
            'confidence': 0,
            'reasoning': 'Parsing failed.',
            'risk_note': 'Error in response structure.'
        }




def evaluate_trade_decision(ta_signals, ai_response_raw):
    """
    Technicals decide direction. AI must confirm unless technical score is very strong.
    AI response must be in structured format: ENTRY_DECISION, CONFIDENCE, etc.
    """
    
    # === NEW: 0-8 Technical Scoring System ===
    if USE_8PT_SCORING and score_technical_v1_8pt is not None:
        return evaluate_trade_decision_8pt(ta_signals, ai_response_raw)
    
    # === LEGACY: Fallback to old scoring system ===
    return evaluate_trade_decision_legacy(ta_signals, ai_response_raw)


def evaluate_trade_decision_8pt(ta_signals, ai_response_raw):
    """
    NEW: 0-8 Technical Scoring System implementation
    """
    print("📊 Using 0-8 Technical Scoring System")
    
    # Get configuration - use tech_scoring as single source of truth
    tech_cfg = CONFIG.get("tech_scoring", {})
    min_score = tech_cfg.get("min_score_for_trade", 6.0)  # Default to 6.0 if not found
    post_session_threshold = tech_cfg.get("post_session_threshold", 8.0)
    pm_usd_min_score = tech_cfg.get("pm_usd_asset_min_score", 6.0)
    require_ema_alignment = tech_cfg.get("require_ema_alignment", True)
    ai_min_confidence = tech_cfg.get("ai_min_confidence", 7.0)
    ai_override_enabled = tech_cfg.get("ai_override_enabled", True)
    
    # Check if we're in post-session mode
    from session_utils import is_post_session
    from post_session_manager import is_post_session_trade_eligible
    
    is_post_session_mode = is_post_session()
    
    # Determine direction from EMA trend
    ema_trend = ta_signals.get("ema_trend", "neutral")
    if ema_trend == "bullish":
        direction = "BUY"
    elif ema_trend == "bearish":
        direction = "SELL"
    else:
        print("⚠️ No clear EMA trend direction")
        return "HOLD"
    
    # Helper function to convert direction
    def convert_direction(dir_str):
        if dir_str == "bullish":
            return "BUY"
        elif dir_str == "bearish":
            return "SELL"
        elif dir_str in ["BUY", "SELL"]:
            return dir_str
        else:
            return "NEUTRAL"
    
    # Build TechContext for scoring
    ctx = TechContext(
        dir=direction,
        session=ta_signals.get("session", "london").lower(),
        symbol=ta_signals.get("symbol", ""),
        
        # Structure signals
        bos_confirmed=ta_signals.get("bos_confirmed", False),
        bos_direction=convert_direction(ta_signals.get("bos_direction", "NEUTRAL")),
        fvg_valid=ta_signals.get("fvg_valid", False),
        fvg_filled=ta_signals.get("fvg_filled", False),
        fvg_direction=convert_direction(ta_signals.get("fvg_direction", "NEUTRAL")),
        ob_tap=ta_signals.get("ob_tap", False),
        ob_direction=convert_direction(ta_signals.get("ob_direction", "NEUTRAL")),
        rejection_at_key_level=ta_signals.get("rejection", False),
        rejection_confirmed_next=ta_signals.get("rejection_confirmed_next", False),
        rejection_direction=convert_direction(ta_signals.get("rejection_direction", "NEUTRAL")),
        sweep_recent=ta_signals.get("liquidity_sweep", False),
        sweep_reversal_confirmed=ta_signals.get("sweep_reversal_confirmed", False),
        sweep_direction=convert_direction(ta_signals.get("sweep_direction", "NEUTRAL")),
        engulfing_present=ta_signals.get("engulfing", False),
        engulfing_direction=convert_direction(ta_signals.get("engulfing_direction", "NEUTRAL")),
        
        # Trend context
        ema21=ta_signals.get("ema21", 0.0),
        ema50=ta_signals.get("ema50", 0.0),
        ema200=ta_signals.get("ema200", 0.0),
        price=ta_signals.get("price", 0.0),
        
        # HTF confirms
        ema_aligned_m15=ta_signals.get("ema_aligned_m15", False),
        ema_aligned_h1=ta_signals.get("ema_aligned_h1", False)
    )
    
    # Calculate technical score
    score_result = score_technical_v1_8pt(ctx)
    
    print(f"📊 Technical Score: {score_result.score_8pt:.1f} / 8.0")
    print(f"📊 Components: {score_result.components}")
    print(f"📊 EMA Alignment: {score_result.ema_alignment_ok}")
    print(f"📊 Technical Direction: {score_result.technical_direction}")
    
    # Determine minimum required score based on session
    session = ta_signals.get("session", "london")
    if is_post_session_mode:
        min_required = post_session_threshold
        print(f"🕐 Post-Session Mode: Required score = {min_required}")
    elif session == "pm" and any(keyword in ta_signals.get("symbol", "").upper() for keyword in CONFIG.get("usd_related_keywords", [])):
        min_required = pm_usd_min_score
        print(f"🕔 PM USD Asset: Required score = {min_required}")
    else:
        min_required = min_score
        print(f"📊 Standard Session: Required score = {min_required}")
    
    # Check EMA alignment requirement
    if require_ema_alignment and not score_result.ema_alignment_ok:
        print("⚠️ EMA alignment requirement not met")
        return "HOLD"
    
    # Post-session specific eligibility check
    if is_post_session_mode:
        symbol = ta_signals.get("symbol", "")
        ai_confidence = 0
        
        # Parse AI response to get confidence
        parsed = parse_ai_response(ai_response_raw)
        if parsed:
            try:
                ai_confidence = float(parsed.get('confidence', 0))
            except:
                ai_confidence = 0
        
        eligible, reason = is_post_session_trade_eligible(symbol, score_result.score_8pt, ai_confidence)
        if not eligible:
            print(f"🕐 Post-Session: {reason}")
            return "HOLD"
    
    # Parse AI response
    parsed = parse_ai_response(ai_response_raw)
    ai_confidence = parsed.get("confidence", 0) if parsed else 0
    ai_direction = parsed.get("decision", "HOLD") if parsed else "HOLD"
    
    # Determine final decision
    final_decision = "HOLD"
    override_used = False
    
    if score_result.score_8pt >= min_required and ai_override_enabled:
        # Technical score is high enough - override AI
        final_decision = score_result.technical_direction
        override_used = True
        print(f"⚡ Technical score {score_result.score_8pt} overrode AI - using {final_decision}")
    else:
        # Require AI confirmation
        if (ai_confidence >= ai_min_confidence and 
            ai_direction == score_result.technical_direction and 
            score_result.score_8pt >= min_required):
            final_decision = ai_direction
            print(f"🤝 AI confirmed technical direction: {final_decision}")
        else:
            print(f"⚠️ AI confidence {ai_confidence} below required {ai_min_confidence} or direction mismatch")
            final_decision = "HOLD"
    
    # Log detailed scoring information
    log_entry = {
        "tech_score_8pt": score_result.score_8pt,
        "tech_components": score_result.components,
        "ema_alignment": score_result.ema_alignment_ok,
        "session": session,
        "symbol": ta_signals.get("symbol", ""),
        "min_required_score": min_required,
        "technical_direction": score_result.technical_direction,
        "ai_dir": ai_direction,
        "ai_conf": ai_confidence,
        "override_used": override_used,
        "final_decision": final_decision
    }
    
    # Log to AI decision log
    try:
        with open("Bot Core/ai_decision_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to log scoring data: {e}")
    
    return final_decision


def evaluate_trade_decision_legacy(ta_signals, ai_response_raw):
    """
    LEGACY: Fallback to old scoring system
    """
    print("📊 Using Legacy Technical Scoring System")
    
    # Check if we're in post-session mode
    from session_utils import is_post_session
    from post_session_manager import is_post_session_trade_eligible
    
    is_post_session_mode = is_post_session()
    
    # Use tech_scoring as single source of truth for all scoring
    tech_cfg = CONFIG.get("tech_scoring", {})
    
    if is_post_session_mode:
        required_score = tech_cfg.get("post_session_threshold", 8.0)
        print(f"🕐 Post-Session Mode: Required score = {required_score}")
    else:
        required_score = tech_cfg.get("min_score_for_trade", 6.0)
    
    technical_score = 0.0

    # Enforce H1/M15 trend agreement
    # h1 = ta_signals.get("h1_trend")
    # m15 = ta_signals.get("ema_trend")
    # if h1 and m15 and h1 != m15:
    #     print(f"🔁 Skipping: H1 ({h1}) and M15 ({m15}) trend mismatch.")
    #     return "HOLD"

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

    trend = ta_signals.get("ema_trend", "")
    direction = "BUY" if trend == "bullish" else "SELL" if trend == "bearish" else None

    print(f"📊 Technical Score: {round(technical_score, 2)} / 8.0")
    print("📉 EMA Trend:", trend)

    #check if technical score meets minimum requirement
    if technical_score < required_score:
        print(f"⚠️ Technical score {technical_score}/8 is below required {required_score}, Skipping trade.")
        return "HOLD"
    
    # Post-session specific eligibility check
    if is_post_session_mode:
        symbol = ta_signals.get("symbol", "")
        ai_confidence = 0
        
        # Parse AI response to get confidence
        parsed = parse_ai_response(ai_response_raw)
        if parsed:
            try:
                ai_confidence = float(parsed.get('confidence', 0))
            except:
                ai_confidence = 0
        
        eligible, reason = is_post_session_trade_eligible(symbol, technical_score, ai_confidence)
        if not eligible:
            print(f"🕐 Post-Session: {reason}")
            return "HOLD"

    # === PM Session USD/US Asset Filter ===
    from datetime import datetime
    now = datetime.now()
    current_hour = now.hour
    pm_start = CONFIG.get("pm_session_start", 17)
    pm_end = CONFIG.get("pm_session_end", 21)
    usd_keywords = CONFIG.get("usd_related_keywords", [])
    min_pm_score = CONFIG.get("pm_usd_asset_min_score", 6)

    symbol = ta_signals.get("symbol", "").upper()

   #if pm_start <= current_hour < pm_end:
   #    if any(keyword in symbol for keyword in usd_keywords):
   #        if technical_score < min_pm_score:
   #            print(f"🕔 PM Session: {symbol} blocked – score {technical_score}/8 below minimum {min_pm_score}")
   #            return "HOLD"

    # === Override AI if technicals are very strong
    if technical_score >= required_score and direction:
        print(f"⚡ Strong technicals (score: {technical_score}) override AI.")
        return direction
    
    # === Parse structured AI response with dynamic confidence requirements
    parsed = parse_ai_response(ai_response_raw)
    if parsed:
        print(f"🧠 AI Decision: {parsed['decision']} | Confidence: {parsed['confidence']} | Reason: {parsed['reasoning']}")
        
        # Dynamic AI confidence requirements based on technical score
        if technical_score >= 7.0:
            required_ai_confidence = 6  # Lower for strong technicals
        elif technical_score >= 6.0:
            required_ai_confidence = 7  # Standard requirement
        else:
            required_ai_confidence = 8  # Higher for weak technicals
        
        print(f"📊 Required AI confidence: {required_ai_confidence} (based on technical score {technical_score})")
        
        if parsed['decision'] == direction and parsed['confidence'] >= required_ai_confidence:
            return parsed['decision']
        else:
            print(f"⚠️ AI confidence {parsed['confidence']} below required {required_ai_confidence} or direction mismatch")
            return "HOLD"
    else:
        print("❌ Could not parse AI. Defaulting to HOLD.")
        return "HOLD"
    
    # Post-session specific eligibility check
    if is_post_session_mode:
        symbol = ta_signals.get("symbol", "")
        ai_confidence = 0
        
        # Parse AI response to get confidence
        parsed = parse_ai_response(ai_response_raw)
        if parsed:
            try:
                ai_confidence = float(parsed.get('confidence', 0))
            except:
                ai_confidence = 0
        
        eligible, reason = is_post_session_trade_eligible(symbol, technical_score, ai_confidence)
        if not eligible:
            print(f"🕐 Post-Session: {reason}")
            return "HOLD"

    # === PM Session USD/US Asset Filter ===
    from datetime import datetime
    now = datetime.now()
    current_hour = now.hour
    pm_start = CONFIG.get("pm_session_start", 17)
    pm_end = CONFIG.get("pm_session_end", 21)
    usd_keywords = CONFIG.get("usd_related_keywords", [])
    min_pm_score = CONFIG.get("pm_usd_asset_min_score", 6)

    symbol = ta_signals.get("symbol", "").upper()

   #if pm_start <= current_hour < pm_end:
   #    if any(keyword in symbol for keyword in usd_keywords):
   #        if technical_score < min_pm_score:
   #            print(f"🕔 PM Session: {symbol} blocked – score {technical_score}/8 below minimum {min_pm_score}")
   #            return "HOLD"

    # === Override AI if technicals are very strong
    if technical_score >= required_score and direction:
        print(f"⚡ Strong technicals (score: {technical_score}) override AI.")
        return direction
    
    # === Parse structured AI response with dynamic confidence requirements
    parsed = parse_ai_response(ai_response_raw)
    if parsed:
        print(f"🧠 AI Decision: {parsed['decision']} | Confidence: {parsed['confidence']} | Reason: {parsed['reasoning']}")
        
        # Dynamic AI confidence requirements based on technical score
        if technical_score >= 7.0:
            required_ai_confidence = 6  # Lower for strong technicals
        elif technical_score >= 6.0:
            required_ai_confidence = 7  # Standard requirement
        else:
            required_ai_confidence = 8  # Higher for weak technicals
        
        print(f"📊 Required AI confidence: {required_ai_confidence} (based on technical score {technical_score})")
        
        if parsed['decision'] == direction and parsed['confidence'] >= required_ai_confidence:
            return parsed['decision']
        else:
            print(f"⚠️ AI confidence {parsed['confidence']} below required {required_ai_confidence} or direction mismatch")
            return "HOLD"
    else:
        print("❌ Could not parse AI. Defaulting to HOLD.")
        return "HOLD"


def build_soft_limit_override_prompt(ta_signals: dict, ai_decision: str, confidence: float, daily_loss: float):
    return f"""
You are a trading risk manager monitoring an AI forex trading bot named D.E.V.I. The bot has lost ${abs(daily_loss):,.2f} today, which is more than 50% of its allowed daily risk limit.

Here is the current technical setup:
- EMA Trend: {ta_signals.get('ema_trend')}
- Structure (BOS): {ta_signals.get('bos')}
- OB Tap: {ta_signals.get('ob_tap')}
- FVG Valid: {ta_signals.get('fvg_valid')}
- Rejection: {ta_signals.get('rejection')}
- Liquidity Sweep: {ta_signals.get('liquidity_sweep')}
- Engulfing Pattern: {ta_signals.get('engulfing')}
- Session: {ta_signals.get('session')}
- AI Decision: {ai_decision} with confidence {confidence}/10

Given this setup and drawdown, is it justified to take this next trade? Respond ONLY with:

OVERRIDE_DECISION: YES or NO  
REASON: [short explanation]
"""

def parse_override_response(response: str):
    try:
        decision_match = re.search(r'OVERRIDE_DECISION:\s*(YES|NO)', response.upper())
        reason_match = re.search(r'REASON:\s*(.+)', response, re.IGNORECASE)
        if decision_match:
            return {
                "override": decision_match.group(1).strip().upper(),
                "reason": reason_match.group(1).strip() if reason_match else "No reason provided."
            }
        return None
    except Exception as e:
        print("⚠️ Failed to parse override response:", e)
        return None

def should_override_soft_limit(ta_signals, ai_response_raw, daily_loss, call_ai_func):
    """
    If soft limit is breached, send override prompt to AI using the last decision.
    Only trade if AI says: OVERRIDE_DECISION: YES
    """
    parsed = parse_ai_response(ai_response_raw)
    if not parsed or 'decision' not in parsed:
        print("⚠️ Invalid AI response passed to soft limit override — skipping override.")
        return False  # default to conservative if AI couldn't be parsed

    prompt = build_soft_limit_override_prompt(
        ta_signals=ta_signals,
        ai_decision=parsed.get("decision"),
        confidence=parsed.get("confidence"),
        daily_loss=daily_loss
    )
    print("📤 Sending soft-limit override prompt to AI...")
    override_response = call_ai_func(prompt)

    parsed_override = parse_override_response(override_response)
    if parsed_override:
        print(f"🤖 Override Decision: {parsed_override['override']} | Reason: {parsed_override['reason']}")
        return parsed_override["override"] == "YES"
    
    print("❌ Could not parse override response. Blocking trade.")
    return False



def calculate_dynamic_sl_tp(price, direction, candles_df, rrr=2.0, window=14, buffer_multiplier=0.5):
    """
    DEPRECATED: Use calculate_structural_sl_tp() instead.
    Kept for backward compatibility.
    """
    print("⚠️ DEPRECATED: Using old ATR-based SL/TP calculation. Consider upgrading to structural SL/TP.")
    
    if len(candles_df) < window + 1:
        raise ValueError("Not enough candle data to calculate ATR.")

    atr_series = average_true_range(
        high=candles_df['high'],
        low=candles_df['low'],
        close=candles_df['close'],
        window=window
    )
    atr = atr_series.iloc[-1]
    buffer = atr * buffer_multiplier

    if direction == "BUY":
        sl = candles_df['low'].tail(10).min() - buffer
        tp = price + (price - sl) * rrr
    elif direction == "SELL":
        sl = candles_df['high'].tail(10).max() + buffer
        tp = price - (sl - price) * rrr
    else:
        raise ValueError("Invalid direction: must be 'BUY' or 'SELL'.")

    return round(sl, 5), round(tp, 5)

def calculate_structural_sl_tp_with_validation(candles_df, entry_price, direction, session_time=None, technical_score=0, symbol=None):
    """
    Calculate structure-aware SL/TP with RRR validation and logging.
    
    Returns:
        dict: SL, TP, RRR validation result, and calculation details
    """
    import json
    
    try:
                # Use structural SL/TP system with RRR validation
        from calculate_structural_sl_tp import calculate_structural_sl_tp
        
        # Calculate structural SL/TP
        result = calculate_structural_sl_tp(candles_df, entry_price, direction, session_time, symbol)
        
        # Structural validation (no hardcoded RRR filters)
        sl = result["sl"]
        tp = result["tp"]
        expected_rrr = result["expected_rrr"]
        
        # Check for invalid SL/TP conditions
        if sl == tp:
            rrr_passed = False
            result["rrr_reason"] = "SL equals TP - invalid structure"
        elif expected_rrr <= 0:
            rrr_passed = False
            result["rrr_reason"] = "Invalid RRR calculation"
        elif result["atr"] <= 0 and result.get("system") != "symbol_specific_v2":
            rrr_passed = False
            result["rrr_reason"] = "Invalid ATR value"
        else:
            # Structure-aware validation passed
            rrr_passed = True
            result["rrr_reason"] = f"Structural validation passed - RRR: {expected_rrr:.3f}"
        
        result["rrr_passed"] = rrr_passed
        
        # 🛡️ NEW: RRR Validation & Repair for legacy system
        if rrr_passed and validate_and_repair_rrr is not None:
            # Validate and repair RRR
            rrr_result = validate_and_repair_rrr(
                entry_price=entry_price,
                sl_price=result["sl"],
                tp_price=result["tp"],
                direction=direction,
                atr_value=result["atr"],
                symbol=symbol,
                structural_targets=None,  # Legacy system doesn't provide these
                structural_stops=None
            )
            
            if rrr_result is None:
                # RRR validation failed
                result["rrr_passed"] = False
                result["rrr_reason"] = "RRR validation failed - trade canceled"
                result["expected_rrr"] = 0.0
            else:
                # RRR validation passed - use repaired values
                final_sl, final_tp, final_rrr = rrr_result
                result["sl"] = final_sl
                result["tp"] = final_tp
                result["expected_rrr"] = final_rrr
                result["rrr_reason"] = f"RRR validation passed - {final_rrr:.3f}"
        elif rrr_passed and validate_and_repair_rrr is None:
            # RRR validation system not available - skip validation
            result["rrr_reason"] = f"RRR validation skipped - system not available, RRR: {expected_rrr:.3f}"
        
        mapped_result = result
        
        # Log the calculation details
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "entry": entry_price,
            "sl": result["sl"],
            "tp": result["tp"],
            "expected_rrr": result["expected_rrr"],
            "technical_score": technical_score,
            "sl_from": result["sl_from"],
            "tp_from": result["tp_from"],
            "session_adjustment": result["session_adjustment"],
            "rrr_passed": str(rrr_passed),
            "rrr_reason": result["rrr_reason"],
            "structures_found": result["structures_found"],
            "atr": result["atr"],
            "atr_multiplier": result.get("atr_multiplier", "N/A"),
            "htf_validation_score": result.get("htf_validation_score", "N/A"),
            "tp_split_enabled": result.get("tp_split", {}).get("enabled", False),
            "system": "legacy_structural"
        }
        
        # Append to AI decision log
        try:
            # Use user-specific path if available
            from shared.settings import get_current_user_paths
            user_paths = get_current_user_paths()
            if user_paths:
                log_path = user_paths["logs"] / "ai_decision_log.jsonl"
            else:
                # Fallback to local logs directory
                log_path = Path("logs") / "ai_decision_log.jsonl"
                log_path.parent.mkdir(exist_ok=True)
            
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"⚠️ Failed to log SL/TP calculation: {e}")
        
        return mapped_result
        
    except Exception as e:
        print(f"❌ Error in structural SL/TP calculation: {e}")
        
        # Emergency fallback using config values instead of ATR
        config_sl_pips = CONFIG.get("sl_pips", 50)
        config_tp_pips = CONFIG.get("tp_pips", 100)
        
        # Convert pips to price distance
        if symbol and "JPY" in symbol.upper():
            pip_size = 0.01  # JPY pairs
        else:
            pip_size = 0.0001  # Major pairs
        
        config_sl_distance = config_sl_pips * pip_size
        config_tp_distance = config_tp_pips * pip_size
        
        if direction == "BUY":
            sl = entry_price - config_sl_distance
            tp = entry_price + config_tp_distance
        else:  # SELL
            sl = entry_price + config_sl_distance
            tp = entry_price - config_tp_distance
        
        expected_rrr = config_tp_pips / config_sl_pips
        
        return {
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "expected_rrr": round(expected_rrr, 3),
            "rrr_passed": True,
            "rrr_reason": f"Emergency config fallback - RRR: {expected_rrr:.3f}",
            "sl_from": f"Emergency config fallback ({config_sl_pips} pips)",
            "tp_from": f"Emergency config fallback ({config_tp_pips} pips)",
            "session_adjustment": "None",
            "atr": 0.0001,
            "structures_found": {"ob_count": 0, "fvg_count": 0, "bos_count": 0},
            "atr_multiplier": "N/A",
            "htf_validation_score": "N/A",
            "tp_split_enabled": False,
            "system": "emergency_fallback"
        }