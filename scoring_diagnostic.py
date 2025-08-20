#!/usr/bin/env python3
"""
🔍 SCORING DIAGNOSTIC TEST
Analyzes why technical scores are consistently low (2-3/8)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Bot Core'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Bot Core', 'scoring'))

from config import CONFIG
from score_technical_v1_8pt import score_technical_v1_8pt, TechContext

def test_scoring_issues():
    """Test why scores are consistently low"""
    print("🔍 SCORING DIAGNOSTIC - Why Are Scores Always 2-3/8?")
    print("=" * 60)
    
    # Test case from recent TSLA logs
    ta_signals = {
        'bos': None,
        'fvg_valid': True,
        'ob_tap': True,
        'rejection': True,
        'liquidity_sweep': True,
        'engulfing': True,
        'ema_trend': 'bullish',
        'bos_confirmed': False,  # ❌ KEY ISSUE #1
        'bos_direction': 'NEUTRAL',
        'fvg_filled': True,      # ❌ KEY ISSUE #2
        'fvg_direction': 'bullish',
        'ob_direction': 'bullish',
        'rejection_confirmed_next': False,  # ❌ KEY ISSUE #3
        'rejection_direction': 'bullish',
        'sweep_reversal_confirmed': True,
        'sweep_direction': 'bullish',
        'engulfing_direction': 'bullish',
        'ema_aligned_m15': True,
        'ema_aligned_h1': False,
        'symbol': 'TSLA'
    }
    
    print("📊 Current TA Signals:")
    for key in ['bos_confirmed', 'fvg_valid', 'fvg_filled', 'ob_tap', 'rejection_confirmed_next', 'sweep_reversal_confirmed', 'engulfing']:
        print(f"   {key}: {ta_signals.get(key, 'N/A')}")
    print()
    
    # Test both BUY and SELL directions
    for direction in ["BUY", "SELL"]:
        print(f"🎯 Testing {direction} Direction:")
        
        # Convert direction
        def convert_direction(dir_str):
            if dir_str == "bullish":
                return "BUY"
            elif dir_str == "bearish":
                return "SELL"
            elif dir_str in ["BUY", "SELL"]:
                return dir_str
            else:
                return "NEUTRAL"
        
        # Build TechContext
        ctx = TechContext(
            dir=direction,
            session="newyork",
            symbol="TSLA",
            bos_confirmed=ta_signals.get("bos_confirmed", False),
            bos_direction=convert_direction(ta_signals.get("bos_direction", "NEUTRAL")),
            fvg_valid=ta_signals.get("fvg_valid", False),
            fvg_filled=ta_signals.get("fvg_filled", False),
            fvg_direction=convert_direction(ta_signals.get("fvg_direction", "NEUTRAL")),
            ob_tap=ta_signals.get("ob_tap", False),
            ob_direction=convert_direction(ta_signals.get("ob_direction", "NEUTRAL")),
            rejection_at_key_level=ta_signals.get("rejection", False),
            rejection_confirmed_next=ta_signals.get("rejection_confirmed_next", False),
            rejection_direction=convert_direction(ta_signals.get("rejection_direction", "NEUTRAL")),
            sweep_recent=ta_signals.get("liquidity_sweep", False),
            sweep_reversal_confirmed=ta_signals.get("sweep_reversal_confirmed", False),
            sweep_direction=convert_direction(ta_signals.get("sweep_direction", "NEUTRAL")),
            engulfing_present=ta_signals.get("engulfing", False),
            engulfing_direction=convert_direction(ta_signals.get("engulfing_direction", "NEUTRAL")),
            ema21=334.89,
            ema50=333.95,
            ema200=332.84,
            price=338.25,
            ema_aligned_m15=ta_signals.get("ema_aligned_m15", False),
            ema_aligned_h1=ta_signals.get("ema_aligned_h1", False)
        )
        
        # Calculate score
        result = score_technical_v1_8pt(ctx)
        
        print(f"   Direction: {direction}")
        print(f"   Total Score: {result.score_8pt}/8.0")
        print(f"   Components: {result.components}")
        print(f"   Technical Direction: {result.technical_direction}")
        print()
        
        # Analyze each component
        print("   🔍 Component Analysis:")
        components = result.components
        
        # BOS Analysis
        bos_expected = 2.0 if (ctx.bos_confirmed and ctx.bos_direction == direction) else 0.0
        print(f"   ❌ BOS: {components['bos']}/2.0 (Expected: {bos_expected})")
        if components['bos'] == 0.0:
            if not ctx.bos_confirmed:
                print(f"      ⚠️  ISSUE: BOS not confirmed")
            elif ctx.bos_direction != direction:
                print(f"      ⚠️  ISSUE: BOS direction ({ctx.bos_direction}) ≠ {direction}")
        
        # FVG Analysis  
        fvg_expected = 2.0 if (ctx.fvg_valid and not ctx.fvg_filled and ctx.fvg_direction == direction) else 0.0
        print(f"   ❌ FVG: {components['fvg']}/2.0 (Expected: {fvg_expected})")
        if components['fvg'] == 0.0:
            if not ctx.fvg_valid:
                print(f"      ⚠️  ISSUE: FVG not valid")
            elif ctx.fvg_filled:
                print(f"      ⚠️  ISSUE: FVG already filled")
            elif ctx.fvg_direction != direction:
                print(f"      ⚠️  ISSUE: FVG direction ({ctx.fvg_direction}) ≠ {direction}")
        
        # OB Tap Analysis
        ob_expected = 1.5 if (ctx.ob_tap and ctx.ob_direction == direction) else 0.0
        print(f"   ✅ OB: {components['ob_tap']}/1.5 (Expected: {ob_expected})")
        
        # Rejection Analysis
        rej_expected = 1.0 if (ctx.rejection_at_key_level and ctx.rejection_confirmed_next and ctx.rejection_direction == direction) else 0.0
        print(f"   ❌ REJ: {components['rejection']}/1.0 (Expected: {rej_expected})")
        if components['rejection'] == 0.0:
            if not ctx.rejection_confirmed_next:
                print(f"      ⚠️  ISSUE: Rejection not confirmed next candle")
        
        # Sweep Analysis
        sweep_expected = 1.0 if (ctx.sweep_recent and ctx.sweep_reversal_confirmed and ctx.sweep_direction == direction) else 0.0
        print(f"   ✅ SWEEP: {components['sweep']}/1.0 (Expected: {sweep_expected})")
        
        # Engulfing Analysis
        eng_expected = 0.5 if (ctx.engulfing_present and ctx.engulfing_direction == direction) else 0.0
        print(f"   ✅ ENG: {components['engulfing']}/0.5 (Expected: {eng_expected})")
        
        print("-" * 40)

def test_ideal_scenario():
    """Test what a high-scoring scenario would look like"""
    print("\n🎯 IDEAL HIGH-SCORING SCENARIO TEST")
    print("=" * 60)
    
    # Perfect setup
    ctx = TechContext(
        dir="BUY",
        session="newyork",
        symbol="TEST",
        bos_confirmed=True,         # ✅ 2.0 points
        bos_direction="BUY",
        fvg_valid=True,             # ✅ 2.0 points
        fvg_filled=False,           # ✅ Not filled
        fvg_direction="BUY",
        ob_tap=True,                # ✅ 1.5 points
        ob_direction="BUY",
        rejection_at_key_level=True,    # ✅ 1.0 points
        rejection_confirmed_next=True,
        rejection_direction="BUY",
        sweep_recent=True,          # ✅ 1.0 points
        sweep_reversal_confirmed=True,
        sweep_direction="BUY",
        engulfing_present=True,     # ✅ 0.5 points
        engulfing_direction="BUY",
        ema21=100.0,
        ema50=99.0,
        ema200=98.0,
        price=101.0,
        ema_aligned_m15=True,
        ema_aligned_h1=True
    )
    
    result = score_technical_v1_8pt(ctx)
    print(f"📊 Perfect Score: {result.score_8pt}/8.0")
    print(f"📊 Components: {result.components}")
    print(f"📊 Expected: 8.0 = 2.0 + 2.0 + 1.5 + 1.0 + 1.0 + 0.5")

def analyze_common_issues():
    """Analyze why scores are consistently low"""
    print("\n🚨 COMMON ISSUES CAUSING LOW SCORES")
    print("=" * 60)
    
    issues = [
        {
            "issue": "BOS Not Confirmed",
            "impact": "-2.0 points",
            "cause": "bos_confirmed = False",
            "fix": "Need confirmed break of structure"
        },
        {
            "issue": "FVG Already Filled", 
            "impact": "-2.0 points",
            "cause": "fvg_filled = True",
            "fix": "Need unfilled FVG for points"
        },
        {
            "issue": "Rejection Not Confirmed Next",
            "impact": "-1.0 points", 
            "cause": "rejection_confirmed_next = False",
            "fix": "Need next candle confirmation"
        },
        {
            "issue": "Direction Mismatch",
            "impact": "Variable",
            "cause": "Signal direction ≠ trade direction",
            "fix": "All signals must align with trade direction"
        }
    ]
    
    for i, issue in enumerate(issues, 1):
        print(f"{i}. ❌ {issue['issue']}")
        print(f"   Impact: {issue['impact']}")
        print(f"   Cause: {issue['cause']}")
        print(f"   Fix: {issue['fix']}")
        print()

if __name__ == "__main__":
    test_scoring_issues()
    test_ideal_scenario()
    analyze_common_issues()
    
    print("💡 CONCLUSION:")
    print("   Low scores are likely due to:")
    print("   1. BOS not being confirmed (lose 2.0 points)")
    print("   2. FVGs being filled (lose 2.0 points)")  
    print("   3. Rejections not confirmed next candle (lose 1.0 points)")
    print("   4. This leaves only OB+Sweep+Engulfing = 3.0 points max")
    print("   5. System is working correctly but market conditions are weak!")
