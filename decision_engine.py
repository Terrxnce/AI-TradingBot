def evaluate_trade_decision(ta_signals, ai_sentiment):
    """
    Combine technical signals and AI sentiment to produce a trade decision.

    Args:
        ta_signals (dict): Technical signals, e.g.
            {
                "bos": True,
                "fvg_valid": True,
                "ob_tap": True,
                "ema_trend": "bullish"
            }
        ai_sentiment (str): Summary or raw response from AI sentiment analysis

    Returns:
        str: One of 'BUY', 'SELL', 'HOLD'
    """
    # Rule: all key TA conditions must be aligned
    technical_score = 0

    if ta_signals.get("bos"):
        technical_score += 1
    if ta_signals.get("fvg_valid"):
        technical_score += 1
    if ta_signals.get("ob_tap"):
        technical_score += 1

    trend = ta_signals.get("ema_trend")

    # Parse AI sentiment
    ai_sentiment = ai_sentiment.lower()
    is_bullish = any(word in ai_sentiment for word in ["bullish", "rise", "increase", "hawkish"])
    is_bearish = any(word in ai_sentiment for word in ["bearish", "fall", "decline", "dovish"])

    # Decision rules
    if technical_score >= 2:
        if trend == "bullish" and is_bullish:
            return "BUY"
        elif trend == "bearish" and is_bearish:
            return "SELL"

    return "HOLD"


# Example usage
if __name__ == "__main__":
    ta = {
        "bos": True,
        "fvg_valid": True,
        "ob_tap": False,
        "ema_trend": "bullish"
    }

    ai = "CPI came in stronger than expected, suggesting bullish momentum."

    decision = evaluate_trade_decision(ta, ai)
    print("Trade Decision:", decision)
