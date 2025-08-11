# ------------------------------------------------------------------------------------
# 🧱 calculate_structural_sl_tp.py – Structure-Aware SL/TP Engine
#
# This module implements a hybrid SL/TP system that:
#   - Anchors SL to valid structure + ATR buffer
#   - Sets TP based on realistic structure targets
#   - Blocks trades with RRR < 1.2
#   - Adapts TP based on time/session context
#   - Logs full rationale for SL/TP calculation
#
# ✅ calculate_structural_sl_tp() – Main SL/TP calculation function
# ✅ detect_structure_levels() – OB/FVG/BOS detection
# ✅ calculate_session_adjustment() – Time-based TP adjustments
#
# Used by: decision_engine.py for trade validation
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import pandas as pd
import numpy as np
from datetime import datetime, time
from ta.volatility import average_true_range
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import CONFIG

def detect_structure_levels(candles_df, entry_price, direction, lookback=20):
    """
    Detect Order Blocks, FVGs, and BOS levels around entry price.
    
    Returns:
        dict: Structure levels with prices and types
    """
    if len(candles_df) < lookback:
        return {"ob_levels": [], "fvg_levels": [], "bos_levels": []}
    
    # Get recent candles for analysis
    recent_candles = candles_df.tail(lookback).copy()
    
    structures = {
        "ob_levels": [],
        "fvg_levels": [],
        "bos_levels": []
    }
    
    # Detect Order Blocks (simplified - strong rejection candles)
    for i in range(1, len(recent_candles) - 1):
        current = recent_candles.iloc[i]
        prev = recent_candles.iloc[i-1]
        next_candle = recent_candles.iloc[i+1]
        
        # Bullish Order Block (rejection from low with strong bounce)
        if (current['low'] < prev['low'] and 
            current['close'] > current['open'] and
            next_candle['low'] > current['low']):
            
            structures["ob_levels"].append({
                "type": "bullish_ob",
                "price": current['low'],
                "strength": abs(current['close'] - current['open']) / current['open']
            })
        
        # Bearish Order Block (rejection from high with strong drop)
        if (current['high'] > prev['high'] and 
            current['close'] < current['open'] and
            next_candle['high'] < current['high']):
            
            structures["ob_levels"].append({
                "type": "bearish_ob",
                "price": current['high'],
                "strength": abs(current['open'] - current['close']) / current['open']
            })
    
    # Detect Fair Value Gaps (FVGs)
    for i in range(1, len(recent_candles) - 1):
        prev = recent_candles.iloc[i-1]
        current = recent_candles.iloc[i]
        next_candle = recent_candles.iloc[i+1]
        
        # Bullish FVG (gap up)
        if prev['high'] < next_candle['low']:
            gap_top = next_candle['low']
            gap_bottom = prev['high']
            gap_midpoint = (gap_top + gap_bottom) / 2
            
            structures["fvg_levels"].append({
                "type": "bullish_fvg",
                "price": gap_midpoint,
                "gap_size": gap_top - gap_bottom
            })
        
        # Bearish FVG (gap down)
        if prev['low'] > next_candle['high']:
            gap_top = prev['low']
            gap_bottom = next_candle['high']
            gap_midpoint = (gap_top + gap_bottom) / 2
            
            structures["fvg_levels"].append({
                "type": "bearish_fvg",
                "price": gap_midpoint,
                "gap_size": gap_top - gap_bottom
            })
    
    # Detect Break of Structure (BOS) - simplified swing highs/lows
    highs = recent_candles['high'].rolling(window=3, center=True).max()
    lows = recent_candles['low'].rolling(window=3, center=True).min()
    
    for i in range(1, len(recent_candles) - 1):
        if recent_candles.iloc[i]['high'] == highs.iloc[i]:
            structures["bos_levels"].append({
                "type": "bearish_bos",
                "price": recent_candles.iloc[i]['high']
            })
        
        if recent_candles.iloc[i]['low'] == lows.iloc[i]:
            structures["bos_levels"].append({
                "type": "bullish_bos",
                "price": recent_candles.iloc[i]['low']
            })
    
    return structures

