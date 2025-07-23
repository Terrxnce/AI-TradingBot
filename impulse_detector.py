import pandas as pd

def detect_impulsive_move(candles: pd.DataFrame, window=10, multiplier=1.8, debug=False):
    """
    Detects recent impulsive move (bullish or bearish) based on breakout candle.

    Returns:
        "bullish" | "bearish" | None
    """
    if candles is None or len(candles) < window + 1:
        return None

    # Ensure required columns exist
    required_cols = {"high", "low", "open", "close"}
    if not required_cols.issubset(candles.columns):
        if debug:
            print(f"❌ Missing columns in candles: {required_cols - set(candles.columns)}")
        return None

    recent = candles.iloc[-1]
    prior = candles.iloc[-(window+1):-1]

    prior_ranges = prior["high"] - prior["low"]
    avg_range = prior_ranges.mean()

    current_range = recent["high"] - recent["low"]
    body = abs(recent["close"] - recent["open"])
    bullish = recent["close"] > recent["open"]
    bearish = recent["close"] < recent["open"]

    broke_above = recent["close"] > prior["high"].max()
    broke_below = recent["close"] < prior["low"].min()

    if debug:
        print(f"🧪 Impulse Check → Current Range: {current_range:.5f} | Avg Range: {avg_range:.5f}")
        print(f"Body: {body:.5f} | Broke Above: {broke_above} | Broke Below: {broke_below}")

    if current_range > multiplier * avg_range and body > 0.7 * current_range:
        if bullish and broke_above:
            if debug: print("✅ Bullish impulse detected.")
            return "bullish"
        elif bearish and broke_below:
            if debug: print("✅ Bearish impulse detected.")
            return "bearish"

    return None
