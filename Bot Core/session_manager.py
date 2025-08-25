# ------------------------------------------------------------------------------------
# 🕐 session_manager.py – New Session Management System
#
# Handles all session logic with:
# - NY AM Session (12:30-15:00 UTC) - 100% lot, 6.0 min score
# - PM Session (17:00-19:00 UTC) - 75% lot, 7.0 min score  
# - Asian Session (00:00-03:00 UTC) - 50% lot, 7.0 min score
# - Forced auto-close at session boundaries
# - UTC-based time handling
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import sys
import os
from datetime import datetime, timezone, time
from typing import Dict, Optional, Tuple

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
from config import CONFIG

class SessionManager:
    """Comprehensive session management with forced auto-close points"""
    
    def __init__(self):
        self.sessions = CONFIG.get("sessions", {})
        self._current_session_cache = None
        self._last_check_time = None
    
    def get_current_utc_time(self) -> datetime:
        """Get current UTC time"""
        return datetime.now(timezone.utc)
    
    def parse_time_string(self, time_str: str) -> time:
        """Parse time string like '12:30' to time object"""
        hour, minute = map(int, time_str.split(':'))
        return time(hour, minute)
    
    def is_time_in_range(self, current_time: time, start_time: time, end_time: time) -> bool:
        """Check if current time is within a time range"""
        if start_time <= end_time:
            # Same day range (e.g., 12:30-15:00)
            return start_time <= current_time < end_time
        else:
            # Overnight range (e.g., 23:00-06:00)
            return current_time >= start_time or current_time < end_time
    
    def get_current_session_info(self) -> Dict:
        """
        Get current session information
        
        Returns:
            Dict with session_type, lot_multiplier, min_score, auto_close_time
        """
        now_utc = self.get_current_utc_time()
        current_time = now_utc.time()
        
        # Check for forced auto-close first
        forced_close = self.check_for_forced_close(now_utc)
        if forced_close:
            return {
                "session_type": "FORCED_CLOSE",
                "reason": forced_close,
                "lot_multiplier": 0.0,
                "min_score": 0.0,
                "current_time_utc": current_time.strftime("%H:%M"),
                "auto_close_time": None
            }
        
        # Check each session
        for session_name, session_config in self.sessions.items():
            start_time = self.parse_time_string(session_config["start_utc"])
            end_time = self.parse_time_string(session_config["end_utc"])
            
            if self.is_time_in_range(current_time, start_time, end_time):
                return {
                    "session_type": session_name.upper(),
                    "session_name": session_name,  # Add lowercase session name for hourly limiter
                    "lot_multiplier": session_config["lot_multiplier"],
                    "min_score": session_config["min_score"],
                    "current_time_utc": current_time.strftime("%H:%M"),
                    "session_window": f"{session_config['start_utc']}-{session_config['end_utc']}",
                    "auto_close_time": session_config["auto_close_utc"]
                }
        
        # No active session
        return {
            "session_type": "OFF",
            "session_name": "off",  # Add lowercase session name for hourly limiter
            "lot_multiplier": 0.0,
            "min_score": 0.0,
            "current_time_utc": current_time.strftime("%H:%M"),
            "session_window": "No active session",
            "auto_close_time": None
        }
    
    def get_current_session_name(self) -> str:
        """
        Get current session name (lowercase) for hourly limiter
        
        Returns:
            str: Current session name (e.g., 'ny_am', 'pm', 'asian', 'off')
        """
        session_info = self.get_current_session_info()
        return session_info.get("session_name", "off")
    
    def check_for_forced_close(self, now_utc: datetime) -> Optional[str]:
        """
        Check if current time requires forced auto-close
        
        Returns:
            Close reason string or None
        """
        current_hour = now_utc.hour
        current_minute = now_utc.minute
        
        # Check exact auto-close times
        if current_hour == 15 and current_minute == 0:
            return "ny_close"
        elif current_hour == 19 and current_minute == 0:
            return "pm_close"
        elif current_hour == 3 and current_minute == 0:
            return "asia_close"
        
        return None
    
    def get_next_session_start(self) -> Tuple[str, datetime]:
        """
        Get the next session start time
        
        Returns:
            Tuple of (session_name, start_datetime)
        """
        now_utc = self.get_current_utc_time()
        current_time = now_utc.time()
        
        # Define session order (chronological within a day)
        session_order = ["asian", "ny_am", "pm"]
        
        # Find next session in chronological order
        for session_name in session_order:
            if session_name not in self.sessions:
                continue
                
            session_config = self.sessions[session_name]
            start_time = self.parse_time_string(session_config["start_utc"])
            
            # If current time is before this session start, this is the next one
            if current_time < start_time:
                next_start = now_utc.replace(
                    hour=start_time.hour,
                    minute=start_time.minute,
                    second=0,
                    microsecond=0
                )
                return session_name, next_start
        
        # If we're past all sessions today, next is asian session tomorrow
        asian_config = self.sessions["asian"]
        start_time = self.parse_time_string(asian_config["start_utc"])
        
        next_start = now_utc.replace(
            hour=start_time.hour,
            minute=start_time.minute,
            second=0,
            microsecond=0
        )
        next_start = next_start.replace(day=next_start.day + 1)
        
        return "asian", next_start
    
    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed"""
        session_info = self.get_current_session_info()
        return session_info["session_type"] not in ["OFF", "FORCED_CLOSE"]
    
    def get_session_display_name(self, session_type: str) -> str:
        """Get human-readable session name"""
        display_names = {
            "NY_AM": "New York AM",
            "PM": "PM Session", 
            "ASIAN": "Asian Session",
            "OFF": "Off Hours",
            "FORCED_CLOSE": "Forced Close"
        }
        return display_names.get(session_type, session_type)

# Global instance
session_manager = SessionManager()

# Convenience functions
def get_current_session_info() -> Dict:
    """Get current session information"""
    return session_manager.get_current_session_info()

def check_for_forced_close() -> Optional[str]:
    """Check if forced close is needed"""
    return session_manager.check_for_forced_close(session_manager.get_current_utc_time())

def is_trading_allowed() -> bool:
    """Check if trading is currently allowed"""
    return session_manager.is_trading_allowed()

def get_next_session_start() -> Tuple[str, datetime]:
    """Get next session start time"""
    return session_manager.get_next_session_start()

def get_current_session_name() -> str:
    """Get current session name (lowercase) for hourly limiter"""
    return session_manager.get_current_session_name()
