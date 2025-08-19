#!/usr/bin/env python3
"""
rsi_fib_confluence.py - RSI and Fibonacci Confluence Detection
Detects confluence between RSI levels and Fibonacci retracements
"""

import pandas as pd
import numpy as np

def calculate_rsi(df, period=14):
    """
    Calculate RSI indicator
    
    Args:
        df: DataFrame with OHLC data
        period: RSI period (default 14)
    
    Returns:
        Series: RSI values
    """
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_fibonacci_levels(high, low):
    """
    Calculate Fibonacci retracement levels
    
    Args:
        high: High price
        low: Low price
    
    Returns:
        dict: Fibonacci levels
    """
    diff = high - low
    return {
        "0.0": low,
        "0.236": low + 0.236 * diff,
        "0.382": low + 0.382 * diff,
        "0.5": low + 0.5 * diff,
        "0.618": low + 0.618 * diff,
        "0.786": low + 0.786 * diff,
        "1.0": high
    }

def fib_confluence(df, impulse_data=None, lookback=20):
    """
    Detect Fibonacci confluence levels
    
    Args:
        df: DataFrame with OHLC data
        impulse_data: Impulse data (ignored, for backward compatibility)
        lookback: Lookback period for swing high/low
    
    Returns:
        tuple: (bool, str) - (confluence_hit, description)
    """
    # Handle case where impulse_data is passed incorrectly
    if isinstance(impulse_data, int):
        lookback = impulse_data
    elif isinstance(lookback, dict):
        lookback = 20  # Default value if parameters are mixed up
    
    if len(df) < lookback:
        return False, "Insufficient data for Fib analysis"
    
    # Get swing high and low
    recent = df.tail(lookback)
    swing_high = recent['high'].max()
    swing_low = recent['low'].min()
    
    # Calculate Fibonacci levels
    fib_levels = calculate_fibonacci_levels(swing_high, swing_low)
    
    # Get current price
    current_price = df.iloc[-1]['close']
    
    # Find nearest Fibonacci level
    nearest_level = None
    min_distance = float('inf')
    
    for level_name, level_price in fib_levels.items():
        distance = abs(current_price - level_price)
        if distance < min_distance:
            min_distance = distance
            nearest_level = {
                "level": level_name,
                "price": level_price,
                "distance": distance
            }
    
    # Check if price is near a key Fibonacci level (within 0.1% tolerance)
    tolerance = current_price * 0.001  # 0.1% tolerance
    
    if nearest_level and nearest_level["distance"] <= tolerance:
        level_name = nearest_level["level"]
        level_price = nearest_level["price"]
        return True, f"Fib {level_name} confluence at {level_price:.2f}"
    
    return False, "No Fibonacci confluence detected"

def rsi_support(df, period=14, oversold=30, overbought=70):
    """
    Detect RSI support/resistance levels
    
    Args:
        df: DataFrame with OHLC data
        period: RSI period
        oversold: Oversold threshold
        overbought: Overbought threshold
    
    Returns:
        tuple: (bool, str) - (signal_active, description)
    """
    if len(df) < period + 1:
        return False, "Insufficient data for RSI analysis"
    
    # Calculate RSI
    rsi = calculate_rsi(df, period)
    current_rsi = rsi.iloc[-1]
    
    # Determine RSI condition
    if current_rsi < oversold:
        return True, f"RSI oversold at {current_rsi:.1f} (bullish signal)"
    elif current_rsi > overbought:
        return True, f"RSI overbought at {current_rsi:.1f} (bearish signal)"
    else:
        return False, f"RSI neutral at {current_rsi:.1f}"

