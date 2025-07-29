import MetaTrader5 as mt5
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import CONFIG
import os
import json

# Where we track cooldown to avoid re-triggering lock every loop
COOLDOWN_FILE = "profit_lock_cooldown.json"

def get_floating_pnl():
    positions = mt5.positions_get()
    if positions is None:
        return 0.0
    return sum(p.profit for p in positions)

def get_balance():
    acc_info = mt5.account_info()
    if acc_info is None or acc_info.balance == 0:
        return CONFIG.get("initial_balance", 10_000)
    return acc_info.balance

def all_trades_locked_recently():
    if not os.path.exists(COOLDOWN_FILE):
        return False

    with open(COOLDOWN_FILE, "r") as f:
        state = json.load(f)

    cooldown_minutes = CONFIG.get("global_profit_lock_cooldown_minutes", 60)
    last_trigger_time = datetime.fromisoformat(state.get("last_triggered", "1970-01-01T00:00:00"))
    return datetime.now() - last_trigger_time < timedelta(minutes=cooldown_minutes)

def record_lock_event():
    with open(COOLDOWN_FILE, "w") as f:
        json.dump({"last_triggered": datetime.now().isoformat()}, f)

def close_all_positions():
    positions = mt5.positions_get()
    if not positions:
        return

    for pos in positions:
        symbol = pos.symbol
        volume = pos.volume
        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            continue

        price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "position": pos.ticket,
            "price": price,
            "deviation": 10,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"🔐 Closed {symbol} ({volume}) to lock in profit.")
        else:
            print(f"❌ Failed to close {symbol}: {result.retcode} | {result.comment}")

def check_and_lock_profits():
    if not mt5.terminal_info():
        return

    if all_trades_locked_recently():
        print("⏳ Profit lock cooldown active — skipping.")
        return

    floating_pnl = get_floating_pnl()
    balance = get_balance()
    threshold_percent = CONFIG.get("global_profit_lock_percent", 2.0)
    threshold_amount = balance * (threshold_percent / 100)

    print(f"💰 Floating PnL: ${floating_pnl:.2f} | Lock Threshold: ${threshold_amount:.2f}")

    if floating_pnl >= threshold_amount:
        print(f"🎯 Profit target of {threshold_percent}% hit. Closing all trades.")
        close_all_positions()
        record_lock_event()
        
        # Reset partial close cycle when full close is triggered
        try:
            from position_manager import save_partial_close_cycle_state
            save_partial_close_cycle_state(triggered=False)
            print("🔄 Partial close cycle reset due to full profit lock.")
        except Exception as e:
            print(f"⚠️ Failed to reset partial close cycle: {e}")
    else:
        print("🔄 No profit lock triggered.")
