# ------------------------------------------------------------------------------------
# 🏗️ structure_sl_tp.py – Structure-Aware SL/TP System
#
# This module implements structure-aware SL/TP using Order Blocks and Fair Value Gaps
# as primary anchors, with ATR fallback when no valid structure is found.
#
# ✅ calculate_structure_sl_tp() – Main structure-aware SL/TP calculation
# ✅ find_closest_structure() – Find nearest OB/FVG for SL
# ✅ find_next_structure() – Find next OB/FVG for TP
# ✅ validate_structure_levels() – Validate structure-based levels
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# Phase: 2 - Structure-Aware SL/TP
# ------------------------------------------------------------------------------------

import pandas as pd
import numpy as np
import sys
import os

# Import configuration and utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
from config import CONFIG, SL_TP_CONFIG
from broker_validation import enforce_broker_min_stops


def get_symbol_pip_info(symbol):
    """Get pip size and precision information for a symbol."""
    symbol_upper = symbol.upper() if symbol else ""
    
    if "JPY" in symbol_upper:
        return {"pip_size": 0.01, "digits": 3}
    else:
        return {"pip_size": 0.0001, "digits": 5}


def find_closest_structure(entry_price, direction, order_blocks, fvgs, symbol):
    """
    Find the closest structure (OB or FVG) for stop loss placement.
    
    Args:
        entry_price (float): Entry price
        direction (str): "BUY" or "SELL"
        order_blocks (list): List of order block dictionaries
        fvgs (list): List of fair value gap dictionaries
        symbol (str): Trading symbol
    
    Returns:
        dict: Closest structure info or None
    """
    pip_info = get_symbol_pip_info(symbol)
    pip_size = pip_info["pip_size"]
    buffer_pips = SL_TP_CONFIG.get("structure_sl_buffer_pips", 10)
    buffer_distance = buffer_pips * pip_size
    
    closest_structure = None
    min_distance = float('inf')
    
    # Check Order Blocks
    for ob in order_blocks:
        if direction == "BUY":
            # For BUY: SL should be below entry, use OB low
            if ob.get("low") and ob["low"] < entry_price:
                distance = entry_price - ob["low"]
                if distance < min_distance:
                    min_distance = distance
                    closest_structure = {
                        "type": "order_block",
                        "level": ob["low"],
                        "sl_price": ob["low"] - buffer_distance,
                        "distance": distance,
                        "direction": ob.get("direction", "unknown")
                    }
        else:  # SELL
            # For SELL: SL should be above entry, use OB high
            if ob.get("high") and ob["high"] > entry_price:
                distance = ob["high"] - entry_price
                if distance < min_distance:
                    min_distance = distance
                    closest_structure = {
                        "type": "order_block",
                        "level": ob["high"],
                        "sl_price": ob["high"] + buffer_distance,
                        "distance": distance,
                        "direction": ob.get("direction", "unknown")
                    }
    
    # Check Fair Value Gaps
    for fvg in fvgs:
        if direction == "BUY":
            # For BUY: SL should be below entry, use FVG low
            if fvg.get("low") and fvg["low"] < entry_price:
                distance = entry_price - fvg["low"]
                if distance < min_distance:
                    min_distance = distance
                    closest_structure = {
                        "type": "fvg",
                        "level": fvg["low"],
                        "sl_price": fvg["low"] - buffer_distance,
                        "distance": distance,
                        "direction": fvg.get("direction", "unknown")
                    }
        else:  # SELL
            # For SELL: SL should be above entry, use FVG high
            if fvg.get("high") and fvg["high"] > entry_price:
                distance = fvg["high"] - entry_price
                if distance < min_distance:
                    min_distance = distance
                    closest_structure = {
                        "type": "fvg",
                        "level": fvg["high"],
                        "sl_price": fvg["high"] + buffer_distance,
                        "distance": distance,
                        "direction": fvg.get("direction", "unknown")
                    }
    
    return closest_structure


