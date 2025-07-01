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


from config import CONFIG  # Optional config import
from ta.volatility import average_true_range
import pandas as pd
import re

def evaluate_trade_decision(ta_signals, ai_sentiment):
    """
    Technicals make the decision, AI confirms or blocks it —
    unless technicals are very strong (score 5+), then override AI.
    """
    required_score = CONFIG.get("min_score_for_trade", 3)
    technical_score = 0

    if ta_signals.get("bos") in ["bullish", "bearish"]:
        technical_score += 1
    if ta_signals.get("fvg_valid"):
        technical_score += 1
    if ta_signals.get("ob_tap"):
        technical_score += 1
    if ta_signals.get("rejection"):
        technical_score += 1
    if ta_signals.get("false_break"):
        technical_score += 1
    if ta_signals.get("engulfing"):
        technical_score += 1

    trend = ta_signals.get("ema_trend", "")

    # === Parse AI ===
    ai_sentiment = ai_sentiment.lower()
    sentiment_match = re.search(r"sentiment\s*[:\-]?\s*(bullish|bearish|neutral)", ai_sentiment)
    confidence_match = re.search(r"confidence\s*[:\-]?\s*(high|medium|low)", ai_sentiment)

    sentiment = sentiment_match.group(1) if sentiment_match else "neutral"
    confidence = confidence_match.group(1) if confidence_match else "low"

    print("📊 Technical Score:", technical_score)
    print("📉 EMA Trend:", trend)
    print(f"🧠 Sentiment: {sentiment} | Confidence: {confidence}")

    # === 1. Override AI if technicals are very strong (5 or 6)
    if technical_score >= 5 and trend in ["bullish", "bearish"]:
        print("⚡ Strong technicals override AI. Executing trade based on trend only.")
        return "BUY" if trend == "bullish" else "SELL"

    # === 2. Use AI + TA logic
    direction = None
    if technical_score >= required_score:
        if trend == "bullish":
            direction = "BUY"
        elif trend == "bearish":
            direction = "SELL"

    if direction == "BUY" and sentiment == "bullish" and confidence in ["medium", "high"]:
        return "BUY"
    elif direction == "SELL" and sentiment == "bearish" and confidence in ["medium", "high"]:
        return "SELL"

    return "HOLD"


def calculate_dynamic_sl_tp(price, direction, candles_df, rrr=2.0, window=14, buffer_multiplier=0.5):
    """
    Calculates SL and TP dynamically based on ATR and recent price structure.
    Returns: (sl_price, tp_price)
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

    recent_lows = candles_df['low'].tail(10)
    recent_highs = candles_df['high'].tail(10)

    if direction == "BUY":
        sl = recent_lows.min() - buffer
        tp = price + (price - sl) * rrr
    elif direction == "SELL":
        sl = recent_highs.max() + buffer
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
        "false_break": True,
        "engulfing": True,
        "ema_trend": "bullish"
    }

    test_sentiment = """
    1. Sentiment: Bullish
    2. Confidence: Medium
    3. Rationale: EMA trend and FVG are aligned for a buy.
    """
    print("Decision:", evaluate_trade_decision(test_ta, test_sentiment))
