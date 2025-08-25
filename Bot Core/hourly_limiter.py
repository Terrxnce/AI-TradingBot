# ------------------------------------------------------------------------------------
# 🕐 hourly_limiter.py — Hourly Trade Rate Limiting System
#
# Enforces session-specific trade frequency limits to prevent overtrading
# and align with market liquidity/volatility conditions.
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

class HourlyLimiter:
    """Manages hourly trade limits per symbol and session"""
    
    def __init__(self, state_file: str = "hourly_trade_state.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load trade state from JSON file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading hourly trade state: {e}")
        
        return {}
    
    def _save_state(self):
        """Save trade state to JSON file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving hourly trade state: {e}")
    
    def can_trade_this_hour(self, symbol: str, session: str, config: Dict) -> bool:
        """
        Check if symbol can trade in current session based on hourly limits
        
        Args:
            symbol: Trading symbol (e.g., 'NVDA', 'AUDJPY')
            session: Session name (e.g., 'ny_am', 'pm', 'asian')
            config: HOURLY_TRADE_LIMITS configuration
            
        Returns:
            bool: True if trade is allowed, False if rate limited
        """
        # Get session configuration
        session_config = config.get(session)
        if not session_config:
            return True  # No limits for this session
        
        # Check if symbol is restricted in this session
        if symbol.upper() not in session_config["symbols"]:
            return True  # Symbol not restricted in this session
        
        # Get current time and one hour ago
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        # Get recent trades for this symbol/session
        recent_trades = self._get_recent_trades(symbol, session, one_hour_ago)
        
        # Check against limit
        max_trades = session_config["max_trades_per_hour"]
        can_trade = len(recent_trades) < max_trades
        
        if not can_trade:
            print(f"🚫 Rate-limited: {symbol} in {session} session - {len(recent_trades)}/{max_trades} trades in last hour")
        
        return can_trade
    
    def _get_recent_trades(self, symbol: str, session: str, cutoff_time: datetime) -> List[str]:
        """Get recent trade timestamps for symbol/session"""
        symbol_data = self.state.get(symbol, {})
        session_trades = symbol_data.get(session, [])
        
        recent_trades = []
        for timestamp_str in session_trades:
            try:
                trade_time = datetime.fromisoformat(timestamp_str)
                if trade_time > cutoff_time:
                    recent_trades.append(timestamp_str)
            except Exception as e:
                print(f"⚠️ Error parsing trade timestamp {timestamp_str}: {e}")
        
        return recent_trades
    
    def record_trade(self, symbol: str, session: str):
        """
        Record a trade for rate limiting purposes
        
        Args:
            symbol: Trading symbol
            session: Session name
        """
        now = datetime.utcnow().isoformat()
        
        # Initialize symbol data if needed
        if symbol not in self.state:
            self.state[symbol] = {}
        
        # Initialize session data if needed
        if session not in self.state[symbol]:
            self.state[symbol][session] = []
        
        # Add trade timestamp
        self.state[symbol][session].append(now)
        
        # Save state
        self._save_state()
        
        print(f"📝 Recorded trade: {symbol} in {session} session at {now}")
    
    def cleanup_old_timestamps(self, max_age_hours: int = 24):
        """
        Remove timestamps older than max_age_hours
        
        Args:
            max_age_hours: Maximum age in hours to keep timestamps
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        for symbol in list(self.state.keys()):
            for session in list(self.state[symbol].keys()):
                original_count = len(self.state[symbol][session])
                self.state[symbol][session] = [
                    t for t in self.state[symbol][session]
                    if datetime.fromisoformat(t) > cutoff
                ]
                cleaned_count += original_count - len(self.state[symbol][session])
        
        if cleaned_count > 0:
            self._save_state()
            print(f"🧹 Cleaned {cleaned_count} old trade timestamps")
    
    def get_trade_summary(self, symbol: str, session: str) -> Dict:
        """
        Get summary of recent trades for symbol/session
        
        Args:
            symbol: Trading symbol
            session: Session name
            
        Returns:
            Dict with trade count and recent timestamps
        """
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        recent_trades = self._get_recent_trades(symbol, session, one_hour_ago)
        
        return {
            "symbol": symbol,
            "session": session,
            "trades_last_hour": len(recent_trades),
            "recent_timestamps": recent_trades
        }
    
    def validate_session_symbol_combo(self, symbol: str, session: str, config: Dict) -> bool:
        """
        Validate if symbol is allowed in this session
        
        Args:
            symbol: Trading symbol
            session: Session name
            config: HOURLY_TRADE_LIMITS configuration
            
        Returns:
            bool: True if symbol is allowed in session
        """
        session_config = config.get(session)
        if not session_config:
            return False
        
        return symbol.upper() in session_config["symbols"]

# Global instance for easy access
hourly_limiter = HourlyLimiter()

def can_trade_this_hour(symbol: str, session: str, config: Dict) -> bool:
    """Convenience function to check if trade is allowed"""
    return hourly_limiter.can_trade_this_hour(symbol, session, config)

def record_trade(symbol: str, session: str):
    """Convenience function to record a trade"""
    hourly_limiter.record_trade(symbol, session)

def validate_session_symbol_combo(symbol: str, session: str, config: Dict) -> bool:
    """Convenience function to validate symbol/session combination"""
    return hourly_limiter.validate_session_symbol_combo(symbol, session, config)
