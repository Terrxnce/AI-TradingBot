# ------------------------------------------------------------------------------------
# 📊 atr_sl_tp.py – Pure ATR-Based SL/TP System
#
# This module implements a clean ATR-based SL/TP system that:
#   - Uses only ATR calculations with configurable multipliers
#   - Removes all structure-aware logic (OB, FVG, BOS, etc.)
#   - Ensures deterministic and consistent behavior
#   - Validates precision and safety requirements
#
# ✅ calculate_atr_sl_tp() – Main ATR-based SL/TP calculation
# ✅ validate_sl_tp() – Safety and precision validation
# ✅ get_symbol_pip_info() – Symbol-specific pip calculation
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import pandas as pd
import numpy as np
from ta.volatility import average_true_range
import sys
import os

# Import configuration
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
from config import CONFIG

def get_symbol_pip_info(symbol):
    """
    Get pip size and precision information for a symbol.
    
    Returns:
        dict: pip_size, digits, min_distance_pips
    """
    symbol_upper = symbol.upper() if symbol else ""
    
    # JPY pairs
    if "JPY" in symbol_upper:
        return {
            "pip_size": 0.01,
            "digits": 3,
            "min_distance_pips": 3  # Minimum 3 pips for JPY pairs
        }
    
    # Major pairs and most others
    else:
        return {
            "pip_size": 0.0001,
            "digits": 5,
            "min_distance_pips": 10  # Minimum 10 pips for major pairs
        }

def validate_sl_tp(entry_price, sl, tp, direction, symbol):
    """
    Validate SL/TP values for safety and precision.
    
    Returns:
        dict: validated_sl, validated_tp, is_valid, validation_notes
    """
    pip_info = get_symbol_pip_info(symbol)
    min_distance = pip_info["min_distance_pips"] * pip_info["pip_size"]
    digits = pip_info["digits"]
    
    validation_notes = []
    
    # Round to proper precision
    sl = round(sl, digits)
    tp = round(tp, digits)
    
    # Validate SL/TP are not null and positive
    if sl is None or sl <= 0:
        validation_notes.append("Invalid SL: null or non-positive")
        return {"is_valid": False, "validation_notes": validation_notes}
    
    if tp is None or tp <= 0:
        validation_notes.append("Invalid TP: null or non-positive")
        return {"is_valid": False, "validation_notes": validation_notes}
    
    # Validate SL/TP direction
    if direction == "BUY":
        # For BUY: SL should be below entry, TP should be above entry
        if sl >= entry_price:
            sl = entry_price - min_distance
            validation_notes.append(f"Adjusted SL for BUY (was above entry): {sl}")
        
        if tp <= entry_price:
            tp = entry_price + min_distance
            validation_notes.append(f"Adjusted TP for BUY (was below entry): {tp}")
            
    else:  # SELL
        # For SELL: SL should be above entry, TP should be below entry
        if sl <= entry_price:
            sl = entry_price + min_distance
            validation_notes.append(f"Adjusted SL for SELL (was below entry): {sl}")
        
        if tp >= entry_price:
            tp = entry_price - min_distance
            validation_notes.append(f"Adjusted TP for SELL (was above entry): {tp}")
    
    # Validate minimum distance
    sl_distance = abs(entry_price - sl)
    tp_distance = abs(entry_price - tp)
    
    if sl_distance < min_distance:
        if direction == "BUY":
            sl = entry_price - min_distance
        else:
            sl = entry_price + min_distance
        validation_notes.append(f"Adjusted SL to minimum distance: {min_distance}")
    
    if tp_distance < min_distance:
        if direction == "BUY":
            tp = entry_price + min_distance
        else:
            tp = entry_price - min_distance
        validation_notes.append(f"Adjusted TP to minimum distance: {min_distance}")
    
    # Final precision rounding
    sl = round(sl, digits)
    tp = round(tp, digits)
    
    return {
        "validated_sl": sl,
        "validated_tp": tp,
        "is_valid": True,
        "validation_notes": validation_notes
    }

