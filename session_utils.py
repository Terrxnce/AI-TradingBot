import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import CONFIG
from datetime import datetime, time

def detect_session():
    """Detect current trading session based on UTC time"""
    now = datetime.utcnow()
    current_hour = now.hour
    
    session_hours = CONFIG.get("session_hours", {})
    
    if 1 <= current_hour < 7:
        return "Asia"
    elif 8 <= current_hour < 12:
        return "London"
    elif 13.5 <= current_hour < 14:
        return "New York Pre-Market"
    elif 14 <= current_hour < 20:
        return "New York"
    elif 20 <= current_hour < 24:
        return "Post-Market"
    else:
        return "Off-Hours"

def is_post_session():
    """
    Check if current time is within post-session trading window
    Post-Session: 17:00-19:00 UTC (5:00-7:00 PM UTC)
    """
    now = datetime.utcnow()
    current_hour = now.hour
    current_minute = now.minute
    
    # Post-session window: 17:00-19:00 UTC
    post_session_start = 17  # 5:00 PM UTC
    post_session_end = 19    # 7:00 PM UTC
    
    # Check if within post-session window
    if post_session_start <= current_hour < post_session_end:
        return True
    
    # Check for soft extension past 19:00 UTC
    if current_hour == 19 and current_minute <= 30:
        return True
    
    return False

def get_post_session_time_remaining():
    """
    Get remaining time in post-session window
    Returns minutes remaining until hard exit at 19:30 UTC
    """
    now = datetime.utcnow()
    hard_exit_time = now.replace(hour=19, minute=30, second=0, microsecond=0)
    
    if now >= hard_exit_time:
        return 0
    
    time_diff = hard_exit_time - now
    return int(time_diff.total_seconds() / 60)

def is_post_session_extension_allowed(entry_time, floating_pnl_percent, stop_loss_hit=False):
    """
    Check if post-session trade can extend past 19:00 UTC
    Conditions:
    - Trade must be in profit > 1.0%
    - Trade age <= 30 minutes
    - Stop loss not hit
    """
    now = datetime.utcnow()
    
    # Check if past 19:00 UTC
    if now.hour < 19:
        return False
    
    # Check if stop loss was hit
    if stop_loss_hit:
        return False
    
    # Check floating PnL requirement
    min_pnl = CONFIG.get("post_session_extension_min_pnl", 1.0)
    if floating_pnl_percent < min_pnl:
        return False
    
    # Check trade age (max 30 minutes)
    max_extension_minutes = CONFIG.get("post_session_max_extension_minutes", 30)
    trade_age_minutes = (now - entry_time).total_seconds() / 60
    
    if trade_age_minutes > max_extension_minutes:
        return False
    
    return True

def get_post_session_lot_size(base_lot_size):
    """
    Calculate post-session lot size based on configuration
    Returns 0.75x base lot size for post-session trades
    """
    multiplier = CONFIG.get("post_session_lot_multiplier", 0.75)
    return base_lot_size * multiplier
