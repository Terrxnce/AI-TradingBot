# ------------------------------------------------------------------------------------
# 🧪 test_ai_timeout_fix.py – Test AI Timeout Technical Override
#
# Tests the new technical override logic for AI timeouts
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'Bot Core'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))

from decision_engine import evaluate_trade_decision_legacy

def test_ai_timeout_scenarios():
    """Test various AI timeout scenarios"""
    
    print("🧪 TESTING AI TIMEOUT TECHNICAL OVERRIDE")
    print("=" * 50)
    
    # Mock TA signals for a strong bearish setup
    strong_bearish_signals = {
        "bos": "bearish",
        "fvg_valid": True,
        "ob_tap": True,
        "rejection": True,
        "liquidity_sweep": True,
        "engulfing": True,
        "ema_trend": "bearish",
        "session": "PM"
    }
    
    # Mock TA signals for a weak setup
    weak_signals = {
        "bos": None,
        "fvg_valid": False,
        "ob_tap": False,
        "rejection": False,
        "liquidity_sweep": False,
        "engulfing": False,
        "ema_trend": "neutral",
        "session": "PM"
    }
    
    # Test scenarios
    test_cases = [
        {
            "name": "Strong Technicals + AI Timeout (Should Trade)",
            "signals": strong_bearish_signals,
            "ai_response": "",  # Empty response = timeout
            "expected": "SELL"
        },
        {
            "name": "Weak Technicals + AI Timeout (Should Not Trade)",
            "signals": weak_signals,
            "ai_response": "",  # Empty response = timeout
            "expected": "HOLD"
        },
        {
            "name": "Strong Technicals + Good AI (Should Trade)",
            "signals": strong_bearish_signals,
            "ai_response": "ENTRY_DECISION: SELL\nCONFIDENCE: 8\nREASONING: Strong bearish signals\nRISK_NOTE: Good risk/reward",
            "expected": "SELL"
        },
        {
            "name": "Strong Technicals + Low AI Confidence (Should Not Trade)",
            "signals": strong_bearish_signals,
            "ai_response": "ENTRY_DECISION: SELL\nCONFIDENCE: 5\nREASONING: Weak signals\nRISK_NOTE: High risk",
            "expected": "HOLD"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            result = evaluate_trade_decision_legacy(test_case['signals'], test_case['ai_response'])
            
            status = "✅" if result == test_case['expected'] else "❌"
            print(f"{status} Result: {result} | Expected: {test_case['expected']}")
            
            if result != test_case['expected']:
                print(f"   ❌ FAILED: Got {result}, expected {test_case['expected']}")
            else:
                print(f"   ✅ PASSED: Correct decision")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("✅ AI Timeout Fix Test Complete!")

if __name__ == "__main__":
    test_ai_timeout_scenarios()