def calculate_atr_sl_tp(candles_df, entry_price, direction, symbol=None):
    """
    Calculate SL and TP using pure ATR-based system.
    
    Args:
        candles_df (pd.DataFrame): OHLCV data for ATR calculation
        entry_price (float): Entry price
        direction (str): "BUY" or "SELL"
        symbol (str): Symbol name for pip calculations
    
    Returns:
        dict: SL, TP, RRR, ATR, and calculation details
    """
    
    # Get configuration multipliers
    sl_multiplier = CONFIG.get("DEFAULT_SL_MULTIPLIER", 1.5)
    tp_multiplier = CONFIG.get("DEFAULT_TP_MULTIPLIER", 2.5)
    atr_period = CONFIG.get("ATR_PERIOD", 14)
    
    # Calculate ATR
    if len(candles_df) < atr_period:
        print(f"⚠️ Insufficient data for ATR calculation (need {atr_period}, have {len(candles_df)})")
        # Use fallback fixed pip values
        pip_info = get_symbol_pip_info(symbol)
        fallback_sl_pips = 50
        fallback_tp_pips = 100
        
        sl_distance = fallback_sl_pips * pip_info["pip_size"]
        tp_distance = fallback_tp_pips * pip_info["pip_size"]
        
        if direction == "BUY":
            sl = entry_price - sl_distance
            tp = entry_price + tp_distance
        else:  # SELL
            sl = entry_price + sl_distance
            tp = entry_price - tp_distance
            
        # Validate results
        validation = validate_sl_tp(entry_price, sl, tp, direction, symbol)
        
        return {
            "sl": validation["validated_sl"],
            "tp": validation["validated_tp"],
            "atr": 0.0,
            "sl_multiplier": "fallback",
            "tp_multiplier": "fallback",
            "expected_rrr": fallback_tp_pips / fallback_sl_pips,
            "sl_from": f"Fallback ({fallback_sl_pips} pips)",
            "tp_from": f"Fallback ({fallback_tp_pips} pips)",
            "system": "atr_fallback",
            "validation_notes": validation["validation_notes"],
            "session_adjustment": "None",  # ATR system doesn't use session adjustments
            "structures_found": {"ob_count": 0, "fvg_count": 0, "bos_count": 0, "swing_count": 0}  # ATR system doesn't use structures
        }
    
    # Calculate ATR using TA library
    try:
        atr_series = average_true_range(
            high=candles_df['high'],
            low=candles_df['low'],
            close=candles_df['close'],
            window=atr_period
        )
        
        # Get the latest ATR value
        atr = atr_series.iloc[-1]
        
        if np.isnan(atr) or atr <= 0:
            raise ValueError("Invalid ATR value")
            
    except Exception as e:
        print(f"⚠️ ATR calculation failed: {e}")
        # Use fallback approach
        high_low_range = candles_df['high'] - candles_df['low']
        atr = high_low_range.tail(atr_period).mean()
        
        if np.isnan(atr) or atr <= 0:
            pip_info = get_symbol_pip_info(symbol)
            atr = 20 * pip_info["pip_size"]  # 20 pip fallback
    
    # Calculate SL and TP distances
    sl_distance = atr * sl_multiplier
    tp_distance = atr * tp_multiplier
    
    # Calculate SL and TP prices
    if direction == "BUY":
        sl = entry_price - sl_distance
        tp = entry_price + tp_distance
    else:  # SELL
        sl = entry_price + sl_distance
        tp = entry_price - tp_distance
    
    # Validate and adjust if necessary
    validation = validate_sl_tp(entry_price, sl, tp, direction, symbol)
    
    if not validation["is_valid"]:
        print("❌ SL/TP validation failed")
        return None
    
    # Calculate final RRR
    final_sl_distance = abs(entry_price - validation["validated_sl"])
    final_tp_distance = abs(entry_price - validation["validated_tp"])
    expected_rrr = final_tp_distance / final_sl_distance if final_sl_distance > 0 else 0
    
    return {
        "sl": validation["validated_sl"],
        "tp": validation["validated_tp"],
        "atr": round(atr, 5),
        "sl_multiplier": sl_multiplier,
        "tp_multiplier": tp_multiplier,
        "expected_rrr": round(expected_rrr, 3),
        "sl_from": f"ATR × {sl_multiplier}",
        "tp_from": f"ATR × {tp_multiplier}",
        "system": "pure_atr",
        "validation_notes": validation["validation_notes"],
        "sl_distance_pips": round(final_sl_distance / get_symbol_pip_info(symbol)["pip_size"], 1),
        "tp_distance_pips": round(final_tp_distance / get_symbol_pip_info(symbol)["pip_size"], 1),
        "session_adjustment": "None",  # ATR system doesn't use session adjustments
        "structures_found": {"ob_count": 0, "fvg_count": 0, "bos_count": 0, "swing_count": 0}  # ATR system doesn't use structures
    }

# Test function
if __name__ == "__main__":
    # Create sample data for testing
    sample_data = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=50, freq='15min'),
        'open': np.random.uniform(1.1950, 1.2050, 50),
        'high': np.random.uniform(1.1960, 1.2060, 50),
        'low': np.random.uniform(1.1940, 1.2040, 50),
        'close': np.random.uniform(1.1950, 1.2050, 50),
        'volume': np.random.randint(100, 1000, 50)
    })
    
    # Test BUY trade
    result = calculate_atr_sl_tp(
        candles_df=sample_data,
        entry_price=1.2000,
        direction="BUY",
        symbol="EURUSD"
    )
    
    print("🧪 ATR SL/TP Test Results:")
    print(f"Entry: 1.2000")
    print(f"SL: {result['sl']} ({result['sl_from']})")
    print(f"TP: {result['tp']} ({result['tp_from']})")
    print(f"ATR: {result['atr']}")
    print(f"RRR: {result['expected_rrr']}")
    print(f"SL Distance: {result['sl_distance_pips']} pips")
    print(f"TP Distance: {result['tp_distance_pips']} pips")
    print(f"Validation: {result['validation_notes']}")