def find_next_structure(entry_price, direction, order_blocks, fvgs, symbol):
    """
    Find the next structure (OB or FVG) for take profit placement.
    
    Args:
        entry_price (float): Entry price
        direction (str): "BUY" or "SELL"
        order_blocks (list): List of order block dictionaries
        fvgs (list): List of fair value gap dictionaries
        symbol (str): Trading symbol
    
    Returns:
        dict: Next structure info or None
    """
    next_structure = None
    min_distance = float('inf')
    
    # Check Order Blocks
    for ob in order_blocks:
        if direction == "BUY":
            # For BUY: TP should be above entry, use OB high
            if ob.get("high") and ob["high"] > entry_price:
                distance = ob["high"] - entry_price
                if distance < min_distance:
                    min_distance = distance
                    next_structure = {
                        "type": "order_block",
                        "level": ob["high"],
                        "tp_price": ob["high"],
                        "distance": distance,
                        "direction": ob.get("direction", "unknown")
                    }
        else:  # SELL
            # For SELL: TP should be below entry, use OB low
            if ob.get("low") and ob["low"] < entry_price:
                distance = entry_price - ob["low"]
                if distance < min_distance:
                    min_distance = distance
                    next_structure = {
                        "type": "order_block",
                        "level": ob["low"],
                        "tp_price": ob["low"],
                        "distance": distance,
                        "direction": ob.get("direction", "unknown")
                    }
    
    # Check Fair Value Gaps
    for fvg in fvgs:
        if direction == "BUY":
            # For BUY: TP should be above entry, use FVG high
            if fvg.get("high") and fvg["high"] > entry_price:
                distance = fvg["high"] - entry_price
                if distance < min_distance:
                    min_distance = distance
                    next_structure = {
                        "type": "fvg",
                        "level": fvg["high"],
                        "tp_price": fvg["high"],
                        "distance": distance,
                        "direction": fvg.get("direction", "unknown")
                    }
        else:  # SELL
            # For SELL: TP should be below entry, use FVG low
            if fvg.get("low") and fvg["low"] < entry_price:
                distance = entry_price - fvg["low"]
                if distance < min_distance:
                    min_distance = distance
                    next_structure = {
                        "type": "fvg",
                        "level": fvg["low"],
                        "tp_price": fvg["low"],
                        "distance": distance,
                        "direction": fvg.get("direction", "unknown")
                    }
    
    return next_structure


def validate_structure_levels(sl, tp, entry_price, direction, symbol):
    """
    Validate structure-based SL/TP levels for safety and precision.
    
    Returns:
        dict: Validation result with adjusted levels if needed
    """
    pip_info = get_symbol_pip_info(symbol)
    min_distance = 10 * pip_info["pip_size"]  # Minimum 10 pips
    digits = pip_info["digits"]
    
    validation_notes = []
    
    # Round to proper precision
    sl = round(sl, digits)
    tp = round(tp, digits)
    
    # Validate SL/TP are not null and positive
    if sl is None or sl <= 0:
        validation_notes.append("Invalid structure SL: null or non-positive")
        return {"is_valid": False, "validation_notes": validation_notes}
    
    if tp is None or tp <= 0:
        validation_notes.append("Invalid structure TP: null or non-positive")
        return {"is_valid": False, "validation_notes": validation_notes}
    
    # Validate SL/TP direction
    if direction == "BUY":
        if sl >= entry_price:
            sl = entry_price - min_distance
            validation_notes.append(f"Adjusted structure SL for BUY (was above entry): {sl}")
        
        if tp <= entry_price:
            tp = entry_price + min_distance
            validation_notes.append(f"Adjusted structure TP for BUY (was below entry): {tp}")
            
    else:  # SELL
        if sl <= entry_price:
            sl = entry_price + min_distance
            validation_notes.append(f"Adjusted structure SL for SELL (was below entry): {sl}")
        
        if tp >= entry_price:
            tp = entry_price - min_distance
            validation_notes.append(f"Adjusted structure TP for SELL (was above entry): {tp}")
    
    # Validate minimum distance
    sl_distance = abs(entry_price - sl)
    tp_distance = abs(entry_price - tp)
    
    if sl_distance < min_distance:
        if direction == "BUY":
            sl = entry_price - min_distance
        else:
            sl = entry_price + min_distance
        validation_notes.append(f"Adjusted structure SL to minimum distance: {min_distance}")
    
    if tp_distance < min_distance:
        if direction == "BUY":
            tp = entry_price + min_distance
        else:
            tp = entry_price - min_distance
        validation_notes.append(f"Adjusted structure TP to minimum distance: {min_distance}")
    
    # Final precision rounding
    sl = round(sl, digits)
    tp = round(tp, digits)
    
    return {
        "validated_sl": sl,
        "validated_tp": tp,
        "is_valid": True,
        "validation_notes": validation_notes
    }


