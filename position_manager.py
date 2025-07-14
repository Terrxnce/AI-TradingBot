import MetaTrader5 as mt5

def check_for_2_percent_gain():
    positions = mt5.positions_get()
    if positions is None:
        print("❌ No open positions found.")
        return

    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        entry = pos.price_open
        volume = pos.volume
        current_sl = pos.sl
        point = mt5.symbol_info(symbol).point
        digits = mt5.symbol_info(symbol).digits
        price = mt5.symbol_info_tick(symbol).bid if pos.type == 0 else mt5.symbol_info_tick(symbol).ask

        # Calculate % gain
        gain = ((price - entry) / entry) * 100 if pos.type == 0 else ((entry - price) / entry) * 100

        if gain >= 2.0:
            print(f"🚀 {symbol} is up {gain:.2f}% — evaluating SL move and 50% close")

            # === 1. Move SL to breakeven only if it's not already there
            entry_rounded = round(entry, digits)
            if round(current_sl, digits) != entry_rounded:
                result_sl = mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "sl": entry_rounded,
                    "tp": pos.tp,
                    "symbol": symbol,
                })
                if result_sl.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"🔐 SL moved to breakeven for {symbol}")
                else:
                    print(f"❌ Failed to move SL for {symbol}: {result_sl.retcode} | {result_sl.comment}")
            else:
                print(f"⏸️ SL already at breakeven for {symbol} — no change")

            # === 2. Close 50% of volume
            half_volume = round(volume / 2.0, 2)
            if half_volume >= 0.1:
                close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                result_close = mt5.order_send({
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": half_volume,
                    "type": close_type,
                    "position": ticket,
                    "price": price,
                    "deviation": 10,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                })
                if result_close.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ Closed 50% of {symbol} @ {price}")
                else:
                    print(f"❌ Failed to close 50% of {symbol}: {result_close.retcode} | {result_close.comment}")
            else:
                print(f"⚠️ Position too small to close half: {volume}")
