import MetaTrader5 as mt5
from datetime import datetime, timedelta

def apply_trailing_stop(minutes=30, trail_pips=20):
    positions = mt5.positions_get()
    if not positions:
        return

    for pos in positions:
        open_time = datetime.fromtimestamp(pos.time)
        if datetime.now() - open_time < timedelta(minutes=minutes):
            continue
        if pos.profit <= 0:
            continue  # only trail if profitable

        symbol_info = mt5.symbol_info(pos.symbol)
        point = symbol_info.point
        digits = symbol_info.digits
        sl_offset = trail_pips * point
        current_sl = pos.sl if pos.sl else 0

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

        result = mt5.order_send({
            "action": mt5.TRADE_ACTION_SLTP,
            "position": pos.ticket,
            "sl": round(new_sl, digits),
            "tp": pos.tp,
            "symbol": pos.symbol,
        })

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"🔄 Trailing SL modified for {pos.symbol} | New SL: {round(new_sl, digits)}")
        else:
            print(f"❌ Failed to modify SL for {pos.symbol}: {result.retcode} | {result.comment}")
