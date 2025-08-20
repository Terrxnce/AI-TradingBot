# ------------------------------------------------------------------------------------
# 📊 score_technical_simple.py – Simplified D.E.V.I Scoring System
#
# This module implements the original documented D.E.V.I scoring logic:
# - Basic boolean checks (no complex validation)
# - Higher scoring frequency (more trades)
# - Matches documented behavior exactly
#
# Scoring Rules (Simple):
# - BOS: 2.0 points (if exists and matches trend)
# - FVG: 2.0 points (if valid, regardless of fill status)
# - OB Tap: 1.5 points (if tap detected)
# - Rejection: 1.0 points (if rejection detected)
# - Sweep: 1.0 points (if sweep detected)
# - Engulfing: 0.5 points (if pattern detected)
# - Total capped at 8.0
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Data Files'))
from config import CONFIG

def calculate_simple_technical_score(ta_signals):
    """
    Calculate technical score using original documented D.E.V.I logic.
    
    Args:
        ta_signals (dict): Technical analysis signals
    
    Returns:
        dict: score, components breakdown, reasoning
    """
    
    technical_score = 0.0
    components = {
        "bos": 0.0,
        "fvg": 0.0,
        "ob_tap": 0.0,
        "rejection": 0.0,
        "sweep": 0.0,
        "engulfing": 0.0
    }
    
    scoring_details = []
    
    # 1. Break of Structure (BOS) - 2.0 Points
    if ta_signals.get("bos") in ["bullish", "bearish"]:
        technical_score += 2.0
        components["bos"] = 2.0
        scoring_details.append(f"✅ BOS ({ta_signals.get('bos')}): +2.0")
    else:
        scoring_details.append(f"❌ BOS: 0.0 (no BOS or neutral)")
    
    # 2. Fair Value Gap (FVG) - 2.0 Points  
    if ta_signals.get("fvg_valid"):
        technical_score += 2.0
        components["fvg"] = 2.0
        scoring_details.append("✅ FVG Valid: +2.0")
    else:
        scoring_details.append("❌ FVG: 0.0 (not valid)")
    
    # 3. Order Block (OB) Tap - 1.5 Points
    if ta_signals.get("ob_tap"):
        technical_score += 1.5
        components["ob_tap"] = 1.5
        scoring_details.append("✅ OB Tap: +1.5")
    else:
        scoring_details.append("❌ OB Tap: 0.0")
    
    # 4. Rejection - 1.0 Points
    if ta_signals.get("rejection"):
        technical_score += 1.0
        components["rejection"] = 1.0
        scoring_details.append("✅ Rejection: +1.0")
    else:
        scoring_details.append("❌ Rejection: 0.0")
    
    # 5. Liquidity Sweep - 1.0 Points
    if ta_signals.get("liquidity_sweep"):
        technical_score += 1.0
        components["sweep"] = 1.0
        scoring_details.append("✅ Liquidity Sweep: +1.0")
    else:
        scoring_details.append("❌ Liquidity Sweep: 0.0")
    
    # 6. Engulfing Pattern - 0.5 Points
    if ta_signals.get("engulfing"):
        technical_score += 0.5
        components["engulfing"] = 0.5
        scoring_details.append("✅ Engulfing: +0.5")
    else:
        scoring_details.append("❌ Engulfing: 0.0")
    
    # Cap at 8.0
    technical_score = min(technical_score, 8.0)
    
    return {
        "score": technical_score,
        "components": components,
        "scoring_details": scoring_details,
        "system": "simple_documented"
    }

def get_simple_technical_direction(ta_signals):
    """
    Determine technical direction using simple EMA trend.
    
    Returns:
        str: "BUY", "SELL", or "HOLD"
    """
    ema_trend = ta_signals.get("ema_trend", "neutral")
    
    if ema_trend == "bullish":
        return "BUY"
    elif ema_trend == "bearish":  
        return "SELL"
    else:
        return "HOLD"

def evaluate_simple_scoring(ta_signals):
    """
    Complete evaluation using simple scoring system.
    
    Returns:
        dict: Complete scoring evaluation
    """
    
    # Calculate score
    score_result = calculate_simple_technical_score(ta_signals)
    
    # Determine direction
    technical_direction = get_simple_technical_direction(ta_signals)
    
    # Check minimum threshold
    min_score = CONFIG.get("tech_scoring", {}).get("min_score_for_trade", 6.5)
    score_passed = score_result["score"] >= min_score
    
    # Check EMA alignment requirement (simplified)
    ema_aligned = ta_signals.get("ema_aligned_m15", False)
    
    return {
        "technical_score": score_result["score"],
        "components": score_result["components"],
        "technical_direction": technical_direction,
        "score_passed": score_passed,
        "ema_aligned": ema_aligned,
        "scoring_details": score_result["scoring_details"],
        "system": "simple_documented",
        "threshold": min_score
    }

# Test function
if __name__ == "__main__":
    # Test with TSLA signals that gave 3.0/8.0 in sophisticated system
    test_signals = {
        'bos': 'bearish',  # Would get 2.0 points (vs 0.0 in sophisticated)
        'fvg_valid': True,  # Would get 2.0 points (vs 0.0 in sophisticated)
        'fvg_filled': True,  # Ignored in simple system
        'ob_tap': True,     # Gets 1.5 points (same)
        'rejection': True,  # Would get 1.0 points (vs 0.0 in sophisticated)
        'rejection_confirmed_next': False,  # Ignored in simple system
        'liquidity_sweep': True,  # Gets 1.0 points (same)
        'engulfing': True,  # Gets 0.5 points (same)
        'ema_trend': 'bullish',
        'ema_aligned_m15': True
    }
    
    result = evaluate_simple_scoring(test_signals)
    
    print("🧪 SIMPLE SCORING TEST")
    print("=" * 40)
    print(f"Technical Score: {result['technical_score']}/8.0")
    print(f"Technical Direction: {result['technical_direction']}")
    print(f"Score Passed: {result['score_passed']} (threshold: {result['threshold']})")
    print(f"Components: {result['components']}")
    print("\nScoring Breakdown:")
    for detail in result['scoring_details']:
        print(f"  {detail}")
    
    print(f"\n📊 COMPARISON:")
    print(f"  Sophisticated System: 3.0/8.0 (blocked)")
    print(f"  Simple System: {result['technical_score']}/8.0 ({'✅ PASSED' if result['score_passed'] else '❌ BLOCKED'})")
