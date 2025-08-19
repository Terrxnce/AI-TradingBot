# ------------------------------------------------------------------------------------
# 🎯 equity_cycle_manager.py – D.E.V.I Equity-Based Profit Cycle System
#
# This module implements the new simplified equity-based profit management:
#   - +1.0% Floating PnL: Close 50% + Move SL to breakeven
#   - +1.5% Floating PnL: Close all remaining trades + Reset cycle
#   - +2.0% Floating PnL: Global autoclose + Pause new trades
#
# ✅ check_equity_cycle() – Main function to check and execute cycle stages
# ✅ close_partial_positions() – Close 50% of each open trade
# ✅ move_sl_to_breakeven() – Move stop loss to breakeven + buffer
# ✅ close_all_positions() – Close all remaining trades
# ✅ pause_new_trades() – Block new trades until daily reset
#
# Used by: bot_runner.py in main trading loop
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot - Equity Cycle Refactor
# ------------------------------------------------------------------------------------

import MetaTrader5 as mt5
import sys
import os
import json
from datetime import datetime, timedelta
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import CONFIG

# State file for tracking equity cycle
EQUITY_CYCLE_STATE_FILE = "equity_cycle_state.json"

def get_balance():
    """Get current account balance"""
    acc_info = mt5.account_info()
    if acc_info is None or acc_info.balance == 0:
        return CONFIG.get("initial_balance", 10_000)
    return acc_info.balance

def get_floating_pnl():
    """Get total floating PnL from all open positions"""
    positions = mt5.positions_get()
    if positions is None:
        return 0.0
    return sum(p.profit for p in positions)

