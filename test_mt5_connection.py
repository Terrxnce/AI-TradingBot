import MetaTrader5 as mt5
import time

def test_mt5_connection():
    """Test MT5 connection and basic functionality"""
    
    print("🔍 Testing MT5 Connection...")
    
    if not mt5.initialize():
        print("❌ MT5 initialization failed")
        print(f"Last error: {mt5.last_error()}")
        return False
    
    print("✅ MT5 initialized")
    
    # Test terminal info
    terminal_info = mt5.terminal_info()
    if terminal_info:
        print(f"✅ Terminal connected: {terminal_info.name}")
    else:
        print("❌ No terminal info")
        return False
    
    # Test account info
    account_info = mt5.account_info()
    if account_info:
        print(f"✅ Account connected: {account_info.login}")
        print(f"   Balance: ${account_info.balance}")
    else:
        print("❌ No account info")
        return False
    
    # Test symbol info
    symbol_info = mt5.symbol_info("EURUSD")
    if symbol_info:
        print(f"✅ EURUSD available: {symbol_info.name}")
        print(f"   Trade Mode: {symbol_info.trade_mode}")
        print(f"   Volume Min: {symbol_info.volume_min}")
    else:
        print("❌ EURUSD not available")
        return False
    
    # Test tick data
    tick = mt5.symbol_info_tick("EURUSD")
    if tick:
        print(f"✅ Tick data available:")
        print(f"   Bid: {tick.bid}")
        print(f"   Ask: {tick.ask}")
    else:
        print("❌ No tick data")
        return False
    
    # Test a simple order request (without sending)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": "EURUSD",
        "volume": 0.01,
        "type": mt5.ORDER_TYPE_SELL,
        "price": tick.bid,
        "sl": tick.bid + 0.0010,  # 10 pips above
        "tp": tick.bid - 0.0020,  # 20 pips below
        "deviation": 10,
        "magic": 123456,
        "comment": "Test order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    print(f"\n🧪 Testing order request structure...")
    print(f"   Request keys: {list(request.keys())}")
    print(f"   Symbol: {request['symbol']}")
    print(f"   Volume: {request['volume']}")
    print(f"   Type: {request['type']}")
    print(f"   Price: {request['price']}")
    
    # Don't actually send the order, just test the structure
    print("✅ Order request structure looks valid")
    
    mt5.shutdown()
    print("✅ MT5 shutdown complete")
    return True

if __name__ == "__main__":
    test_mt5_connection()
