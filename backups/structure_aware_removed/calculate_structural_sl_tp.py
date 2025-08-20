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
from symbol_config import get_symbol_config, calculate_proper_sl_tp

# Import new SL/TP upgrade modules
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'Bot Core'))
    from adaptive_atr import adaptive_atr_multiplier, calculate_atr_series
    from htf_validate import validate_structure_basic, get_htf_data, add_structure_age
    from tp_split import place_split_tps, validate_tp_split_config, calc_price_at_rrr
    SLTP_UPGRADE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ SL/TP upgrade modules not available: {e}")
    SLTP_UPGRADE_AVAILABLE = False

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

def find_nearest_structure_behind(entry_price, direction, structures, symbol=None):
    """
    Find the nearest valid structure behind the entry price for SL calculation.
    """
    valid_structures = []
    
    # Get HTF data for validation if enabled
    htf_df = None
    if (SLTP_UPGRADE_AVAILABLE and 
        CONFIG["sltp_system"]["enable_htf_validation"] and 
        symbol):
        htf_timeframe = CONFIG["sltp_system"]["htf_timeframe"]
        htf_df = get_htf_data(symbol, htf_timeframe, 100)
        min_score = CONFIG["sltp_system"]["htf_min_score"]
    
    # For BUY orders, look for bearish structures below entry
    if direction == "BUY":
        for ob in structures["ob_levels"]:
            if ob["type"] == "bearish_ob" and ob["price"] < entry_price:
                # HTF validation
                if htf_df is not None:
                    if not validate_structure_basic(ob, htf_df, min_score):
                        continue
                valid_structures.append(("OB", ob["price"], ob["strength"]))
        
        for fvg in structures["fvg_levels"]:
            if fvg["type"] == "bearish_fvg" and fvg["price"] < entry_price:
                # HTF validation
                if htf_df is not None:
                    if not validate_structure_basic(fvg, htf_df, min_score):
                        continue
                valid_structures.append(("FVG", fvg["price"], fvg["gap_size"]))
        
        for bos in structures["bos_levels"]:
            if bos["type"] == "bullish_bos" and bos["price"] < entry_price:
                # HTF validation
                if htf_df is not None:
                    if not validate_structure_basic(bos, htf_df, min_score):
                        continue
                valid_structures.append(("BOS", bos["price"], 1.0))
    
    # For SELL orders, look for bullish structures above entry
    else:  # SELL
        for ob in structures["ob_levels"]:
            if ob["type"] == "bullish_ob" and ob["price"] > entry_price:
                # HTF validation
                if htf_df is not None:
                    if not validate_structure_basic(ob, htf_df, min_score):
                        continue
                valid_structures.append(("OB", ob["price"], ob["strength"]))
        
        for fvg in structures["fvg_levels"]:
            if fvg["type"] == "bullish_fvg" and fvg["price"] > entry_price:
                # HTF validation
                if htf_df is not None:
                    if not validate_structure_basic(fvg, htf_df, min_score):
                        continue
                valid_structures.append(("FVG", fvg["price"], fvg["gap_size"]))
        
        for bos in structures["bos_levels"]:
            if bos["type"] == "bearish_bos" and bos["price"] > entry_price:
                # HTF validation
                if htf_df is not None:
                    if not validate_structure_basic(bos, htf_df, min_score):
                        continue
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

