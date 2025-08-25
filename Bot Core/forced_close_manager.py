# ------------------------------------------------------------------------------------
# 🚨 forced_close_manager.py – Forced Auto-Close System
#
# Handles forced closure of all positions at session boundaries:
# - NY AM Close: 15:00 UTC (4:00 PM Irish)
# - PM Close: 19:00 UTC (8:00 PM Irish)  
# - Asian Close: 03:00 UTC (4:00 AM Irish)
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import MetaTrader5 as mt5
import sys
import os
from datetime import datetime, timezone
from typing import List, Dict

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
from config import CONFIG

def get_all_open_positions() -> List[Dict]:
    """Get all open positions from MT5"""
    positions = mt5.positions_get()
    if positions is None:
        return []
    
    return [
        {
            'ticket': pos.ticket,
            'symbol': pos.symbol,
            'type': pos.type,
            'volume': pos.volume,
            'price_open': pos.price_open,
            'price_current': pos.price_current,
            'profit': pos.profit,
            'comment': pos.comment
        }
        for pos in positions
    ]

def close_position(ticket: int, reason: str) -> bool:
    """Close a specific position by ticket"""
    position = mt5.positions_get(ticket=ticket)
    if not position:
        print(f"❌ Position {ticket} not found")
        return False
    
    pos = position[0]
    
    # Determine close action based on position type
    if pos.type == mt5.POSITION_TYPE_BUY:
        action = mt5.TRADE_ACTION_DEAL
        order_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(pos.symbol).bid
    else:
        action = mt5.TRADE_ACTION_DEAL
        order_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(pos.symbol).ask
    
    # Prepare close request
    request = {
        "action": action,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": order_type,
        "position": ticket,
        "price": price,
        "deviation": 10,
        "magic": 123456,
        "comment": f"FORCED_CLOSE_{reason}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    # Send close order
    result = mt5.order_send(request)
    
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"✅ Closed position {ticket} ({pos.symbol}) - {reason}")
        return True
    else:
        error_msg = getattr(result, 'comment', 'Unknown error') if result else 'No result'
        print(f"❌ Failed to close position {ticket}: {error_msg}")
        return False

def close_all_positions(reason: str) -> Dict:
    """
    Close all open positions
    
    Args:
        reason: Reason for closure (ny_close, pm_close, asia_close)
    
    Returns:
        Dict with close results
    """
    print(f"🚨 FORCED CLOSE TRIGGERED: {reason}")
    print(f"🕐 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    positions = get_all_open_positions()
    
    if not positions:
        print("ℹ️ No open positions to close")
        return {
            "total_positions": 0,
            "closed_successfully": 0,
            "failed_to_close": 0,
            "reason": reason
        }
    
    print(f"📊 Found {len(positions)} open positions")
    
    closed_count = 0
    failed_count = 0
    
    for pos in positions:
        print(f"🔒 Closing {pos['symbol']} (Ticket: {pos['ticket']}) - PnL: {pos['profit']:.2f}")
        
        if close_position(pos['ticket'], reason):
            closed_count += 1
        else:
            failed_count += 1
    
    # Summary
    print(f"📈 FORCED CLOSE SUMMARY:")
    print(f"   Total positions: {len(positions)}")
    print(f"   Closed successfully: {closed_count}")
    print(f"   Failed to close: {failed_count}")
    print(f"   Reason: {reason}")
    
    return {
        "total_positions": len(positions),
        "closed_successfully": closed_count,
        "failed_to_close": failed_count,
        "reason": reason
    }

def get_close_reason_display(reason: str) -> str:
    """Get human-readable close reason"""
    display_names = {
        "ny_close": "New York AM Session Close",
        "pm_close": "PM Session Close", 
        "asia_close": "Asian Session Close"
    }
    return display_names.get(reason, reason)

def log_forced_close_event(reason: str, results: Dict):
    """Log forced close event to file"""
    try:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "forced_close",
            "reason": reason,
            "display_reason": get_close_reason_display(reason),
            "results": results
        }
        
        # Log to forced close log file
        log_file = "forced_close_log.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            import json
            f.write(json.dumps(log_entry) + "\n")
            
    except Exception as e:
        print(f"⚠️ Failed to log forced close event: {e}")

def execute_forced_close(reason: str) -> Dict:
    """
    Execute forced close with logging
    
    Args:
        reason: Close reason (ny_close, pm_close, asia_close)
    
    Returns:
        Close results
    """
    results = close_all_positions(reason)
    log_forced_close_event(reason, results)
    return results