def load_equity_cycle_state():
    """Load equity cycle state from file"""
    try:
        if os.path.exists(EQUITY_CYCLE_STATE_FILE):
            with open(EQUITY_CYCLE_STATE_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load equity cycle state: {e}")
    
    return {
        "stage_1_triggered": False,  # +1.0% (50% close + breakeven)
        "stage_2_triggered": False,  # +1.5% (close all + reset)
        "stage_3_triggered": False,  # +2.0% (pause trades)
        "session_date": None,
        "last_trigger_time": None,
        "trades_paused": False
    }

def save_equity_cycle_state(state):
    """Save equity cycle state to file"""
    try:
        with open(EQUITY_CYCLE_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to save equity cycle state: {e}")

def reset_cycle_if_new_session():
    """Reset cycle state if it's a new trading session"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    state = load_equity_cycle_state()
    
    if state.get("session_date") != current_date:
        print(f"🔄 New session detected ({current_date}). Resetting equity cycle.")
        state = {
            "stage_1_triggered": False,
            "stage_2_triggered": False,
            "stage_3_triggered": False,
            "session_date": current_date,
            "last_trigger_time": None,
            "trades_paused": False
        }
        save_equity_cycle_state(state)
        return True
    return False

def close_partial_positions():
    """Close 50% of each open position"""
    positions = mt5.positions_get()
    if not positions:
        print("🟡 No open positions to partially close.")
        return True
    
    success_count = 0
    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        volume = pos.volume
        
        # Calculate 50% volume
        symbol_info = mt5.symbol_info(symbol)
        min_vol = symbol_info.volume_min if symbol_info else 0.01
        half_volume = round(volume / 2.0, 2)
        
        # Skip if half volume is below minimum
        if half_volume < min_vol:
            print(f"⚠️ {symbol} position too small to close 50%: {volume}")
            continue
        
        # Get current market price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"❌ Could not get tick data for {symbol}")
            continue
        
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        
        # Close 50%
        result = mt5.order_send({
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": half_volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "comment": "DEVI_CYCLE_50%"
        })
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Closed 50% of {symbol} position @ {price:.5f}")
            success_count += 1
        else:
            print(f"❌ Failed to close 50% of {symbol}: {result.retcode} | {result.comment}")
    
    return success_count > 0

def move_sl_to_breakeven():
    """Move stop loss to breakeven + buffer for all remaining positions"""
    positions = mt5.positions_get()
    if not positions:
        print("🟡 No positions to move to breakeven.")
        return True
    
    success_count = 0
    breakeven_buffer_pips = 5  # Fixed 5 pip buffer
    
    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        entry_price = pos.price_open
        current_sl = pos.sl
        
        # Get symbol info for pip calculation
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"❌ Could not get symbol info for {symbol}")
            continue
        
        digits = symbol_info.digits
        point = symbol_info.point
        
        # Calculate breakeven + buffer
        if "JPY" in symbol:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        buffer_price = breakeven_buffer_pips * pip_value
        
        if pos.type == mt5.ORDER_TYPE_BUY:
            new_sl = entry_price + buffer_price
        else:
            new_sl = entry_price - buffer_price
        
        new_sl = round(new_sl, digits)
        
        # Only update if SL is not already at breakeven
        if abs(current_sl - new_sl) > point:
            result = mt5.order_send({
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "sl": new_sl,
                "tp": pos.tp if pos.tp > 0 else 0.0,
                "symbol": symbol,
                "comment": "DEVI_CYCLE_BE"
            })
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"🔐 Moved {symbol} SL to breakeven+{breakeven_buffer_pips}p: {new_sl:.5f}")
                success_count += 1
            else:
                print(f"❌ Failed to move {symbol} SL: {result.retcode} | {result.comment}")
        else:
            print(f"⏸️ {symbol} SL already at breakeven")
            success_count += 1
    
    return success_count > 0

def close_all_positions():
    """Close all remaining open positions"""
    positions = mt5.positions_get()
    if not positions:
        print("🟢 No open positions to close.")
        return True
    
    print(f"🔄 Closing all {len(positions)} remaining position(s)...")
    success_count = 0
    
    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        volume = pos.volume
        
        # Get current market price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"❌ Could not get tick data for {symbol}")
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
            "comment": "DEVI_CYCLE_FULL"
        })
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Closed {symbol} position @ {price:.5f}")
            success_count += 1
        else:
            print(f"❌ Failed to close {symbol}: {result.retcode} | {result.comment}")
    
    return success_count == len(positions)

def log_cycle_stage(stage, floating_pnl, balance, action):
    """Log cycle stage trigger to both trade log and AI decision log"""
    timestamp = datetime.now()
    
    # Log to trade_log.csv
    try:
        trade_log_entry = f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')},EQUITY_CYCLE,STAGE_{stage},{floating_pnl:.2f},{balance:.2f},{action}\n"
        with open("logs/trade_log.csv", "a") as f:
            f.write(trade_log_entry)
    except Exception as e:
        print(f"⚠️ Failed to log to trade_log.csv: {e}")
    
    # Log to ai_decision_log.jsonl
    try:
        ai_log_entry = {
            "timestamp": timestamp.isoformat(),
            "event_type": "equity_cycle_trigger",
            "stage": stage,
            "floating_pnl": floating_pnl,
            "balance": balance,
            "action": action,
            "threshold_percent": [1.0, 1.5, 2.0][stage - 1]
        }
        with open("ai_decision_log.jsonl", "a") as f:
            f.write(json.dumps(ai_log_entry) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to log to ai_decision_log.jsonl: {e}")

def check_equity_cycle():
    """
    Main function to check and execute equity cycle stages.
    Should be called in the main bot loop.
    
    Returns:
        bool: True if any cycle action was triggered
    """
    if not mt5.terminal_info():
        return False
    
    # Reset cycle if new session
    reset_cycle_if_new_session()
    
    balance = get_balance()
    floating_pnl = get_floating_pnl()
    
    if balance <= 0:
        return False
    
    # Calculate floating PnL percentage
    floating_pnl_percent = (floating_pnl / balance) * 100
    
    # Load current state
    state = load_equity_cycle_state()
    
    # Check if trades are paused (Stage 3 effect)
    if state.get("trades_paused", False):
        print(f"⏸️ New trades paused due to +2% equity cycle trigger")
        return False
    
    # Stage 3: +2.0% - Global autoclose + Pause trades
    if floating_pnl_percent >= 2.0 and not state.get("stage_3_triggered", False):
        print(f"🎯 Stage 3 Triggered: +2.0% floating PnL (${floating_pnl:.2f})")
        log_cycle_stage(3, floating_pnl, balance, "PAUSE_TRADES")
        
        # Close all positions
        if close_all_positions():
            state["stage_3_triggered"] = True
            state["trades_paused"] = True
            state["last_trigger_time"] = datetime.now().isoformat()
            save_equity_cycle_state(state)
            print("🛑 All trades closed. New trades paused until daily reset.")
            return True
    
    # Stage 2: +1.5% - Close all remaining + Reset cycle
    elif floating_pnl_percent >= 1.5 and not state.get("stage_2_triggered", False):
        print(f"🎯 Stage 2 Triggered: +1.5% floating PnL (${floating_pnl:.2f})")
        log_cycle_stage(2, floating_pnl, balance, "CLOSE_ALL")
        
        # Close all remaining positions
        if close_all_positions():
            state["stage_2_triggered"] = True
            state["last_trigger_time"] = datetime.now().isoformat()
            save_equity_cycle_state(state)
            print("✅ All remaining trades closed. Cycle ready for next session.")
            return True
    
    # Stage 1: +1.0% - Close 50% + Move to breakeven
    elif floating_pnl_percent >= 1.0 and not state.get("stage_1_triggered", False):
        print(f"🎯 Stage 1 Triggered: +1.0% floating PnL (${floating_pnl:.2f})")
        log_cycle_stage(1, floating_pnl, balance, "PARTIAL_CLOSE_BREAKEVEN")
        
        # Close 50% and move to breakeven
        partial_success = close_partial_positions()
        breakeven_success = move_sl_to_breakeven()
        
        if partial_success or breakeven_success:
            state["stage_1_triggered"] = True
            state["last_trigger_time"] = datetime.now().isoformat()
            save_equity_cycle_state(state)
            print("✅ Stage 1 complete: 50% closed, SL moved to breakeven")
            return True
    
    # No cycle action triggered
    return False

def is_trades_paused():
    """Check if new trades are paused due to Stage 3 trigger"""
    state = load_equity_cycle_state()
    return state.get("trades_paused", False)

def get_cycle_status():
    """Get current cycle status for monitoring"""
    state = load_equity_cycle_state()
    balance = get_balance()
    floating_pnl = get_floating_pnl()
    floating_percent = (floating_pnl / balance * 100) if balance > 0 else 0
    
    return {
        "floating_pnl": floating_pnl,
        "floating_percent": floating_percent,
        "stage_1_triggered": state.get("stage_1_triggered", False),
        "stage_2_triggered": state.get("stage_2_triggered", False),
        "stage_3_triggered": state.get("stage_3_triggered", False),
        "trades_paused": state.get("trades_paused", False),
        "session_date": state.get("session_date"),
        "next_threshold": 1.0 if not state.get("stage_1_triggered") else 
                         1.5 if not state.get("stage_2_triggered") else
                         2.0 if not state.get("stage_3_triggered") else None
    }

# Test function for development
if __name__ == "__main__":
    print("🧪 Testing Equity Cycle Manager")
    
    # Test cycle status
    status = get_cycle_status()
    print(f"Current Status: {status}")
    
    # Test state management
    state = load_equity_cycle_state()
    print(f"Current State: {state}")
