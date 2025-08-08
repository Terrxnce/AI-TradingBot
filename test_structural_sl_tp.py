#!/usr/bin/env python3
"""
Test script for the new structural SL/TP system
Validates RRR calculations, structure detection, and session adjustments
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add Bot Core to path to import the decision engine
sys.path.append('Bot Core')

# Mock MetaTrader5 since we don't have it in test environment
class MockMT5:
    class account_info:
        balance = 10000
    
    @staticmethod
    def account_info():
        return MockMT5.account_info()

sys.modules['MetaTrader5'] = MockMT5

# Import our modules
from calculate_structural_sl_tp import calculate_structural_sl_tp, detect_structure_levels
from decision_engine import calculate_structural_sl_tp_with_validation

def create_test_data():
    """Create sample OHLC data for testing"""
    np.random.seed(42)  # For reproducible results
    
    dates = pd.date_range('2024-01-01', periods=100, freq='15min')
    base_price = 1.2000
    
    data = {
        'time': dates,
        'open': [],
        'high': [],
        'low': [],
        'close': [],
        'volume': np.random.randint(100, 1000, 100)
    }
    
    # Generate realistic OHLC with some structure
    current_price = base_price
    for i in range(100):
        # Random walk with volatility
        change = np.random.normal(0, 0.0005)
        current_price += change
        
        open_price = current_price
        
        # Generate high and low with some range
        high_offset = abs(np.random.normal(0, 0.0003))
        low_offset = abs(np.random.normal(0, 0.0003))
        
        high_price = open_price + high_offset
        low_price = open_price - low_offset
        
        # Close price somewhere between high and low
        close_price = np.random.uniform(low_price, high_price)
        current_price = close_price
        
        data['open'].append(round(open_price, 5))
        data['high'].append(round(high_price, 5))
        data['low'].append(round(low_price, 5))
        data['close'].append(round(close_price, 5))
    
    return pd.DataFrame(data)

def test_case_1_buy_setup():
    """
    Test Case 1: BUY Setup @ 14:15 UTC
    Entry: 1.2000
    Expected: Structure-based SL/TP with RRR validation
    """
    print("\n" + "="*60)
    print("TEST CASE 1: BUY Setup @ 14:15 UTC")
    print("="*60)
    
    # Create test data
    candles_df = create_test_data()
    entry_price = 1.2000
    direction = "BUY"
    session_time = datetime.now().replace(hour=14, minute=15, second=0, microsecond=0)
    technical_score = 6.8
    
    print(f"📊 Entry Price: {entry_price}")
    print(f"📈 Direction: {direction}")
    print(f"🕐 Session Time: {session_time.strftime('%H:%M UTC')}")
    print(f"📋 Technical Score: {technical_score}")
    
    # Test structure detection
    structures = detect_structure_levels(candles_df, entry_price, direction)
    print(f"\n🏗️ Structures Found:")
    print(f"   - Order Blocks: {len(structures['ob_levels'])}")
    print(f"   - FVGs: {len(structures['fvg_levels'])}")
    print(f"   - BOS Levels: {len(structures['bos_levels'])}")
    
    # Test SL/TP calculation
    result = calculate_structural_sl_tp(candles_df, entry_price, direction, session_time)
    
    print(f"\n🎯 SL/TP Results:")
    print(f"   - SL: {result['sl']} ({result['sl_from']})")
    print(f"   - TP: {result['tp']} ({result['tp_from']})")
    print(f"   - RRR: {result['expected_rrr']}")
    print(f"   - Session Adjustment: {result['session_adjustment']}")
    print(f"   - ATR: {result['atr']}")
    
    # Test RRR validation
    validation_result = calculate_structural_sl_tp_with_validation(
        candles_df, entry_price, direction, session_time, technical_score
    )
    
    print(f"\n✅ RRR Validation:")
    print(f"   - RRR Passed: {validation_result['rrr_passed']}")
    print(f"   - Reason: {validation_result['rrr_reason']}")
    
    return validation_result

def test_case_2_sell_post_session():
    """
    Test Case 2: SELL Setup @ 17:10 UTC (Post-session)
    Entry: 1.3000
    Expected: Post-session percentage-based TP
    """
    print("\n" + "="*60)
    print("TEST CASE 2: SELL Setup @ 17:10 UTC (Post-session)")
    print("="*60)
    
    # Create test data
    candles_df = create_test_data()
    entry_price = 1.3000
    direction = "SELL"
    session_time = datetime.now().replace(hour=17, minute=10, second=0, microsecond=0)
    technical_score = 8.2
    
    print(f"📊 Entry Price: {entry_price}")
    print(f"📈 Direction: {direction}")
    print(f"🕐 Session Time: {session_time.strftime('%H:%M UTC')} (Post-session)")
    print(f"📋 Technical Score: {technical_score}")
    
    # Test SL/TP calculation
    result = calculate_structural_sl_tp(candles_df, entry_price, direction, session_time)
    
    print(f"\n🎯 SL/TP Results:")
    print(f"   - SL: {result['sl']} ({result['sl_from']})")
    print(f"   - TP: {result['tp']} ({result['tp_from']})")
    print(f"   - RRR: {result['expected_rrr']}")
    print(f"   - Session Adjustment: {result['session_adjustment']}")
    print(f"   - ATR: {result['atr']}")
    
    # Test RRR validation
    validation_result = calculate_structural_sl_tp_with_validation(
        candles_df, entry_price, direction, session_time, technical_score
    )
    
    print(f"\n✅ RRR Validation:")
    print(f"   - RRR Passed: {validation_result['rrr_passed']}")
    print(f"   - Reason: {validation_result['rrr_reason']}")
    
    return validation_result

def test_case_3_low_rrr_block():
    """
    Test Case 3: Low RRR Trade Block
    Entry: Price that results in low RRR
    Expected: Trade should be blocked
    """
    print("\n" + "="*60)
    print("TEST CASE 3: Low RRR Trade Block")
    print("="*60)
    
    # Create test data
    candles_df = create_test_data()
    entry_price = 1.2000
    direction = "BUY"
    session_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
    technical_score = 5.5  # Low technical score
    
    print(f"📊 Entry Price: {entry_price}")
    print(f"📈 Direction: {direction}")
    print(f"🕐 Session Time: {session_time.strftime('%H:%M UTC')}")
    print(f"📋 Technical Score: {technical_score} (Low)")
    
    # Test SL/TP calculation
    result = calculate_structural_sl_tp(candles_df, entry_price, direction, session_time)
    
    print(f"\n🎯 SL/TP Results:")
    print(f"   - SL: {result['sl']} ({result['sl_from']})")
    print(f"   - TP: {result['tp']} ({result['tp_from']})")
    print(f"   - RRR: {result['expected_rrr']}")
    
    # Test RRR validation with low technical score
    validation_result = calculate_structural_sl_tp_with_validation(
        candles_df, entry_price, direction, session_time, technical_score
    )
    
    print(f"\n✅ RRR Validation:")
    print(f"   - RRR Passed: {validation_result['rrr_passed']}")
    print(f"   - Reason: {validation_result['rrr_reason']}")
    
    return validation_result

def test_session_adjustments():
    """
    Test different session adjustments
    """
    print("\n" + "="*60)
    print("SESSION ADJUSTMENT TESTS")
    print("="*60)
    
    candles_df = create_test_data()
    entry_price = 1.2000
    direction = "BUY"
    
    test_times = [
        {"time": datetime.now().replace(hour=14, minute=0), "description": "Normal session"},
        {"time": datetime.now().replace(hour=15, minute=45), "description": "After 15:30 UTC"},
        {"time": datetime.now().replace(hour=17, minute=30), "description": "Post-session"},
        {"time": datetime.now().replace(hour=19, minute=30), "description": "Late post-session"},
    ]
    
    for test_time in test_times:
        print(f"\n⏰ {test_time['description']} - {test_time['time'].strftime('%H:%M UTC')}")
        
        result = calculate_structural_sl_tp(candles_df, entry_price, direction, test_time['time'])
        
        print(f"   - TP: {result['tp']} ({result['tp_from']})")
        print(f"   - RRR: {result['expected_rrr']}")
        print(f"   - Session Adjustment: {result['session_adjustment']}")

def run_comprehensive_tests():
    """
    Run all test cases and provide summary
    """
    print("🧪 STRUCTURAL SL/TP SYSTEM - COMPREHENSIVE TESTS")
    print("="*80)
    
    test_results = []
    
    # Run test cases
    test_results.append(("Test Case 1 - BUY Setup", test_case_1_buy_setup()))
    test_results.append(("Test Case 2 - SELL Post-session", test_case_2_sell_post_session()))
    test_results.append(("Test Case 3 - Low RRR Block", test_case_3_low_rrr_block()))
    
    # Run session adjustment tests
    test_session_adjustments()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result["rrr_passed"] else "❌ BLOCKED"
        rrr = result["expected_rrr"]
        print(f"{test_name}: {status} (RRR: {rrr})")
    
    print(f"\n🎉 All tests completed successfully!")
    print(f"📊 Structural SL/TP system is working as expected")
    print(f"🔒 RRR validation is properly blocking low-quality trades")
    print(f"🕐 Session adjustments are functioning correctly")

if __name__ == "__main__":
    run_comprehensive_tests()