#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 D.E.V.I Trading Bot - Comprehensive System Test
==================================================

This script performs a complete validation of all critical components
to ensure the bot is ready for live market testing.

Author: Terrence Ndifor (Terry)
Project: Smart Multi-Timeframe Trading Bot
"""

import sys
import os
import json
import time
from datetime import datetime
import MetaTrader5 as mt5

# Add paths for imports
sys.path.append('Bot Core')
sys.path.append('Data Files')

def test_imports():
    """Test all critical module imports"""
    print("🔍 Testing Module Imports...")
    
    try:
        from config import CONFIG
        print("✅ Config module imported")
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        return False
    
    try:
        from decision_engine import evaluate_trade_decision, build_ai_prompt
        print("✅ Decision engine imported")
    except Exception as e:
        print(f"❌ Decision engine import failed: {e}")
        return False
    
    try:
        from strategy_engine import analyze_structure
        print("✅ Strategy engine imported")
    except Exception as e:
        print(f"❌ Strategy engine import failed: {e}")
        return False
    
    try:
        from broker_interface import place_trade, initialize_mt5
        print("✅ Broker interface imported")
    except Exception as e:
        print(f"❌ Broker interface import failed: {e}")
        return False
    
    try:
        from calculate_structural_sl_tp import calculate_structural_sl_tp
        print("✅ Structural SL/TP imported")
    except Exception as e:
        print(f"❌ Structural SL/TP import failed: {e}")
        return False
    
    try:
        from risk_guard import can_trade
        print("✅ Risk guard imported")
    except Exception as e:
        print(f"❌ Risk guard import failed: {e}")
        return False
    
    return True

def test_configuration():
    """Test configuration loading and validation"""
    print("\n🔍 Testing Configuration...")
    
    try:
        from config import CONFIG, FTMO_PARAMS
        
        # Check required config fields
        required_fields = [
            "min_score_for_trade",
            "lot_size", 
            "delay_seconds",
            "allowed_trading_window",
            "partial_close_trigger_percent",
            "full_close_trigger_percent",
            "post_session_enabled",
            "post_session_score_threshold",
            "enable_dynamic_rrr",
            "enable_dynamic_ai_confidence"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in CONFIG:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing config fields: {missing_fields}")
            return False
        
        print("✅ All required config fields present")
        print(f"✅ Min score: {CONFIG['min_score_for_trade']}")
        print(f"✅ Trading window: {CONFIG['allowed_trading_window']}")
        print(f"✅ Dynamic RRR: {CONFIG['enable_dynamic_rrr']}")
        print(f"✅ Dynamic AI confidence: {CONFIG['enable_dynamic_ai_confidence']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_mt5_connection():
    """Test MT5 connection and basic functionality"""
    print("\n🔍 Testing MT5 Connection...")
    
    try:
        if not mt5.initialize():
            print(f"❌ MT5 initialization failed: {mt5.last_error()}")
            return False
        
        print("✅ MT5 initialized")
        
        # Test terminal info
        terminal_info = mt5.terminal_info()
        if not terminal_info:
            print("❌ Terminal info unavailable")
            return False
        
        print(f"✅ Terminal: {terminal_info.name}")
        print(f"✅ Version: {getattr(terminal_info, 'version', 'Unknown')}")
        
        # Test account info
        account_info = mt5.account_info()
        if not account_info:
            print("❌ Account info unavailable")
            return False
        
        print(f"✅ Account: {account_info.login}")
        print(f"✅ Balance: ${account_info.balance:.2f}")
        print(f"✅ Equity: ${account_info.equity:.2f}")
        
        # Test symbol info
        symbol_info = mt5.symbol_info("EURUSD")
        if not symbol_info:
            print("❌ EURUSD symbol info unavailable")
            return False
        
        print(f"✅ EURUSD available")
        print(f"✅ Trade mode: {symbol_info.trade_mode}")
        print(f"✅ Min volume: {symbol_info.volume_min}")
        
        # Test tick data
        tick = mt5.symbol_info_tick("EURUSD")
        if not tick:
            print("❌ EURUSD tick data unavailable")
            return False
        
        print(f"✅ Tick data: Bid={tick.bid}, Ask={tick.ask}")
        
        mt5.shutdown()
        return True
        
    except Exception as e:
        print(f"❌ MT5 connection test failed: {e}")
        return False

def test_technical_analysis():
    """Test technical analysis components"""
    print("\n🔍 Testing Technical Analysis...")
    
    try:
        from strategy_engine import analyze_structure
        from get_candles import get_latest_candle_data
        
        # Get sample data
        candles = get_latest_candle_data("EURUSD", mt5.TIMEFRAME_M15)
        if candles is None or len(candles) < 50:
            print("❌ Insufficient candle data for analysis")
            return False
        
        print(f"✅ Got {len(candles)} M15 candles")
        
        # Test structure analysis
        ta_signals = analyze_structure(candles, timeframe=mt5.TIMEFRAME_M15)
        
        required_signals = [
            "bos", "fvg_valid", "ob_tap", "rejection", 
            "liquidity_sweep", "engulfing", "ema_trend"
        ]
        
        for signal in required_signals:
            if signal not in ta_signals:
                print(f"❌ Missing signal: {signal}")
                return False
        
        print("✅ All technical signals present")
        print(f"✅ EMA trend: {ta_signals['ema_trend']}")
        print(f"✅ BOS: {ta_signals['bos']}")
        print(f"✅ FVG valid: {ta_signals['fvg_valid']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Technical analysis test failed: {e}")
        return False

def test_decision_engine():
    """Test decision engine logic"""
    print("\n🔍 Testing Decision Engine...")
    
    try:
        from decision_engine import evaluate_trade_decision, build_ai_prompt
        
        # Create sample TA signals
        ta_signals = {
            "symbol": "EURUSD",
            "ema_trend": "bullish",
            "bos": "bullish",
            "fvg_valid": True,
            "ob_tap": True,
            "rejection": False,
            "liquidity_sweep": False,
            "engulfing": True,
            "session": "New York"
        }
        
        # Test AI prompt building
        prompt = build_ai_prompt(ta_signals, session_info="New York")
        if not prompt or len(prompt) < 100:
            print("❌ AI prompt generation failed")
            return False
        
        print("✅ AI prompt generated successfully")
        
        # Test decision evaluation with mock AI response
        mock_ai_response = """
