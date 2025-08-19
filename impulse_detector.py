#!/usr/bin/env python3
"""
impulse_detector.py - Impulse Move Detection
Detects strong directional moves in price action
"""

import pandas as pd
import numpy as np

def detect_impulsive_move(df, lookback=5, threshold=0.002):
    """
    Detect impulsive moves in price action
    
    Args:
        df: DataFrame with OHLC data
        lookback: Number of candles to look back
        threshold: Minimum move threshold (0.002 = 0.2%)
    
    Returns:
        dict: Impulse move information or None
    """
    if len(df) < lookback + 1:
        return None
    
    # Get recent candles
    recent = df.tail(lookback + 1)
    
    # Calculate price changes
    price_changes = recent['close'].pct_change().dropna()
    
    # Check for strong directional move
    if len(price_changes) >= 3:
        # Look for 3 consecutive moves in same direction
        recent_changes = price_changes.tail(3)
        
        # All positive (bullish impulse)
        if all(change > threshold for change in recent_changes):
            return {
                "type": "bullish",
                "strength": recent_changes.mean(),
                "duration": 3,
                "start_price": recent.iloc[-4]['close'],
                "end_price": recent.iloc[-1]['close']
            }
        
        # All negative (bearish impulse)
        elif all(change < -threshold for change in recent_changes):
            return {
                "type": "bearish", 
                "strength": abs(recent_changes.mean()),
                "duration": 3,
                "start_price": recent.iloc[-4]['close'],
                "end_price": recent.iloc[-1]['close']
            }
    
    return None