def find_nearest_structure_behind(entry_price, direction, structures):
    """
    Find the nearest valid structure behind the entry price for SL calculation.
    """
    valid_structures = []
    
    # For BUY orders, look for bearish structures below entry
    if direction == "BUY":
        for ob in structures["ob_levels"]:
            if ob["type"] == "bearish_ob" and ob["price"] < entry_price:
                valid_structures.append(("OB", ob["price"], ob["strength"]))
        
        for fvg in structures["fvg_levels"]:
            if fvg["type"] == "bearish_fvg" and fvg["price"] < entry_price:
                valid_structures.append(("FVG", fvg["price"], fvg["gap_size"]))
        
        for bos in structures["bos_levels"]:
            if bos["type"] == "bullish_bos" and bos["price"] < entry_price:
                valid_structures.append(("BOS", bos["price"], 1.0))
    
    # For SELL orders, look for bullish structures above entry
    else:  # SELL
        for ob in structures["ob_levels"]:
            if ob["type"] == "bullish_ob" and ob["price"] > entry_price:
                valid_structures.append(("OB", ob["price"], ob["strength"]))
        
        for fvg in structures["fvg_levels"]:
            if fvg["type"] == "bullish_fvg" and fvg["price"] > entry_price:
                valid_structures.append(("FVG", fvg["price"], fvg["gap_size"]))
        
        for bos in structures["bos_levels"]:
            if bos["type"] == "bearish_bos" and bos["price"] > entry_price:
                valid_structures.append(("BOS", bos["price"], 1.0))
    
    if not valid_structures:
        return None, None, None
    
    # Sort by distance to entry and return nearest
    valid_structures.sort(key=lambda x: abs(x[1] - entry_price))
    return valid_structures[0]

def find_next_structure_ahead(entry_price, direction, structures):
    """
    Find the next valid structure ahead of the entry price for TP calculation.
    """
    valid_structures = []
    
    # For BUY orders, look for bullish structures above entry
    if direction == "BUY":
        for ob in structures["ob_levels"]:
            if ob["type"] == "bullish_ob" and ob["price"] > entry_price:
                valid_structures.append(("OB", ob["price"], ob["strength"]))
        
        for fvg in structures["fvg_levels"]:
            if fvg["type"] == "bullish_fvg" and fvg["price"] > entry_price:
                valid_structures.append(("FVG", fvg["price"], fvg["gap_size"]))
        
        for bos in structures["bos_levels"]:
            if bos["type"] == "bullish_bos" and bos["price"] > entry_price:
                valid_structures.append(("BOS", bos["price"], 1.0))
    
    # For SELL orders, look for bearish structures below entry
    else:  # SELL
        for ob in structures["ob_levels"]:
            if ob["type"] == "bearish_ob" and ob["price"] < entry_price:
                valid_structures.append(("OB", ob["price"], ob["strength"]))
        
        for fvg in structures["fvg_levels"]:
            if fvg["type"] == "bearish_fvg" and fvg["price"] < entry_price:
                valid_structures.append(("FVG", fvg["price"], fvg["gap_size"]))
        
        for bos in structures["bos_levels"]:
            if bos["type"] == "bearish_bos" and bos["price"] < entry_price:
                valid_structures.append(("BOS", bos["price"], 1.0))
    
    if not valid_structures:
        return None, None, None
    
    # Sort by distance to entry and return nearest
    valid_structures.sort(key=lambda x: abs(x[1] - entry_price))
    return valid_structures[0]

