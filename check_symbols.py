import MetaTrader5 as mt5

def check_available_symbols():
    if not mt5.initialize():
        print("❌ MT5 initialization failed")
        return
    
    print("✅ MT5 initialized")
    
    # Get all symbols
    symbols = mt5.symbols_get()
    if symbols is None:
        print("❌ Failed to get symbols")
        return
    
    print(f"📊 Total symbols available: {len(symbols)}")
    
    # Show first 20 symbols
    print("\n🔍 First 20 symbols:")
    for i, symbol in enumerate(symbols[:20]):
        print(f"{i+1:2d}. {symbol.name}")
    
    # Check for specific symbols
    test_symbols = ["EURUSD", "GBPUSD", "USDJPY", "NVDA", "AAPL", "US500"]
    print(f"\n🔍 Checking specific symbols:")
    for symbol_name in test_symbols:
        symbol_info = mt5.symbol_info(symbol_name)
        if symbol_info:
            status = "✅ Available" if symbol_info.visible else "⚠️ Not in Market Watch"
            print(f"   {symbol_name}: {status}")
        else:
            print(f"   {symbol_name}: ❌ Not found")
    
    mt5.shutdown()

if __name__ == "__main__":
    check_available_symbols()