def calculate_structural_sl_tp(candles_df, entry_price, direction, session_time=None, symbol=None):
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
    # Use symbol-specific configuration for proper SL/TP calculation
    if symbol:
        print(f"🧱 Calculating proper SL/TP for {symbol} using symbol-specific config")
        proper_calc = calculate_proper_sl_tp(symbol, entry_price, direction)
        
        # Get symbol config for additional info
        symbol_config = get_symbol_config(symbol)
        
        # Detect structures for validation (optional enhancement)
        structures = {"ob_levels": [], "fvg_levels": [], "bos_levels": []}
        if len(candles_df) >= 20:
            structures = detect_structure_levels(candles_df, entry_price, direction)
        
        # Calculate session adjustment (if any)
        session_adjustment = "None"
        if session_time:
            session_adjustment = calculate_session_adjustment(
                session_time, entry_price, proper_calc["sl"], proper_calc["tp"], direction
            )
        
        return {
            "sl": proper_calc["sl"],
            "tp": proper_calc["tp"],
            "expected_rrr": proper_calc["rrr"],
            "rrr_passed": proper_calc["rrr"] >= 1.5,  # Minimum 1.5:1 RRR
            "rrr_reason": f"Symbol-specific calculation: {proper_calc['rrr']}:1 RRR",
            "sl_from": f"Symbol config ({symbol_config['asset_class']})",
            "tp_from": f"Symbol config ({symbol_config['asset_class']})",
            "session_adjustment": session_adjustment,
            "atr": 0.0,  # Not used in symbol-specific calculation
            "structures_found": {
                "ob_count": len(structures["ob_levels"]),
                "fvg_count": len(structures["fvg_levels"]),
                "bos_count": len(structures["bos_levels"])
            },
            "atr_multiplier": "N/A",
            "htf_validation_score": "N/A",
            "tp_split_enabled": False,  # Disabled for D.E.V.I system
            "system": "symbol_specific_v2"
        }
    
    # Fallback for missing symbol or insufficient data
    if len(candles_df) < 20:
        print("⚠️ Insufficient data for structure analysis. Using ATR fallback.")
        return calculate_atr_fallback(candles_df, entry_price, direction, session_time)
    
    # Detect structure levels
    structures = detect_structure_levels(candles_df, entry_price, direction)
    
    # Add age information for HTF validation
    if SLTP_UPGRADE_AVAILABLE and CONFIG["sltp_system"]["enable_htf_validation"]:
        structures = add_structure_age(structures, len(candles_df) - 1)
    
    # Calculate ATR for buffer
    if SLTP_UPGRADE_AVAILABLE and CONFIG["sltp_system"]["enable_adaptive_atr"]:
        atr_series = calculate_atr_series(candles_df, 14)
        atr = atr_series.iloc[-1]
        atr_multiplier = adaptive_atr_multiplier(atr_series, CONFIG["sltp_system"]["adaptive_atr"])
    else:
        atr_series = average_true_range(
            high=candles_df['high'],
            low=candles_df['low'],
            close=candles_df['close'],
            window=14
        )
        atr = atr_series.iloc[-1]
        atr_multiplier = 1.5  # Default multiplier
    
    # Find SL structure (behind entry)
    sl_structure_type, sl_structure_price, sl_structure_strength = find_nearest_structure_behind(
        entry_price, direction, structures, symbol
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
        # 🎯 PRIORITY: Use config-based SL instead of ATR fallback
        config_sl_pips = CONFIG.get("sl_pips", 80)
        pip_size = 0.0001 if "JPY" not in symbol else 0.01
        config_sl_distance = config_sl_pips * pip_size
        
        if direction == "BUY":
            sl = entry_price - config_sl_distance
            sl_from = f"Config-based fallback ({config_sl_pips} pips)"
        else:  # SELL
            sl = entry_price + config_sl_distance
            sl_from = f"Config-based fallback ({config_sl_pips} pips)"
    
    # Validate SL position
    if direction == "BUY" and sl >= entry_price:
        print(f"⚠️ Invalid SL for BUY: {sl} >= {entry_price}, using ATR fallback")
        sl = entry_price - (atr * atr_multiplier)
        sl_from = f"ATR fallback (invalid structure, {atr_multiplier:.1f}x)"
    elif direction == "SELL" and sl <= entry_price:  # SELL SL should be ABOVE entry
        print(f"⚠️ Invalid SL for SELL: {sl} <= {entry_price}, using ATR fallback")
        sl = entry_price + (atr * atr_multiplier)
        sl_from = f"ATR fallback (invalid structure, {atr_multiplier:.1f}x)"
    
    # Find TP structure (ahead of entry)
    tp_structure_type, tp_structure_price, tp_structure_strength = find_next_structure_ahead(
        entry_price, direction, structures
    )
    
    # Calculate TP
    if tp_structure_price is not None:
        tp = tp_structure_price
        tp_from = f"Next {tp_structure_type}"
    else:
        # 🎯 PRIORITY: Use config-based TP instead of 2:1 RRR fallback
        config_tp_pips = CONFIG.get("tp_pips", 160)
        pip_size = 0.0001 if "JPY" not in symbol else 0.01
        config_tp_distance = config_tp_pips * pip_size
        
        if direction == "BUY":
            tp = entry_price + config_tp_distance
            tp_from = f"Config-based fallback ({config_tp_pips} pips)"
        else:  # SELL
            tp = entry_price - config_tp_distance
            tp_from = f"Config-based fallback ({config_tp_pips} pips)"
    
    # Apply session adjustments
    adjusted_tp, session_adjustment = calculate_session_adjustment(
        session_time, entry_price, sl, tp, direction
    )
    
    # Calculate RRR
    sl_distance = abs(entry_price - sl)
    tp_distance = abs(adjusted_tp - entry_price)
    expected_rrr = tp_distance / sl_distance if sl_distance > 0 else 0
    
    # 🎯 PRIORITY: Use config-based SL/TP if structure-based is too small
    config_sl_pips = CONFIG.get("sl_pips", 80)
    config_tp_pips = CONFIG.get("tp_pips", 160)
    
    # Convert pips to price distance
    pip_size = 0.0001 if "JPY" not in symbol else 0.01
    config_sl_distance = config_sl_pips * pip_size
    config_tp_distance = config_tp_pips * pip_size
    
    # Check if current SL/TP are too small compared to config
    if sl_distance < config_sl_distance:
        print(f"⚠️ Structure SL ({sl_distance:.5f}) smaller than config ({config_sl_distance:.5f}), using config")
        if direction == "BUY":
            sl = entry_price - config_sl_distance
        else:  # SELL
            sl = entry_price + config_sl_distance
        sl_from = f"Config-based ({config_sl_pips} pips)"
        sl_distance = config_sl_distance
    
    if tp_distance < config_tp_distance:
        print(f"⚠️ Structure TP ({tp_distance:.5f}) smaller than config ({config_tp_distance:.5f}), using config")
        if direction == "BUY":
            adjusted_tp = entry_price + config_tp_distance
        else:  # SELL
            adjusted_tp = entry_price - config_tp_distance
        tp_from = f"Config-based ({config_tp_pips} pips)"
        tp_distance = config_tp_distance
    
    # Ensure minimum SL distance (at least 15 pips for JPY pairs, 10 for others)
    min_sl_distance = 0.0015 if "JPY" in symbol else 0.0010  # 15 pips for JPY, 10 for others
    if sl_distance < min_sl_distance:
        print(f"⚠️ SL distance {sl_distance:.5f} too small, adjusting to minimum {min_sl_distance:.5f}")
        if direction == "BUY":
            sl = entry_price - min_sl_distance
        else:  # SELL
            sl = entry_price + min_sl_distance
        sl_from = f"Minimum distance ({min_sl_distance:.5f})"
        # Recalculate RRR
        sl_distance = min_sl_distance
        tp_distance = abs(adjusted_tp - entry_price)
        expected_rrr = tp_distance / sl_distance if sl_distance > 0 else 0
    
    # Prepare TP split information if enabled
    tp_split_info = None
    if (SLTP_UPGRADE_AVAILABLE and
        CONFIG["sltp_system"]["enable_tp_split"] and 
        symbol):
        tp_split_info = {
            "enabled": True,
            "tp1_price": calc_price_at_rrr(entry_price, sl, 1.0, direction == "BUY"),
            "tp2_price": calc_price_at_rrr(entry_price, sl, 2.0, direction == "BUY"),
            "tp1_ratio": 1.0,
            "tp2_ratio": 2.0,
            "tp1_size": 0.30,
            "tp2_size": 0.70
        }
    else:
        tp_split_info = {"enabled": False}
    
    return {
        "sl": round(sl, 5),
        "tp": round(adjusted_tp, 5),
        "expected_rrr": round(expected_rrr, 3),
        "sl_from": sl_from,
        "tp_from": tp_from,
        "session_adjustment": session_adjustment,
        "atr": round(atr, 5),
        "atr_multiplier": atr_multiplier,
        "structures_found": {
            "ob_count": len(structures["ob_levels"]),
            "fvg_count": len(structures["fvg_levels"]),
            "bos_count": len(structures["bos_levels"])
        },
        "tp_split": tp_split_info,
        "htf_validation_score": "N/A"  # Will be populated if HTF validation is used
    }

def calculate_atr_fallback(candles_df, entry_price, direction, session_time=None):
    """
    Fallback to config-based calculation when insufficient data for structure analysis.
    """
    # 🎯 PRIORITY: Use config values instead of ATR-based calculation
    config_sl_pips = CONFIG.get("sl_pips", 80)
    config_tp_pips = CONFIG.get("tp_pips", 160)
    
    # Convert pips to price distance (assuming major pairs)
    pip_size = 0.0001  # For major pairs like EURUSD, GBPUSD
    config_sl_distance = config_sl_pips * pip_size
    config_tp_distance = config_tp_pips * pip_size
    
    if direction == "BUY":
        sl = entry_price - config_sl_distance
        tp = entry_price + config_tp_distance
    else:  # SELL
        sl = entry_price + config_sl_distance
        tp = entry_price - config_tp_distance
    
    expected_rrr = config_tp_pips / config_sl_pips  # 160/80 = 2.0
    sl_from = f"Config fallback ({config_sl_pips} pips)"
    tp_from = f"Config fallback ({config_tp_pips} pips)"
    session_adjustment = "None"
    
    return {
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "expected_rrr": round(expected_rrr, 3),
        "sl_from": sl_from,
        "tp_from": tp_from,
        "session_adjustment": session_adjustment,
        "atr": 0.0001,  # Default ATR value for fallback
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