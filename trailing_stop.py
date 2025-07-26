import MetaTrader5 as mt5
from datetime import datetime, timedelta
from trade_state_tracker import should_apply_trailing_sl, mark_trailing_applied

def apply_trailing_stop(minutes=30, trail_pips=20):
    if not mt5.terminal_info():
        return

    positions = mt5.positions_get()
    if not positions:
        return

    for pos in positions:
        open_time = datetime.fromtimestamp(pos.time)

        # ✅ Only apply if trade meets time or partial-close logic
        if not should_apply_trailing_sl(pos.ticket, open_time):
            continue

        if pos.profit <= 0:
            continue  # Only trail if profitable

        symbol_info = mt5.symbol_info(pos.symbol)
        if not symbol_info:
            continue

        point = symbol_info.point
        digits = symbol_info.digits
        sl_offset = trail_pips * point
        current_sl = pos.sl if pos.sl else 0

        # === Calculate New SL
        if pos.type == mt5.ORDER_TYPE_BUY:
            new_sl = max(pos.price_open + sl_offset, current_sl)
            if new_sl <= current_sl:
                continue
        elif pos.type == mt5.ORDER_TYPE_SELL:
            new_sl = min(pos.price_open - sl_offset, current_sl if current_sl != 0 else float('inf'))
            if new_sl >= current_sl:
                continue
        else:
            continue

        # === Apply Trailing SL
        result = mt5.order_send({
            "action": mt5.TRADE_ACTION_SLTP,
            "position": pos.ticket,
            "sl": round(new_sl, digits),
            "tp": pos.tp,
            "symbol": pos.symbol,
        })

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"🔄 Trailing SL modified for {pos.symbol} | New SL: {round(new_sl, digits)}")
            reason = "partial" if (datetime.now() - open_time < timedelta(minutes=minutes)) else "30min"
            mark_trailing_applied(pos.ticket, reason=reason)
        else:
            print(f"❌ Failed to modify SL for {pos.symbol}: {result.retcode} | {result.comment}")
