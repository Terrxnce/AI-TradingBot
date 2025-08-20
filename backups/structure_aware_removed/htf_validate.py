# ------------------------------------------------------------------------------------
# 🔍 htf_validate.py – Higher Timeframe Structure Validation
#
# This module implements basic HTF validation for market structures:
#   - Validates OB/FVG/BOS consistency on higher timeframe
#   - Checks HTF bias alignment with structure direction
#   - Evaluates structure age and freshness
#   - Provides simple 0..1 scoring system
#
# ✅ htf_score() – Main scoring function
# ✅ validate_structure_basic() – Structure validation wrapper
# ✅ get_htf_bias() – HTF trend bias calculation
#
# Used by: calculate_structural_sl_tp.py for structure filtering
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot
# ------------------------------------------------------------------------------------

import pandas as pd
import numpy as np

def get_htf_bias(htf_df: pd.DataFrame) -> str:
    """
    Calculate simple HTF bias using SMA20 vs current price.
    
    Args:
        htf_df (pd.DataFrame): Higher timeframe OHLCV data
    
    Returns:
        str: "bullish", "bearish", or "neutral"
    """
    if htf_df is None or len(htf_df) < 20:
        return "neutral"
    
    try:
        # Calculate SMA20
        sma20 = htf_df['close'].rolling(20).mean().iloc[-1]
        last_close = htf_df['close'].iloc[-1]
        
        # Determine bias
        if last_close > sma20 * 1.001:  # 0.1% buffer
            return "bullish"
        elif last_close < sma20 * 0.999:  # 0.1% buffer
            return "bearish"
        else:
            return "neutral"
    except:
        return "neutral"

def htf_score(structure: dict, htf_df: pd.DataFrame, current_bias: str = None) -> float:
    """
    Calculate HTF validation score for a market structure.
    
    Args:
        structure (dict): Structure dictionary with type, price, strength, age
        htf_df (pd.DataFrame): Higher timeframe OHLCV data
        current_bias (str): Current HTF bias (optional, will calculate if None)
    
    Returns:
        float: Score between 0.0 and 1.0
    """
    if htf_df is None or len(htf_df) < 50:
        return 0.6  # neutral pass if no HTF data
    
    # Extract structure information
    price = structure.get("price", 0)
    structure_type = structure.get("type", "")
    strength = structure.get("strength", 0.5)
    age = structure.get("age", 30)
    
    if price == 0:
        return 0.0
    
    # 1. HTF Proximity Score (0.4)
    # Check if structure price is within 1% range of HTF data
    price_range = price * 0.01
    near_htf = htf_df.tail(50)
    in_range = ((near_htf["low"] <= price + price_range) & 
                (near_htf["high"] >= price - price_range)).any()
    s_htf = 0.4 if in_range else 0.0
    
    # 2. HTF Bias Alignment Score (0.2)
    if current_bias is None:
        current_bias = get_htf_bias(htf_df)
    
    # Check if structure direction aligns with HTF bias
    structure_bullish = "bullish" in structure_type.lower()
    structure_bearish = "bearish" in structure_type.lower()
    
    if (structure_bullish and current_bias == "bullish") or (structure_bearish and current_bias == "bearish"):
        s_bias = 0.2
    elif current_bias == "neutral":
        s_bias = 0.1  # partial score for neutral bias
    else:
        s_bias = 0.0
    
    # 3. Age Freshness Score (0.2)
    # Optimal age: 5-50 candles, older structures get lower scores
    if 5 <= age <= 50:
        s_age = 0.2
    elif 1 <= age <= 100:
        s_age = 0.1
    else:
        s_age = 0.0
    
    # 4. Structure Strength Score (0.2)
    # Use existing strength value (0.0 to 1.0)
    s_strength = 0.2 * min(max(strength, 0.0), 1.0)
    
    # Calculate total score
    total_score = s_htf + s_bias + s_age + s_strength
    
    return total_score

def validate_structure_basic(structure: dict, htf_df: pd.DataFrame, min_score: float = 0.6) -> bool:
    """
    Basic structure validation using HTF data.
    
    Args:
        structure (dict): Structure dictionary
        htf_df (pd.DataFrame): Higher timeframe data
        min_score (float): Minimum required score (default: 0.6)
    
    Returns:
        bool: True if structure passes validation
    """
    score = htf_score(structure, htf_df)
    return score >= min_score

def add_structure_age(structures: dict, current_candle_index: int) -> dict:
    """
    Add age information to structures based on current candle position.
    
    Args:
        structures (dict): Structures dictionary
        current_candle_index (int): Current candle index
    
    Returns:
        dict: Structures with age information added
    """
    aged_structures = structures.copy()
    
    # Add age to each structure type
    for structure_type in ["ob_levels", "fvg_levels", "bos_levels"]:
        if structure_type in aged_structures:
            for structure in aged_structures[structure_type]:
                # Estimate age based on structure position (simplified)
                # In practice, you'd track when each structure was created
                structure["age"] = np.random.randint(5, 50)  # Placeholder
    
    return aged_structures

def get_htf_data(symbol: str, timeframe: str = "H1", lookback: int = 100):
    """
    Get higher timeframe data for validation.
    
    Args:
        symbol (str): Trading symbol
        timeframe (str): Higher timeframe (e.g., "H1", "H4", "D1")
        lookback (int): Number of candles to retrieve
    
    Returns:
        pd.DataFrame: HTF OHLCV data or None if unavailable
    """
    try:
        import MetaTrader5 as mt5
        
        # Convert timeframe string to MT5 timeframe
        tf_map = {
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        
        mt5_timeframe = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
        
        # Get HTF data
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, lookback)
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
        else:
            return None
            
    except Exception as e:
        print(f"⚠️ Failed to get HTF data: {e}")
        return None

# Test function
if __name__ == "__main__":
    # Create sample HTF data
    np.random.seed(42)
    sample_htf_data = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=100, freq='1H'),
        'open': np.random.uniform(1.1950, 1.2050, 100),
        'high': np.random.uniform(1.1960, 1.2060, 100),
        'low': np.random.uniform(1.1940, 1.2040, 100),
        'close': np.random.uniform(1.1950, 1.2050, 100),
        'volume': np.random.randint(100, 1000, 100)
    })
    
    # Test structures
    test_structures = [
        {
            "type": "bullish_ob",
            "price": 1.2000,
            "strength": 0.8,
            "age": 15
        },
        {
            "type": "bearish_fvg", 
            "price": 1.1980,
            "strength": 0.6,
            "age": 45
        },
        {
            "type": "bullish_bos",
            "price": 1.2020,
            "strength": 0.9,
            "age": 5
        }
    ]
    
    # Test HTF bias
    bias = get_htf_bias(sample_htf_data)
    print(f"HTF Bias: {bias}")
    
    # Test structure validation
    for i, structure in enumerate(test_structures):
        score = htf_score(structure, sample_htf_data, bias)
        valid = validate_structure_basic(structure, sample_htf_data, 0.6)
        print(f"Structure {i+1} ({structure['type']}): Score={score:.2f}, Valid={valid}")
