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
#
# Used by: bot_runner.py for decision execution
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------


import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
from config import CONFIG  # Optional config import
from ta.volatility import average_true_range
import pandas as pd
import re
from datetime import datetime

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
    required_score = CONFIG.get("min_score_for_trade", 6.0)
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
    
    # === Parse structured AI response
    parsed = parse_ai_response(ai_response_raw)
    if parsed:
        print(f"🧠 AI Decision: {parsed['decision']} | Confidence: {parsed['confidence']} | Reason: {parsed['reasoning']}")
        if parsed['decision'] == direction and parsed['confidence'] >= 7:
            return parsed['decision']
        else:
            print("⚠️ AI confidence too low or direction mismatch")
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
    Calculates SL and TP dynamically based on ATR and recent price structure.
    TP = price ± (price - SL) * RRR
    SL = recent swing high/low ± buffer
    """
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



# === Test block ===
if __name__ == "__main__":
    test_ta = {
        "bos": "bullish",
        "fvg_valid": True,
        "ob_tap": True,
        "rejection": True,
        "liquidity_sweep": True,
        "engulfing": True,
        "ema_trend": "bullish"
    }

    test_sentiment = """
    1. Sentiment: Bullish
    2. Confidence: Medium
    3. Rationale: EMA trend and FVG are aligned for a buy.
    """
    print("Decision:", evaluate_trade_decision(test_ta, test_sentiment))
