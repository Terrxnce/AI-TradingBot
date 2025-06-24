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
def place_trade(symbol: str, action: str, lot: float = 0.1, sl_price: float = 0.0, tp_price: float = 0.0):
    """
    Places a trade with specified parameters, including absolute SL and TP prices.
    sl_price and tp_price should be 0.0 if not used.
    """
    if not mt5.initialize():  # Ensure MT5 is initialized
        raise RuntimeError(f"❌ MT5 initialization failed: {mt5.last_error()}")

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
        print(f"⚠️ Market for {resolved_symbol} is not in full trade mode (possibly closed or specific restrictions). Skipping trade.")
        return

    tick = mt5.symbol_info_tick(resolved_symbol)
    if tick is None:
        raise RuntimeError(f"❌ Failed to get tick data for {resolved_symbol}.")

    # === Trade Parameters ===
    price = tick.ask if action.upper() == "BUY" else tick.bid
    digits = symbol_info.digits
    deviation = 10  # Standard deviation
    order_type = mt5.ORDER_TYPE_BUY if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL

    # Validate and round SL/TP prices if they are set (non-zero)
    # MT5 requires SL/TP to be 0 if not used, or a valid price level otherwise.
    # A common mistake is to send a very small non-zero number when SL/TP is not desired.
    final_sl = 0.0
    if sl_price != 0.0:
        # Basic validation: SL for BUY must be below price, SL for SELL must be above price
        if action.upper() == "BUY" and sl_price >= price:
            print(f"⚠️ Warning: SL price {sl_price} for BUY is not below current price {price}. Adjusting SL to 0 (no SL).")
        elif action.upper() == "SELL" and sl_price <= price:
            print(f"⚠️ Warning: SL price {sl_price} for SELL is not above current price {price}. Adjusting SL to 0 (no SL).")
        else:
            final_sl = round(sl_price, digits)

    final_tp = 0.0
    if tp_price != 0.0:
        # Basic validation: TP for BUY must be above price, TP for SELL must be below price
        if action.upper() == "BUY" and tp_price <= price:
            print(f"⚠️ Warning: TP price {tp_price} for BUY is not above current price {price}. Adjusting TP to 0 (no TP).")
        elif action.upper() == "SELL" and tp_price >= price:
            print(f"⚠️ Warning: TP price {tp_price} for SELL is not below current price {price}. Adjusting TP to 0 (no TP).")
        else:
            final_tp = round(tp_price, digits)

    print(f"🧮 Order Details: Action={action.upper()}, Symbol={resolved_symbol}, Price={price:.{digits}f}, SL={final_sl:.{digits}f}, TP={final_tp:.{digits}f}, Lot={lot}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": resolved_symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": final_sl,
        "tp": final_tp,
        "deviation": deviation,
        "magic": 123456,
        "comment": f"AI Trading Bot {action.upper()}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    print(f"ℹ️ Attempting to send trade request: {request}")

    result = mt5.order_send(request)

    print(f"ℹ️ Trade request sent. Full result: {result}")  # Detailed logging of result

    if result is None:
        print(f"❌ Trade failed: mt5.order_send() returned None. Last error: {mt5.last_error()}")
        return

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        # Specific error codes can be helpful
        error_map = {
            10004: "Requote",
            10006: "Request rejected",
            10007: "Request canceled by trader",
            10008: "Order placed", # Should not happen with TRADE_ACTION_DEAL
            10009: "Request completed", # TRADE_RETCODE_DONE
            10010: "Only part of the request was completed",
            10011: "Request processing error",
            10012: "Request canceled by timeout",
            10013: "Invalid request",
            10014: "Invalid volume in the request",
            10015: "Invalid price in the request",
            10016: "Invalid stops in the request",
            10017: "Trade is disabled",
            10018: "Market is closed",
            10019: "There is not enough money to complete the request",
            10020: "Prices changed",
            10021: "There are no quotes to process the request",
            10022: "Invalid order expiration date in the request",
            10023: "Order state changed",
            10024: "Too frequent requests",
            10025: "No changes in request",
            10026: "Autotrading disabled by server",
            10027: "Autotrading disabled by client terminal", # Check "Algo Trading" button in MT5
            10028: "Request locked for processing",
            10029: "Order or position frozen",
            10030: "Invalid order filling type",
            10031: "No connection with the trade server",
            10032: "Operation is allowed only for live accounts",
            10033: "The number of pending orders has reached the limit",
            10034: "The volume of orders and positions for the symbol has reached the limit",
            10035: "Incorrect or prohibited order type",
            10036: "Position not found", # For close/modify
            10038: "A close volume exceeds the current position volume",
            10039: "A close order already exists for a specified position",
            10040: "The number of open positions simultaneously present on an account can be limited by the server settings",
            10041: "The pending order activation request is rejected, the order is canceled",
            10042: "The request is rejected, because the rule \"Only long positions are allowed\" is set for the symbol",
            10043: "The request is rejected, because the rule \"Only short positions are allowed\" is set for the symbol",
            10044: "The request is rejected, because the rule \"Only position closing is allowed\" is set for the symbol",
            10045: "The request is rejected, because the rule \"Position closing is allowed only by FIFO rule\" is set for the symbol",
            10046: "The request is rejected, because the rule \"Opposite positions on a symbol are prohibited\" is set for the symbol"
        }
        error_description = error_map.get(result.retcode, "Unknown error")

        print(f"❌ Trade failed: RetCode={result.retcode} - {error_description} (Broker comment: {result.comment})")

        if result.retcode == 10018: # Market Closed
            print(f"⚠️ Market closed for {resolved_symbol}. Skipping trade cleanly.")
            return # Already handled, but good to be explicit
        elif result.retcode == 10027: # Autotrading disabled in terminal
            print(f"🚨 CRITICAL: Autotrading is disabled in the MetaTrader 5 terminal. Please enable it (Tools -> Options -> Expert Advisors -> Allow algorithmic trading, AND the 'Algo Trading' button on the toolbar).")
        elif result.retcode == 10017: # Trading disabled for symbol
            print(f"🚨 CRITICAL: Trading is disabled for the symbol {resolved_symbol} on your account or by the broker.")
        elif result.retcode == 10019: # Not enough money
            print(f"🚨 CRITICAL: Insufficient funds to place the trade for {resolved_symbol} with volume {lot}.")
        return

    print(f"✅ Trade executed: {action} {resolved_symbol} @ {price:.{digits}f}. Order ID: {result.order}")
