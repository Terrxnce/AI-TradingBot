# ------------------------------------------------------------------------------------
# 🎯 adaptive_atr.py – Adaptive ATR Multiplier Engine
#
# This module implements percentile-based ATR multiplier calculation:
#   - Computes ATR(14) series over lookback period
#   - Determines current ATR percentile vs historical range
#   - Returns appropriate multiplier based on volatility regime
#   - Provides fallback for insufficient data
#
# ✅ adaptive_atr_multiplier() – Main multiplier calculation function
# ✅ validate_atr_data() – Data quality validation
#
# Used by: calculate_structural_sl_tp.py for dynamic SL calculation
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot
# ------------------------------------------------------------------------------------

import numpy as np
import pandas as pd
from ta.volatility import average_true_range

def validate_atr_data(atr_series: pd.Series, lookback: int) -> bool:
    """
    Validate ATR data quality for reliable percentile calculation.
    
    Args:
        atr_series (pd.Series): ATR series
        lookback (int): Required lookback period
    
    Returns:
        bool: True if data is sufficient for calculation
    """
    if atr_series is None or len(atr_series) == 0:
        return False
    
    # Remove NaN values
    clean_series = atr_series.dropna()
    
    # Check minimum data requirements
    min_required = max(30, lookback // 3)
    if len(clean_series) < min_required:
        return False
    
    # Check for sufficient variation (not all same values)
    if clean_series.std() == 0:
        return False
    
    return True

def adaptive_atr_multiplier(atr_series: pd.Series, cfg: dict) -> float:
    """
    Calculate adaptive ATR multiplier based on current volatility percentile.
    
    Args:
        atr_series (pd.Series): ATR(14) series
        cfg (dict): Configuration dictionary with adaptive_atr settings
    
    Returns:
        float: ATR multiplier (1.2, 1.5, or 1.8)
    """
    # Extract configuration parameters
    L = cfg.get("lookback", 90)
    low_p = cfg.get("low_vol_percentile", 0.3)
    high_p = cfg.get("high_vol_percentile", 0.7)
    m_low = cfg.get("mult_low", 1.2)
    m_mid = cfg.get("mult_mid", 1.5)
    m_high = cfg.get("mult_high", 1.8)
    
    # Validate data quality
    if not validate_atr_data(atr_series, L):
        print(f"⚠️ Insufficient ATR data for adaptive calculation, using default {m_mid}")
        return m_mid
    
    # Get recent ATR values
    recent = atr_series.dropna().tail(L)
    
    # Get current ATR value
    current_atr = recent.iloc[-1]
    
    # Calculate percentile rank
    rank = (recent.values <= current_atr).sum() / len(recent)
    
    # Determine multiplier based on percentile
    if rank <= low_p:
        multiplier = m_low
        regime = "LOW"
    elif rank >= high_p:
        multiplier = m_high
        regime = "HIGH"
    else:
        multiplier = m_mid
        regime = "MID"
    
    print(f"🎯 Adaptive ATR: {current_atr:.5f} (percentile: {rank:.2f}) → {regime} volatility → {multiplier}x multiplier")
    
    return multiplier

def calculate_atr_series(candles_df: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    Calculate ATR series from OHLCV data.
    
    Args:
        candles_df (pd.DataFrame): OHLCV data
        window (int): ATR window (default: 14)
    
    Returns:
        pd.Series: ATR series
    """
    if len(candles_df) < window + 1:
        return pd.Series()
    
    atr_series = average_true_range(
        high=candles_df['high'],
        low=candles_df['low'],
        close=candles_df['close'],
        window=window
    )
    
    return atr_series

# Test function
if __name__ == "__main__":
    # Create sample data for testing
    np.random.seed(42)
    sample_data = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=100, freq='15min'),
        'open': np.random.uniform(1.1950, 1.2050, 100),
        'high': np.random.uniform(1.1960, 1.2060, 100),
        'low': np.random.uniform(1.1940, 1.2040, 100),
        'close': np.random.uniform(1.1950, 1.2050, 100),
        'volume': np.random.randint(100, 1000, 100)
    })
    
    # Test configuration
    test_cfg = {
        "lookback": 90,
        "low_vol_percentile": 0.3,
        "high_vol_percentile": 0.7,
        "mult_low": 1.2,
        "mult_mid": 1.5,
        "mult_high": 1.8
    }
    
    # Calculate ATR series
    atr_series = calculate_atr_series(sample_data)
    
    # Test adaptive multiplier
    multiplier = adaptive_atr_multiplier(atr_series, test_cfg)
    
    print(f"\nTest Result: ATR Multiplier = {multiplier}")
    print(f"Current ATR: {atr_series.iloc[-1]:.5f}")
    print(f"ATR Range: {atr_series.min():.5f} - {atr_series.max():.5f}")
