import MetaTrader5 as mt5
import sys
import os

def test_broker_requirements():
    """Test broker requirements for EURUSD trading"""
    
    if not mt5.initialize():
        print("❌ MT5 initialization failed")
        return
    
    print("✅ MT5 initialized")
    
    # Test EURUSD specifically
    symbol = "EURUSD"
    symbol_info = mt5.symbol_info(symbol)
    
    if symbol_info is None:
        print(f"❌ {symbol} not found in broker")
        return
    
    print(f"\n📊 {symbol} Information:")
    print(f"   Name: {symbol_info.name}")
    print(f"   Trade Mode: {symbol_info.trade_mode}")
    print(f"   Volume Min: {symbol_info.volume_min}")
    print(f"   Volume Max: {symbol_info.volume_max}")
    print(f"   Volume Step: {symbol_info.volume_step}")
    print(f"   Point: {symbol_info.point}")
    print(f"   Digits: {symbol_info.digits}")
    print(f"   Stop Level: {symbol_info.trade_stops_level}")
    print(f"   Freeze Level: {symbol_info.trade_freeze_level}")
    
    # Check if we can trade
    if symbol_info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
        print(f"❌ {symbol} is not available for trading")
        return
    
    # Test minimum lot size
    test_lot = 0.0075
    if test_lot < symbol_info.volume_min:
        print(f"❌ Test lot {test_lot} is below minimum {symbol_info.volume_min}")
        print(f"💡 Try using lot size: {symbol_info.volume_min}")
    else:
        print(f"✅ Test lot {test_lot} is above minimum {symbol_info.volume_min}")
    
    # Get current tick
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        print(f"\n💰 Current Prices:")
        print(f"   Bid: {tick.bid}")
        print(f"   Ask: {tick.ask}")
        print(f"   Spread: {tick.ask - tick.bid}")
    else:
        print(f"❌ No tick data for {symbol}")
    
    # Test account info
    account = mt5.account_info()
    if account:
        print(f"\n💳 Account Info:")
        print(f"   Balance: ${account.balance}")
        print(f"   Equity: ${account.equity}")
        print(f"   Margin: ${account.margin}")
        print(f"   Free Margin: ${account.margin_free}")
    else:
        print("❌ No account info available")
    
    mt5.shutdown()

if __name__ == "__main__":
    test_broker_requirements()
