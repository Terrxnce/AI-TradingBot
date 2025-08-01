# ------------------------------------------------------------------------------------
# 🕐 post_session_manager.py – Post-Session Trading Logic
#
# This module handles all post-session specific trading logic:
# - Post-session trade detection and filtering
# - Reduced lot sizing (0.75x base lot)
# - Enhanced profit management (0.75% partial, 1.5% full)
# - Trailing stop after 30 minutes in profit
# - Soft extension logic past 19:00 UTC
# - Hard exit at 19:30 UTC
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Post-Session v2.4.0
# ------------------------------------------------------------------------------------

import MetaTrader5 as mt5
import sys
import os
import json
from datetime import datetime, timedelta
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import CONFIG
from session_utils import is_post_session, get_post_session_time_remaining, is_post_session_extension_allowed, get_post_session_lot_size

# State file for tracking post-session trades
POST_SESSION_STATE_FILE = "post_session_state.json"

def load_post_session_state():
    """Load post-session trading state"""
    try:
        if os.path.exists(POST_SESSION_STATE_FILE):
            with open(POST_SESSION_STATE_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load post-session state: {e}")
    return {
        "session_date": None,
        "trades_opened": [],
        "reentries_used": {}
    }

def save_post_session_state(state):
    """Save post-session trading state"""
    try:
        with open(POST_SESSION_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to save post-session state: {e}")

def reset_post_session_state_if_needed():
    """Reset post-session state if it's a new session date"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    state = load_post_session_state()
    
    if state.get("session_date") != current_date:
        print(f"🔄 New post-session date detected. Resetting state.")
        new_state = {
            "session_date": current_date,
            "trades_opened": [],
            "reentries_used": {}
        }
        save_post_session_state(new_state)
        return new_state
    
    return state

def is_post_session_trade_eligible(symbol, technical_score, ai_confidence=0):
    """
    Check if a trade is eligible for post-session trading
    Requirements:
    - Must be in post-session window
    - Technical score >= 8.0
    - AI confidence >= 70% (if score < 8.0)
    """
    if not is_post_session():
        return False, "Not in post-session window"
    
    if not CONFIG.get("post_session_enabled", True):
        return False, "Post-session trading disabled"
    
    score_threshold = CONFIG.get("post_session_score_threshold", 8.0)
    min_confidence = CONFIG.get("post_session_min_ai_confidence", 70)
    
    # Check technical score requirement
    if technical_score < score_threshold:
        return False, f"Technical score {technical_score} below threshold {score_threshold}"
    
    # Check AI confidence if score is borderline
    if technical_score < 8.0 and ai_confidence < min_confidence:
        return False, f"AI confidence {ai_confidence}% below minimum {min_confidence}%"
    
    # Check re-entry limits
    state = load_post_session_state()
    symbol_reentries = state.get("reentries_used", {}).get(symbol, 0)
    max_reentries = CONFIG.get("post_session_max_reentries_per_symbol", 1)
    
    if symbol_reentries >= max_reentries:
        return False, f"Maximum re-entries ({max_reentries}) reached for {symbol}"
    
    return True, "Eligible for post-session trading"

def get_post_session_lot_size_for_symbol(symbol, base_lot_size):
    """
    Get the appropriate lot size for post-session trading
    Returns 0.75x base lot size for all post-session trades
    """
    return get_post_session_lot_size(base_lot_size)

def check_post_session_partial_close():
    """
    Check if post-session trades should be partially closed
    Triggers at 0.75% floating profit
    """
    if not is_post_session():
        return
    
    positions = mt5.positions_get()
    if not positions:
        return
    
    # Filter for post-session trades only
    post_session_positions = []
    for pos in positions:
        if hasattr(pos, 'comment') and pos.comment and 'post_session=true' in pos.comment:
            post_session_positions.append(pos)
    
    if not post_session_positions:
        return
    
    account_info = mt5.account_info()
    if not account_info:
        return
    
    balance = account_info.balance
    partial_close_percent = CONFIG.get("post_session_partial_close_percent", 0.75)
    profit_threshold = balance * (partial_close_percent / 100)
    
    for pos in post_session_positions:
        if pos.profit >= profit_threshold:
            print(f"🎯 Post-session partial close triggered for {pos.symbol} at {partial_close_percent}% profit")
            # Close 50% of position
            close_half_position(pos)

def check_post_session_full_close():
    """
    Check if post-session trades should be fully closed
    Triggers at 1.5% floating profit
    """
    if not is_post_session():
        return
    
    positions = mt5.positions_get()
    if not positions:
        return
    
    # Filter for post-session trades only
    post_session_positions = []
    for pos in positions:
        if hasattr(pos, 'comment') and pos.comment and 'post_session=true' in pos.comment:
            post_session_positions.append(pos)
    
    if not post_session_positions:
        return
    
    account_info = mt5.account_info()
    if not account_info:
        return
    
    balance = account_info.balance
    full_close_percent = CONFIG.get("post_session_full_close_percent", 1.5)
    profit_threshold = balance * (full_close_percent / 100)
    
    for pos in post_session_positions:
        if pos.profit >= profit_threshold:
            print(f"🎯 Post-session full close triggered for {pos.symbol} at {full_close_percent}% profit")
            close_full_position(pos)

def check_post_session_hard_exit():
    """
    Force close all post-session trades at 19:30 UTC
    No exceptions - hard exit
    """
    now = datetime.utcnow()
    
    # Check if it's 19:30 UTC or later
    if now.hour == 19 and now.minute >= 30:
        positions = mt5.positions_get()
        if not positions:
            return
        
        # Filter for post-session trades only
        post_session_positions = []
        for pos in positions:
            if hasattr(pos, 'comment') and pos.comment and 'post_session=true' in pos.comment:
                post_session_positions.append(pos)
        
        if post_session_positions:
            print(f"🕐 Post-session hard exit triggered at 19:30 UTC - closing {len(post_session_positions)} trades")
            for pos in post_session_positions:
                close_full_position(pos)

def close_half_position(position):
    """Close 50% of a position"""
    try:
        symbol = position.symbol
        volume = position.volume
        half_volume = round(volume / 2.0, 2)
        
        if half_volume < 0.01:  # Minimum volume check
            return
        
        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(symbol)
        
        if tick is None:
            return
        
        price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask
        
        result = mt5.order_send({
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": half_volume,
            "type": close_type,
            "position": position.ticket,
            "price": price,
            "deviation": 10,
            "type_filling": mt5.ORDER_FILLING_IOC
        })
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Closed 50% of post-session {symbol} position")
        else:
            print(f"❌ Failed to close 50% of {symbol}: {result.retcode}")
    
    except Exception as e:
        print(f"⚠️ Error closing half position: {e}")

def close_full_position(position):
    """Close entire position"""
    try:
        symbol = position.symbol
        volume = position.volume
        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(symbol)
        
        if tick is None:
            return
        
        price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask
        
        result = mt5.order_send({
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": close_type,
            "position": position.ticket,
            "price": price,
            "deviation": 10,
            "type_filling": mt5.ORDER_FILLING_IOC
        })
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Closed full post-session {symbol} position")
        else:
            print(f"❌ Failed to close {symbol}: {result.retcode}")
    
    except Exception as e:
        print(f"⚠️ Error closing full position: {e}")

def record_post_session_trade(symbol, ticket, entry_time):
    """Record a post-session trade in the state file"""
    state = load_post_session_state()
    
    trade_record = {
        "symbol": symbol,
        "ticket": ticket,
        "entry_time": entry_time.isoformat(),
        "entry_price": 0,  # Will be filled by MT5 data
        "status": "open"
    }
    
    state["trades_opened"].append(trade_record)
    save_post_session_state(state)
    print(f"📝 Recorded post-session trade: {symbol} (Ticket: {ticket})")

def record_post_session_reentry(symbol):
    """Record a re-entry for a symbol"""
    state = load_post_session_state()
    
    if "reentries_used" not in state:
        state["reentries_used"] = {}
    
    state["reentries_used"][symbol] = state["reentries_used"].get(symbol, 0) + 1
    save_post_session_state(state)
    print(f"📝 Recorded re-entry for {symbol}")

def get_post_session_status():
    """Get current post-session status"""
    now = datetime.utcnow()
    is_active = is_post_session()
    time_remaining = get_post_session_time_remaining()
    
    positions = mt5.positions_get()
    post_session_positions = []
    
    if positions:
        for pos in positions:
            if hasattr(pos, 'comment') and pos.comment and 'post_session=true' in pos.comment:
                post_session_positions.append(pos)
    
    return {
        "is_active": is_active,
        "time_remaining_minutes": time_remaining,
        "open_positions": len(post_session_positions),
        "current_time_utc": now.strftime("%H:%M UTC"),
        "hard_exit_time": "19:30 UTC"
    } 