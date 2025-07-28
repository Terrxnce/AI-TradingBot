import MetaTrader5 as mt5
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
from config import CONFIG  # Load SL/TP from config
from notifier import send_trade_notification
import time

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
    all_symbols = mt5.symbols_get() 
    if all_symbols is None:
        raise RuntimeError("❌ Failed to fetch symbols from broker.")
    for sym in all_symbols:
        if sym.name.upper().startswith(base_symbol.upper()):
            return sym.name
    return base_symbol  # fallback

def get_account_info_safe():
    """
    Safely fetches account info from MT5.
    Attempts to recover if MT5 was disconnected or not logged in.
    """
    acc_info = mt5.account_info()

    if acc_info is None:
        print("⚠️ Account info unavailable. Attempting recovery...")
        mt5.shutdown()
        time.sleep(2)
        initialize_mt5()

        acc_info = mt5.account_info()
        if acc_info is None:
            print("❌ Account info still unavailable after recovery.")
        else:
            print(f"✅ MT5 recovered. Balance: {acc_info.balance}, Equity: {acc_info.equity}")

    return acc_info

# === Trade Execution with optional SL/TP ===
def place_trade(symbol, action, lot=0.1, sl=None, tp=None, tech_score=None, ema_trend=None, ai_confidence=None, ai_reasoning=None, risk_note=None):
    if not mt5.terminal_info():
        print("❌ MT5 terminal not Connected - Cannot place trade.")
        return False

    resolved_symbol = resolve_symbol(symbol)
    print(f"🔍 Using resolved symbol: {resolved_symbol}")

    symbol_info = mt5.symbol_info(resolved_symbol)
    if symbol_info is None:
        print(f"❌ Symbol {resolved_symbol} not found.")
        return False

    if not symbol_info.visible:
        print(f"📂 Enabling {resolved_symbol} in Market Watch...")
        if not mt5.symbol_select(resolved_symbol, True):
            print(f"❌ Failed to enable {resolved_symbol} in Market Watch.")
            return False

    tick = mt5.symbol_info_tick(resolved_symbol)
    if tick is None or tick.bid == 0.0:
        print(f"❌ Failed to get tick data for {resolved_symbol}. Is the market open?")
        return False
    else:
        print(f"📈 {resolved_symbol}: trading context is now fully active.")

    if symbol_info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
        print(f"⚠️ Market is closed for {resolved_symbol}. Skipping trade.")
        return False

    price = tick.ask if action == "BUY" else tick.bid
    point = symbol_info.point
    digits = symbol_info.digits
    deviation = 10
    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL

    # === SL/TP Logic ===
    if sl is None or tp is None:
        sl_pips = CONFIG.get("sl_pips", 50)
        tp_pips = CONFIG.get("tp_pips", 100)

        stop_level = symbol_info.trade_stops_level or 10
        freeze_level = symbol_info.trade_freeze_level or 0
        min_distance = max(stop_level, freeze_level) * point

        sl_distance = max(sl_pips * point, min_distance)
        tp_distance = max(tp_pips * point, min_distance)

        sl = price - sl_distance if action == "BUY" else price + sl_distance
        tp = price + tp_distance if action == "BUY" else price - tp_distance

    print(f"🧲 Price: {price:.{digits}f} | SL: {sl:.{digits}f} | TP: {tp:.{digits}f}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": resolved_symbol,
        "volume": lot,
        "type": order_type,
        "price": round(price, digits),
        "sl": round(sl, digits),
        "tp": round(tp, digits),
        "deviation": deviation,
        "magic": 123456,
        "comment": f"AI Trading Bot {action}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result is None or not hasattr(result, 'retcode'):
        print(f"❌ Order send failed. No result returned.")
        return False

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        if result.retcode == 10018:
            print(f"⚠️ Market closed for {resolved_symbol}. Skipping trade.")
        else:
            print(f"❌ Trade failed: {result.retcode} - {getattr(result, 'comment', 'No comment')}")
        return False
    else:
        print(f"✅ Trade executed: {action} {resolved_symbol} @ {price:.{digits}f}")

        # === Send Telegram Signal ===
        try:
            send_trade_notification(
                symbol=resolved_symbol,
                direction=action,
                entry=round(price, digits),
                sl=round(sl, digits),
                tp=round(tp, digits),
                lot=lot,
                tech_score=tech_score,
                ema_trend=ema_trend,
                ai_confidence=ai_confidence,
                ai_reasoning=ai_reasoning,
                risk_note=risk_note or "No risk note provided"
            )

            print("📤 Signal sent to Telegram.")
        except Exception as e:
            print(f"⚠️ Failed to send Telegram signal: {e}")

        return True


