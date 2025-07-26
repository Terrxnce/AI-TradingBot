import MetaTrader5 as mt5
from config import CONFIG
from trade_state_tracker import mark_partial_closed
from datetime import datetime


def check_for_partial_close():

    if not mt5.terminal_info():
        print("⚠️ MT5 not initialized. Skipping partial close.")
        return

    acc_info = mt5.account_info()
    if acc_info is None:
        print("❌ Could not fetch account info.")
        return

    balance = acc_info.balance
    positions = mt5.positions_get()
    if not positions:
        print("🟡 No open positions to evaluate.")
        return

    threshold_percent = CONFIG.get("partial_close_trigger_percent", 1.0)
    profit_threshold = balance * (threshold_percent / 100)

    total_floating_profit = sum(p.profit for p in positions)
    print(f"📊 Floating PnL: ${total_floating_profit:.2f} | {threshold_percent}% of balance: ${profit_threshold:.2f}")

    if total_floating_profit >= profit_threshold:
        print(f"🎯 Floating PnL ≥ {threshold_percent}% — closing 50% and setting SL to breakeven...")

        for pos in positions:
            symbol = pos.symbol
            ticket = pos.ticket
            entry = pos.price_open
            volume = pos.volume
            current_sl = pos.sl

            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if info is None or tick is None:
                print(f"❌ Could not fetch data for {symbol}")
                continue

            digits = info.digits
            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

            # === 1. Close 50%
            symbol_info = mt5.symbol_info(symbol)
            min_vol = symbol_info.volume_min if symbol_info else 0.1  # fallback

            half_volume = round(volume / 2.0, 2)
            if half_volume >= min_vol:
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
                    
                    # ✅ Mark this trade for trailing SL later
                    mark_partial_closed(ticket)

                    DEFAULT_LOT = CONFIG["lot_size"]
                    CONFIG["LOT_SIZES"][symbol.upper()] = DEFAULT_LOT
                    print(f"🔁 Lot size for {symbol.upper()} reset to config default: {DEFAULT_LOT}")

                else:
                    print(f"❌ Failed to close 50% of {symbol}: {result_close.retcode} | {result_close.comment}")
            else:
                print(f"⚠️ {symbol} position too small to close half: {volume}")

            # === 2. Set SL to Breakeven for remaining
            entry_rounded = round(entry, digits)
            if round(current_sl, digits) != entry_rounded:
                result_sl = mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "sl": entry_rounded,
                    "tp": pos.tp if pos.tp > 0 else 0.0,
                    "symbol": symbol,
                })
                if result_sl.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"🔐 SL moved to breakeven for {symbol}")
                else:
                    print(f"❌ Failed to move SL for {symbol}: {result_sl.retcode} | {result_sl.comment}")
            else:
                print(f"⏸️ SL already at breakeven for {symbol}")

    else:
        print(f"⏳ Not yet hit {threshold_percent}% profit threshold.")

def close_all_positions():
    """
    Force close all open positions regardless of profit/loss.
    Used for end-of-day cleanup or emergency situations.
    """
    if not mt5.terminal_info():
        print("⚠️ MT5 not initialized. Cannot close positions.")
        return False

    positions = mt5.positions_get()
    if not positions:
        print("🟢 No open positions to close.")
        return True

    print(f"🔄 Closing {len(positions)} open position(s)...")
    
    success_count = 0
    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        volume = pos.volume
        
        # Get current market price for closing
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"❌ Could not get tick data for {symbol} position {ticket}")
            continue
            
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        
        result = mt5.order_send({
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "type_filling": mt5.ORDER_FILLING_IOC,
        })
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Closed {symbol} position {ticket} @ {price}")
            success_count += 1
        else:
            print(f"❌ Failed to close {symbol} position {ticket}: {result.retcode} | {result.comment}")
    
    print(f"📊 Successfully closed {success_count}/{len(positions)} positions.")
    return success_count == len(positions)


def close_trades_at_4pm():
    """
    Check if it's 4:00 PM and close all trades if so.
    Should be called in the main bot loop.
    """
    now = datetime.now()
    if now.hour == 16 and now.minute == 0:
        print("🕓 4:00 PM detected - Auto-closing all trades...")
        close_all_positions()
        return True
    return False