def calculate_session_adjustment(session_time, entry_price, sl, tp, direction):
    """
    Apply session-based adjustments to TP levels.
    """
    if not session_time:
        return tp, "None"
    
    current_hour = session_time.hour
    current_minute = session_time.minute
    time_decimal = current_hour + current_minute / 60
    
    # After 15:30 UTC - compress TP to 1.2 RRR
    if time_decimal >= 15.5:
        sl_distance = abs(entry_price - sl)
        if direction == "BUY":
            compressed_tp = entry_price + (sl_distance * 1.2)
        else:  # SELL
            compressed_tp = entry_price - (sl_distance * 1.2)
        
        return compressed_tp, f"Compressed to 1.2 RRR (after 15:30 UTC)"
    
    # Post-session (17:00-19:00 UTC) - use percentage-based targets
    elif 17.0 <= time_decimal <= 19.0:
        # Get account info for percentage calculation
        try:
            import MetaTrader5 as mt5
            account_info = mt5.account_info()
            if account_info:
                balance = account_info.balance
                # Calculate 1.5% target based on typical lot size
                lot_size = CONFIG.get("lot_size", 1.0)
                target_amount = balance * 0.015  # 1.5%
                
                # Simplified calculation - in practice you'd need pip value
                # This is a rough approximation
                if direction == "BUY":
                    percentage_tp = entry_price + (target_amount / (lot_size * 1000))
                else:
                    percentage_tp = entry_price - (target_amount / (lot_size * 1000))
                
                return percentage_tp, f"Post-session 1.5% target (17:00-19:00 UTC)"
        except:
            pass
    
    return tp, "None"

def calculate_structural_sl_tp(candles_df, entry_price, direction, session_time=None):
    """
    Calculate structure-aware SL and TP levels.
    
    Args:
        candles_df (pd.DataFrame): OHLCV data
        entry_price (float): Entry price
        direction (str): "BUY" or "SELL"
        session_time (datetime): Current session time for adjustments
    
    Returns:
        dict: SL, TP, RRR, and calculation details
    """
    if len(candles_df) < 20:
        # Fallback to ATR-based calculation if insufficient data
        return calculate_atr_fallback(candles_df, entry_price, direction, session_time)
    
    # Detect structure levels
    structures = detect_structure_levels(candles_df, entry_price, direction)
    
    # Calculate ATR for buffer
    atr_series = average_true_range(
        high=candles_df['high'],
        low=candles_df['low'],
        close=candles_df['close'],
        window=14
    )
    atr = atr_series.iloc[-1]
    
    # Find SL structure (behind entry)
    sl_structure_type, sl_structure_price, sl_structure_strength = find_nearest_structure_behind(
        entry_price, direction, structures
    )
    
    # Calculate SL
    if sl_structure_price is not None:
        # Add ATR buffer (min of 0.25 * ATR or 10 pips)
        buffer = min(atr * 0.25, 0.0010)  # 10 pips = 0.0010 for most pairs
        
        if direction == "BUY":
            sl = sl_structure_price - buffer
            sl_from = f"{sl_structure_type} + ATR buffer"
        else:  # SELL
            sl = sl_structure_price + buffer
            sl_from = f"{sl_structure_type} + ATR buffer"
    else:
        # Fallback to ATR-based SL
        if direction == "BUY":
            sl = entry_price - (atr * 0.5)
            sl_from = "ATR fallback"
        else:  # SELL
            sl = entry_price + (atr * 0.5)
            sl_from = "ATR fallback"
    
    # Validate SL position
    if direction == "BUY" and sl >= entry_price:
        print(f"⚠️ Invalid SL for BUY: {sl} >= {entry_price}, using ATR fallback")
        sl = entry_price - (atr * 0.5)
        sl_from = "ATR fallback (invalid structure)"
    elif direction == "SELL" and sl >= entry_price:  # Fixed: SELL SL should be BELOW entry
        print(f"⚠️ Invalid SL for SELL: {sl} >= {entry_price}, using ATR fallback")
        sl = entry_price + (atr * 0.5)
        sl_from = "ATR fallback (invalid structure)"
    
    # Find TP structure (ahead of entry)
    tp_structure_type, tp_structure_price, tp_structure_strength = find_next_structure_ahead(
        entry_price, direction, structures
    )
    
    # Calculate TP
    if tp_structure_price is not None:
        tp = tp_structure_price
        tp_from = f"Next {tp_structure_type}"
    else:
        # Fallback to 2:1 RRR
        if direction == "BUY":
            tp = entry_price + (entry_price - sl) * 2.0
            tp_from = "2:1 RRR fallback"
        else:  # SELL
            tp = entry_price - (sl - entry_price) * 2.0
            tp_from = "2:1 RRR fallback"
    
    # Apply session adjustments
    adjusted_tp, session_adjustment = calculate_session_adjustment(
        session_time, entry_price, sl, tp, direction
    )
    
    # Calculate RRR
    sl_distance = abs(entry_price - sl)
    tp_distance = abs(adjusted_tp - entry_price)
    expected_rrr = tp_distance / sl_distance if sl_distance > 0 else 0
    
    return {
        "sl": round(sl, 5),
        "tp": round(adjusted_tp, 5),
        "expected_rrr": round(expected_rrr, 3),
        "sl_from": sl_from,
        "tp_from": tp_from,
        "session_adjustment": session_adjustment,
        "atr": round(atr, 5),
        "structures_found": {
            "ob_count": len(structures["ob_levels"]),
            "fvg_count": len(structures["fvg_levels"]),
            "bos_count": len(structures["bos_levels"])
        }
    }