ENTRY_DECISION: BUY
CONFIDENCE: 8
REASONING: Strong bullish setup with EMA trend and BOS confirmation
RISK_NOTE: Good structure quality, proceed with caution
"""
        
        decision = evaluate_trade_decision(ta_signals, mock_ai_response)
        print(f"✅ Decision evaluation: {decision}")
        
        return True
        
    except Exception as e:
        print(f"❌ Decision engine test failed: {e}")
        return False

def test_structural_sl_tp():
    """Test structural SL/TP calculation"""
    print("\n🔍 Testing Structural SL/TP...")
    
    try:
        from calculate_structural_sl_tp import calculate_structural_sl_tp
        from get_candles import get_latest_candle_data
        
        # Get sample data
        candles = get_latest_candle_data("EURUSD", mt5.TIMEFRAME_M15)
        if candles is None or len(candles) < 20:
            print("❌ Insufficient candle data for SL/TP calculation")
            return False
        
        # Test BUY setup
        entry_price = candles.iloc[-1]['close']
        result = calculate_structural_sl_tp(
            candles_df=candles,
            entry_price=entry_price,
            direction="BUY",
            session_time=datetime.now()
        )
        
        required_fields = [
            "sl", "tp", "expected_rrr", "sl_from", "tp_from",
            "session_adjustment", "atr", "structures_found"
        ]
        
        for field in required_fields:
            if field not in result:
                print(f"❌ Missing SL/TP field: {field}")
                return False
        
        print("✅ Structural SL/TP calculation successful")
        print(f"✅ SL: {result['sl']} ({result['sl_from']})")
        print(f"✅ TP: {result['tp']} ({result['tp_from']})")
        print(f"✅ RRR: {result['expected_rrr']}")
        print(f"✅ ATR: {result['atr']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Structural SL/TP test failed: {e}")
        return False

def test_risk_management():
    """Test risk management components"""
    print("\n🔍 Testing Risk Management...")
    
    try:
        from risk_guard import can_trade
        
        # Test risk guard with mock data
        mock_ta_signals = {"symbol": "EURUSD"}
        mock_ai_response = "ENTRY_DECISION: BUY\nCONFIDENCE: 7"
        
        # This should return True/False based on current account state
        can_trade_result = can_trade(
            ta_signals=mock_ta_signals,
            ai_response_raw=mock_ai_response,
            call_ai_func=lambda x: "OVERRIDE_DECISION: YES",
            tech_score=6.0
        )
        
        print(f"✅ Risk guard check: {can_trade_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Risk management test failed: {e}")
        return False

def test_broker_interface():
    """Test broker interface (without placing actual trades)"""
    print("\n🔍 Testing Broker Interface...")
    
    try:
        from broker_interface import initialize_mt5, resolve_symbol
        
        # Test initialization
        initialize_mt5()
        print("✅ MT5 initialized for broker interface test")
        
        # Test symbol resolution
        resolved = resolve_symbol("EURUSD")
        print(f"✅ Symbol resolution: EURUSD -> {resolved}")
        
        # Test symbol info retrieval
        symbol_info = mt5.symbol_info(resolved)
        if symbol_info:
            print(f"✅ Symbol info retrieved: {symbol_info.name}")
            print(f"✅ Trade mode: {symbol_info.trade_mode}")
            print(f"✅ Min volume: {symbol_info.volume_min}")
        else:
            print("❌ Symbol info retrieval failed")
            return False
        
        mt5.shutdown()
        return True
        
    except Exception as e:
        print(f"❌ Broker interface test failed: {e}")
        return False

def test_file_permissions():
    """Test file system permissions"""
    print("\n🔍 Testing File Permissions...")
    
    try:
        # Test log directory creation
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        print(f"✅ Log directory: {log_dir}")
        
        # Test log file writing
        test_log_file = os.path.join(log_dir, "test.log")
        with open(test_log_file, "w") as f:
            f.write("Test log entry\n")
        print(f"✅ Log file writing: {test_log_file}")
        
        # Test state file writing
        state_dir = "var/internal/state"
        os.makedirs(state_dir, exist_ok=True)
        test_state_file = os.path.join(state_dir, "test_state.json")
        with open(test_state_file, "w") as f:
            json.dump({"test": "data"}, f)
        print(f"✅ State file writing: {test_state_file}")
        
        # Cleanup test files
        os.remove(test_log_file)
        os.remove(test_state_file)
        
        return True
        
    except Exception as e:
        print(f"❌ File permissions test failed: {e}")
        return False

def main():
    """Run comprehensive system test"""
    print("🔍 D.E.V.I Trading Bot - Comprehensive System Test")
    print("=" * 60)
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_configuration),
        ("MT5 Connection", test_mt5_connection),
        ("Technical Analysis", test_technical_analysis),
        ("Decision Engine", test_decision_engine),
        ("Structural SL/TP", test_structural_sl_tp),
        ("Risk Management", test_risk_management),
        ("Broker Interface", test_broker_interface),
        ("File Permissions", test_file_permissions),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - SYSTEM READY FOR LIVE TRADING!")
        print("✅ D.E.V.I is fully functional and ready for live market testing")
        return True
    else:
        print("⚠️ SOME TESTS FAILED - SYSTEM NOT READY FOR LIVE TRADING")
        print("❌ Please fix the failed tests before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