def calculate_structure_sl_tp(entry_price, direction, analysis_result, symbol):
    """
    Calculate SL and TP using structure-aware system with ATR fallback.
    
    Args:
        entry_price (float): Entry price
        direction (str): "BUY" or "SELL"
        analysis_result (dict): Technical analysis result with structures
        symbol (str): Trading symbol
    
    Returns:
        dict: SL, TP, RRR, and calculation details
    """
    try:
        # Extract structures from analysis
        order_blocks = analysis_result.get("order_blocks", [])
        fvgs = analysis_result.get("fvg", [])
        
        # Find closest structure for SL
        closest_structure = find_closest_structure(entry_price, direction, order_blocks, fvgs, symbol)
        
        # Find next structure for TP
        next_structure = find_next_structure(entry_price, direction, order_blocks, fvgs, symbol)
        
        # Check if we have valid structures
        if closest_structure and next_structure:
            # Use structure-based SL/TP
            sl = closest_structure["sl_price"]
            tp = next_structure["tp_price"]
            
            # Validate structure levels
            validation = validate_structure_levels(sl, tp, entry_price, direction, symbol)
            
            if validation["is_valid"]:
                # Calculate RRR
                sl_distance = abs(entry_price - validation["validated_sl"])
                tp_distance = abs(entry_price - validation["validated_tp"])
                expected_rrr = tp_distance / sl_distance if sl_distance > 0 else 0
                
                # Apply broker validation
                final_sl, final_tp, broker_log = enforce_broker_min_stops(
                    validation["validated_sl"], validation["validated_tp"], entry_price, symbol
                )
                
                return {
                    "sl": final_sl,
                    "tp": final_tp,
                    "expected_rrr": round(expected_rrr, 3),
                    "sl_from": f"Structure ({closest_structure['type']})",
                    "tp_from": f"Structure ({next_structure['type']})",
                    "system": "structure_aware",
                    "sl_source": "structure",
                    "tp_source": "structure",
                    "structure_sl_type": closest_structure["type"],
                    "structure_tp_type": next_structure["type"],
                    "structure_sl_level": closest_structure["level"],
                    "structure_tp_level": next_structure["level"],
                    "sl_buffer_applied": SL_TP_CONFIG.get("structure_sl_buffer_pips", 10),
                    "fallback_used": False,
                    "broker_validation": broker_log,
                    "validation_notes": validation["validation_notes"]
                }
        
        # Fallback to ATR if no valid structures found
        print("⚠️ No valid structures found, using ATR fallback")
        return None
        
    except Exception as e:
        print(f"❌ Structure SL/TP calculation failed: {e}")
        return None


# Test function
if __name__ == "__main__":
    # Sample test data
    test_analysis = {
        "order_blocks": [
            {"low": 94.70, "high": 94.85, "direction": "bullish"},
            {"low": 94.50, "high": 94.65, "direction": "bearish"}
        ],
        "fvg": [
            {"low": 94.60, "high": 94.75, "direction": "bullish"},
            {"low": 94.40, "high": 94.55, "direction": "bearish"}
        ]
    }
    
    # Test SELL trade
    result = calculate_structure_sl_tp(
        entry_price=94.80,
        direction="SELL",
        analysis_result=test_analysis,
        symbol="AUDJPY"
    )
    
    if result:
        print("🧪 Structure SL/TP Test Results:")
        print(f"Entry: 94.80")
        print(f"SL: {result['sl']} ({result['sl_from']})")
        print(f"TP: {result['tp']} ({result['tp_from']})")
        print(f"RRR: {result['expected_rrr']}")
        print(f"SL Source: {result['sl_source']}")
        print(f"TP Source: {result['tp_source']}")
        print(f"Fallback Used: {result['fallback_used']}")
    else:
        print("❌ Structure SL/TP calculation failed")
