import MetaTrader5 as mt5

# === MT5 Setup ===
def initialize_mt5():
    if not mt5.initialize():
        raise RuntimeError(f"❌ MT5 initialization failed: {mt5.last_error()}")
    print("✅ MT5 initialized")

def shutdown_mt5():
    mt5.shutdown()
    print("📴 MT5 shutdown")


# === Symbol Resolution ===
def resolve_symbol(base_symbol):
    if not mt5.initialize():  # Double-check MT5 is up before fetching symbols
        raise RuntimeError(f"❌ MT5 not initialized: {mt5.last_error()}")

    all_symbols = mt5.symbols_get()
    if all_symbols is None:
        raise RuntimeError("❌ Failed to fetch symbols from broker.")

    for sym in all_symbols:
        if sym.name.upper().startswith(base_symbol.upper()):
            return sym.name

    return base_symbol  # fallback


# === Trade Execution ===
def place_trade(symbol, action, lot=0.1):
    if not mt5.initialize():  # Ensure MT5 is initialized
        raise RuntimeError(f"❌ MT5 not initialized: {mt5.last_error()}")

    resolved_symbol = symbol.upper()

    symbol_info = mt5.symbol_info(resolved_symbol)
    if symbol_info is None:
        raise ValueError(f"❌ Symbol {resolved_symbol} not found.")

    if not symbol_info.visible:
        print(f"📂 Enabling {resolved_symbol} in Market Watch...")
        if not mt5.symbol_select(resolved_symbol, True):
            raise RuntimeError(f"❌ Failed to enable {resolved_symbol} in Market Watch.")

    # ✅ Check if market is open
    if symbol_info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
        print(f"⚠️ Market is closed for {resolved_symbol}. Skipping trade cleanly.")
        return  # Just exit cleanly

    tick = mt5.symbol_info_tick(resolved_symbol)
    if tick is None:
        raise RuntimeError(f"❌ Failed to get tick data for {resolved_symbol}.")

    # === Trade Parameters ===
    price = tick.ask if action == "BUY" else tick.bid
    point = symbol_info.point
    digits = symbol_info.digits
    deviation = 10
    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL

    # ✅ Hardcoded 50 pip SL, 100 pip TP
    sl_pips = 50
    tp_pips = 100

    # Get broker stop settings
    stop_level = symbol_info.trade_stops_level or 10
    freeze_level = symbol_info.trade_freeze_level or 0
    min_distance = max(stop_level, freeze_level) * point

    # Convert pips to distance and ensure it's valid
    sl_distance = max(sl_pips * point, min_distance)
    tp_distance = max(tp_pips * point, min_distance)

    sl = price - sl_distance if action == "BUY" else price + sl_distance
    tp = price + tp_distance if action == "BUY" else price - tp_distance

    print(f"🧮 Price: {price:.{digits}f} | SL: {sl:.{digits}f} | TP: {tp:.{digits}f} | MinStop: {min_distance:.5f}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": resolved_symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": round(sl, digits),
        "tp": round(tp, digits),
        "deviation": deviation,
        "magic": 123456,
        "comment": f"AI Trading Bot {action}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        if result.retcode == 10018:
            print(f"⚠️ Market closed for {resolved_symbol}. Skipping trade cleanly.")
            return
        else:
            print(f"❌ Trade failed: {result.retcode} - {result.comment}")
            return

    print(f"✅ Trade executed: {action} {resolved_symbol} @ {price:.{digits}f}")