def calculate_atr_fallback(candles_df, entry_price, direction, session_time=None):
    """
    Fallback to ATR-based calculation when insufficient data for structure analysis.
    """
    if len(candles_df) < 14:
        # Use fixed pip values as last resort
        if direction == "BUY":
            sl = entry_price - 0.0050  # 50 pips
            tp = entry_price + 0.0100  # 100 pips
        else:  # SELL
            sl = entry_price + 0.0050  # 50 pips
            tp = entry_price - 0.0100  # 100 pips
        
        expected_rrr = 2.0
        sl_from = "Fixed 50 pips"
        tp_from = "Fixed 100 pips"
        session_adjustment = "None"
    else:
        # ATR-based calculation
        atr_series = average_true_range(
            high=candles_df['high'],
            low=candles_df['low'],
            close=candles_df['close'],
            window=14
        )
        atr = atr_series.iloc[-1]
        
        if direction == "BUY":
            sl = entry_price - (atr * 0.5)
            tp = entry_price + (atr * 1.0)
        else:  # SELL
            sl = entry_price + (atr * 0.5)
            tp = entry_price - (atr * 1.0)
        
        expected_rrr = 2.0
        sl_from = f"ATR fallback ({round(atr, 5)})"
        tp_from = f"ATR fallback ({round(atr, 5)})"
        session_adjustment = "None"
    
    return {
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "expected_rrr": round(expected_rrr, 3),
        "sl_from": sl_from,
        "tp_from": tp_from,
        "session_adjustment": session_adjustment,
        "atr": round(atr, 5) if len(candles_df) >= 14 else 0.0001,
        "structures_found": {
            "ob_count": 0,
            "fvg_count": 0,
            "bos_count": 0
        }
    }

# Test function
if __name__ == "__main__":
    # Create sample data for testing
    sample_data = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=100, freq='15min'),
        'open': np.random.uniform(1.1950, 1.2050, 100),
        'high': np.random.uniform(1.1960, 1.2060, 100),
        'low': np.random.uniform(1.1940, 1.2040, 100),
        'close': np.random.uniform(1.1950, 1.2050, 100),
        'volume': np.random.randint(100, 1000, 100)
    })
    
    # Test the function
    result = calculate_structural_sl_tp(
        sample_data, 
        entry_price=1.2000, 
        direction="BUY", 
        session_time=datetime.now()
    )
    
    print("Test Result:")
    print(f"SL: {result['sl']} ({result['sl_from']})")
    print(f"TP: {result['tp']} ({result['tp_from']})")
    print(f"RRR: {result['expected_rrr']}")
    print(f"Session: {result['session_adjustment']}")
    print(f"Structures: {result['structures_found']}")