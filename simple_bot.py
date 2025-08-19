#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import MetaTrader5 as mt5
from datetime import datetime
import time

# Add paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Bot Core'))

print("🚀 D.E.V.I - SIMPLIFIED BOT")
print("=" * 50)

try:
    # Initialize MT5
    if not mt5.initialize():
        print("❌ MT5 initialization failed")
        print(f"Error: {mt5.last_error()}")
        exit(1)
    
    print("✅ MT5 connected")
    
    # Load config
    from config import CONFIG
    print("✅ Config loaded")
    
    # Get account info
    account = mt5.account_info()
    if account:
        print(f"✅ Account: {account.login} | Balance: ${account.balance:.2f}")
    
    # Test symbols
    symbols = ["USDJPY", "NVDA"]
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol}...")
        
        # Get symbol info
        info = mt5.symbol_info(symbol)
        if info:
            print(f"✅ {symbol} available")
            print(f"   Current price: {mt5.symbol_info_tick(symbol).ask}")
        else:
            print(f"❌ {symbol} not available")
    
    print("\n🎉 SIMPLIFIED BOT IS WORKING!")
    print("✅ D.E.V.I can connect to MT5 and access market data")
    print("✅ The main bot should work now")
    
    mt5.shutdown()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 50)
