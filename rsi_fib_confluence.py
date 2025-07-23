# rsi_fib_confluence.py
import pandas as pd
import numpy as np

def fib_confluence(candles: pd.DataFrame, impulse_type: str, zone=(0.5, 0.618), window=30):
    """
    Checks if current price is in Fib retracement zone after an impulse.
    Returns (bool, str) → True/False, and a context description string.
    """
    if candles is None or len(candles) < window:
        return False, ""

    recent = candles.iloc[-window:]
    swing_high = recent["high"].max()
    swing_low = recent["low"].min()

    last_price = candles.iloc[-1]["close"]
    retrace_zone = (swing_low + (swing_high - swing_low) * zone[0],
                    swing_low + (swing_high - swing_low) * zone[1])

    in_zone = retrace_zone[0] <= last_price <= retrace_zone[1]

    if in_zone:
        return True, f"Price has retraced to Fib zone {zone[0]*100:.0f}–{zone[1]*100:.0f}%."
    return False, ""

def rsi_support(candles: pd.DataFrame, period=14, lower=35, upper=65):
    """
    Returns True if RSI is in neutral-to-supportive zone (not overbought/oversold),
    and a context description.
    """
    if len(candles) < period:
        return False, ""

    delta = candles["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(window=period).mean().iloc[-1]
    avg_loss = pd.Series(loss).rolling(window=period).mean().iloc[-1]
    if avg_loss == 0:
        return False, ""

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    if lower < rsi < upper:
        return True, f"RSI is at {rsi:.1f}, suggesting momentum is cooling but not extreme."
    return False, ""
