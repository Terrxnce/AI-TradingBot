#!/usr/bin/env python3
"""
Quick validation script for D.E.V.I trading bot
"""

import sys
import os
sys.path.append('Bot Core')
sys.path.append('Data Files')

def main():
    print("🔍 D.E.V.I Quick Validation")
    print("=" * 40)
    
    # Test 1: Config
    try:
        from config import CONFIG
        print("✅ Config loaded")
        print(f"   Min score: {CONFIG['min_score_for_trade']}")
        print(f"   Trading window: {CONFIG['allowed_trading_window']}")
        print(f"   Dynamic RRR: {CONFIG['enable_dynamic_rrr']}")
    except Exception as e:
        print(f"❌ Config failed: {e}")
        return False
    
    # Test 2: Core modules
    try:
        from decision_engine import evaluate_trade_decision
        from strategy_engine import analyze_structure
        from broker_interface import place_trade
        from calculate_structural_sl_tp import calculate_structural_sl_tp
        from risk_guard import can_trade
        print("✅ All core modules imported")
    except Exception as e:
        print(f"❌ Module import failed: {e}")
        return False
    
    # Test 3: MT5 connection
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            account = mt5.account_info()
            if account:
                print(f"✅ MT5 connected - Account: {account.login}")
                print(f"   Balance: ${account.balance:.2f}")
            else:
                print("❌ MT5 account info unavailable")
                return False
        else:
            print("❌ MT5 initialization failed")
            return False
        mt5.shutdown()
    except Exception as e:
        print(f"❌ MT5 test failed: {e}")
        return False
    
    print("\n🎉 VALIDATION SUCCESSFUL!")
    print("✅ D.E.V.I is ready for live trading")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
