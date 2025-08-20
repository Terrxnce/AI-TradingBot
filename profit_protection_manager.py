# ------------------------------------------------------------------------------------
# 🛡️ profit_protection_manager.py — D.E.V.I Profit Protection System
#
# Unified system for:
# 1. Trailing stop activation after 30 minutes in profit (ATR-based)
# 2. +1% floating PnL → Partial close + Breakeven + Lot reset
# 3. +2% floating PnL → Full close (if new trade since partial)
# 4. -0.5% drawdown blocking
# 5. Session cycle reset logic
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import os
import sys
import json
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from pathlib import Path

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import PROTECTION_CONFIG, FTMO_PARAMS

# State file for persistent protection state
PROTECTION_STATE_FILE = "protection_state.json"

class ProtectionManager:
    """Unified profit protection system for D.E.V.I"""
    
    def __init__(self):
        self.state_file = Path(PROTECTION_STATE_FILE)
        self.state = self.load_state()
    
    def load_state(self):
        """Load persistent protection state"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load protection state: {e}")
        
        # Default state
        return {
            "session_baseline_equity": 10000.00,
            "partial_done": False,
            "full_done": False,
            "new_trade_since_partial": False,
            "blocked_for_drawdown": False,
            "lot_reset_after_partial": False,
            "last_reset_ts": datetime.now().isoformat(),
            "trailing_positions": {}  # Track which positions have trailing applied
        }
    
    def save_state(self):
        """Save protection state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save protection state: {e}")
    
    def get_account_equity(self):
        """Get current account equity"""
        account = mt5.account_info()
        return account.equity if account else 0.0
    
    def get_floating_pnl(self):
        """Get current floating P&L"""
        positions = mt5.positions_get()
        if not positions:
            return 0.0
        return sum(pos.profit for pos in positions)
    
    def get_floating_equity_pct(self):
        """Get floating equity percentage vs baseline"""
        current_equity = self.get_account_equity()
        baseline = self.state["session_baseline_equity"]
        if baseline <= 0:
            return 0.0
        return ((current_equity - baseline) / baseline) * 100
    
    def update_session_baseline(self):
        """Update session baseline on first trade"""
        if not self.has_open_positions():
            self.state["session_baseline_equity"] = self.get_account_equity()
            self.save_state()
            print(f"📊 Session baseline updated: ${self.state['session_baseline_equity']:.2f}")
    
    def has_open_positions(self):
        """Check if there are any open positions"""
        positions = mt5.positions_get()
        return bool(positions)
    
    def get_profitable_positions(self):
        """Get list of profitable positions"""
        positions = mt5.positions_get()
        if not positions:
            return []
        return [pos for pos in positions if pos.profit > 0]
    
    def should_reset_cycle(self):
        """Check if protection cycle should reset"""
        # Reset conditions:
        # 1. No open trades AND floating PnL within ±0.1% of baseline
        # 2. Session end time reached
        
        if self.has_open_positions():
            return False
        
        floating_pct = self.get_floating_equity_pct()
        epsilon = PROTECTION_CONFIG["cycle_epsilon_pct"]
        
        if abs(floating_pct) <= epsilon:
            return True
        
        # Check session end time
        now = datetime.now()
        session_end = PROTECTION_CONFIG["session_end_utc"]
        try:
            end_hour, end_min = map(int, session_end.split(':'))
            end_time = now.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
            if now >= end_time:
                return True
        except:
            pass
        
        return False
    
    def reset_protection_cycle(self):
        """Reset all protection flags for new cycle"""
        self.state.update({
            "partial_done": False,
            "full_done": False,
            "new_trade_since_partial": False,
            "blocked_for_drawdown": False,
            "lot_reset_after_partial": False,
            "last_reset_ts": datetime.now().isoformat(),
            "trailing_positions": {}
        })
        self.update_session_baseline()
        self.save_state()
        print("🔄 Protection cycle reset - new session started")
    
    def check_drawdown_block(self):
        """Check if trades should be blocked due to drawdown"""
        floating_pct = self.get_floating_equity_pct()
        drawdown_threshold = PROTECTION_CONFIG["drawdown_block_pct"]
        unblock_threshold = PROTECTION_CONFIG["unblock_threshold_pct"]
        
        if floating_pct <= drawdown_threshold:
            if not self.state["blocked_for_drawdown"]:
                self.state["blocked_for_drawdown"] = True
                self.save_state()
                print(f"🚫 Drawdown block activated: {floating_pct:.2f}% ≤ {drawdown_threshold:.2f}%")
            return True
        elif floating_pct >= unblock_threshold and self.state["blocked_for_drawdown"]:
            self.state["blocked_for_drawdown"] = False
            self.save_state()
            print(f"✅ Drawdown block removed: {floating_pct:.2f}% ≥ {unblock_threshold:.2f}%")
            return False
        
        return self.state["blocked_for_drawdown"]
    
    def calculate_atr_trailing_distance(self, symbol, candles_df=None):
        """Calculate ATR-based trailing distance"""
        if not PROTECTION_CONFIG["trail_use_atr"] or candles_df is None:
            # Fallback to fixed pips
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                point = symbol_info.point
                pips = PROTECTION_CONFIG["trail_fixed_pips"]
                return pips * point * 10  # Convert pips to price units
            return 0.001  # Default fallback
        
        try:
            import pandas as pd
            import numpy as np
            
            # Calculate ATR
            period = PROTECTION_CONFIG["trail_atr_period"]
            multiplier = PROTECTION_CONFIG["trail_atr_mult"]
            
            if len(candles_df) < period:
                return None
            
            # Calculate True Range
            candles_df['tr1'] = candles_df['high'] - candles_df['low']
            candles_df['tr2'] = abs(candles_df['high'] - candles_df['close'].shift(1))
            candles_df['tr3'] = abs(candles_df['low'] - candles_df['close'].shift(1))
            candles_df['tr'] = candles_df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # Calculate ATR
            atr = candles_df['tr'].rolling(window=period).mean().iloc[-1]
            
            return atr * multiplier
            
        except Exception as e:
            print(f"⚠️ ATR calculation failed for {symbol}: {e}")
            return None
    
    def apply_trailing_stops(self, candles_data=None):
        """Apply trailing stops to eligible positions"""
        if not mt5.terminal_info():
            return
        
        positions = mt5.positions_get()
        if not positions:
            return
        
        current_time = datetime.now()
        activate_seconds = PROTECTION_CONFIG["trailing_activate_seconds"]
        
        for pos in positions:
            # Only trail profitable positions
            if pos.profit <= 0:
                continue
            
            # Check if position is old enough for trailing
            open_time = datetime.fromtimestamp(pos.time)
            time_in_trade = (current_time - open_time).total_seconds()
            
            if time_in_trade < activate_seconds:
                continue
            
            # Check if already applied trailing to this position
            ticket_str = str(pos.ticket)
            if ticket_str in self.state["trailing_positions"]:
                continue
            
            # Calculate trailing distance
            symbol_candles = candles_data.get(pos.symbol) if candles_data else None
            trail_distance = self.calculate_atr_trailing_distance(pos.symbol, symbol_candles)
            
            if trail_distance is None:
                continue
            
            # Calculate new stop loss
            symbol_info = mt5.symbol_info(pos.symbol)
            if not symbol_info:
                continue
            
            current_sl = pos.sl if pos.sl else 0
            current_price = pos.price_current
            
            if pos.type == mt5.ORDER_TYPE_BUY:
                new_sl = current_price - trail_distance
                # Only improve SL (move closer to current price)
                if current_sl == 0 or new_sl > current_sl:
                    pass  # Good to update
                else:
                    continue
            elif pos.type == mt5.ORDER_TYPE_SELL:
                new_sl = current_price + trail_distance
                # Only improve SL (move closer to current price)
                if current_sl == 0 or new_sl < current_sl:
                    pass  # Good to update
                else:
                    continue
            else:
                continue
            
            # Apply trailing stop
            new_sl = round(new_sl, symbol_info.digits)
            
            result = mt5.order_send({
                "action": mt5.TRADE_ACTION_SLTP,
                "position": pos.ticket,
                "sl": new_sl,
                "tp": pos.tp,
                "symbol": pos.symbol,
            })
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"🔄 Trailing SL applied to {pos.symbol} #{pos.ticket}: {new_sl}")
                self.state["trailing_positions"][ticket_str] = {
                    "applied_at": current_time.isoformat(),
                    "reason": "30min_profit"
                }
                self.save_state()
            else:
                print(f"❌ Failed to apply trailing SL to {pos.symbol}: {result.comment}")
    
    def partial_close_positions(self):
        """Close 50% of all profitable positions and set breakeven"""
        profitable_positions = self.get_profitable_positions()
        if not profitable_positions:
            return False
        
        success_count = 0
        
        for pos in profitable_positions:
            try:
                # Calculate 50% lot size
                half_lot = round(pos.volume / 2, 2)
                if half_lot < 0.01:  # Minimum lot size
                    half_lot = pos.volume  # Close entire position if too small
                
                # Close 50%
                result = mt5.order_send({
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": pos.symbol,
                    "volume": half_lot,
                    "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                    "position": pos.ticket,
                    "comment": "Partial close +1%"
                })
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ Partial close {pos.symbol}: {half_lot} lots")
                    
                    # Set remaining position to breakeven
                    self.set_breakeven(pos)
                    success_count += 1
                else:
                    print(f"❌ Failed partial close {pos.symbol}: {result.comment}")
                    
            except Exception as e:
                print(f"❌ Error in partial close {pos.symbol}: {e}")
        
        return success_count > 0
    
    def set_breakeven(self, position):
        """Set position to breakeven with safety buffer"""
        symbol_info = mt5.symbol_info(position.symbol)
        if not symbol_info:
            return False
        
        # Calculate breakeven with tick safety
        safety_ticks = PROTECTION_CONFIG["breakeven_tick_safety"]
        tick_size = symbol_info.trade_tick_size
        
        if position.type == mt5.ORDER_TYPE_BUY:
            breakeven_sl = position.price_open + (safety_ticks * tick_size)
        else:
            breakeven_sl = position.price_open - (safety_ticks * tick_size)
        
        breakeven_sl = round(breakeven_sl, symbol_info.digits)
        
        result = mt5.order_send({
            "action": mt5.TRADE_ACTION_SLTP,
            "position": position.ticket,
            "sl": breakeven_sl,
            "tp": position.tp,
            "symbol": position.symbol,
        })
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"🛡️ Breakeven set for {position.symbol}: {breakeven_sl}")
            return True
        else:
            print(f"❌ Failed breakeven for {position.symbol}: {result.comment}")
            return False
    
    def close_all_profitable_positions(self):
        """Close all profitable positions"""
        profitable_positions = self.get_profitable_positions()
        if not profitable_positions:
            return False
        
        success_count = 0
        
        for pos in profitable_positions:
            try:
                result = mt5.order_send({
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": pos.symbol,
                    "volume": pos.volume,
                    "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                    "position": pos.ticket,
                    "comment": "Full close +2%"
                })
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ Full close {pos.symbol}: {pos.volume} lots")
                    success_count += 1
                else:
                    print(f"❌ Failed full close {pos.symbol}: {result.comment}")
                    
            except Exception as e:
                print(f"❌ Error in full close {pos.symbol}: {e}")
        
        return success_count > 0
    
    def check_equity_triggers(self):
        """Check and handle equity-based triggers"""
        floating_pct = self.get_floating_equity_pct()
        
        partial_threshold = PROTECTION_CONFIG["equity_partial_pct"]
        full_threshold = PROTECTION_CONFIG["equity_full_pct"]
        
        # Check +1% partial trigger
        if (floating_pct >= partial_threshold and 
            not self.state["partial_done"] and 
            self.has_open_positions()):
            
            print(f"🎯 +1% equity trigger: {floating_pct:.2f}% ≥ {partial_threshold:.2f}%")
            
            if self.partial_close_positions():
                self.state["partial_done"] = True
                self.state["lot_reset_after_partial"] = True
                self.state["new_trade_since_partial"] = False
                self.save_state()
                print("📊 Partial close completed - lot sizes reset for future trades")
        
        # Check +2% full trigger (only if partial done and new trade since)
        if (floating_pct >= full_threshold and 
            self.state["partial_done"] and 
            self.state["new_trade_since_partial"] and 
            not self.state["full_done"] and 
            self.has_open_positions()):
            
            print(f"🎯 +2% equity trigger: {floating_pct:.2f}% ≥ {full_threshold:.2f}%")
            
            if self.close_all_profitable_positions():
                self.state["full_done"] = True
                self.save_state()
                print("📊 Full close completed - continuing normal trading")
    
    def mark_new_trade_opened(self):
        """Mark that a new trade was opened (for tracking after partial)"""
        if self.state["partial_done"] and not self.state["new_trade_since_partial"]:
            self.state["new_trade_since_partial"] = True
            self.save_state()
            print("📈 New trade opened after partial close - enabling +2% trigger")
    
    def get_lot_size_multiplier(self):
        """Get lot size multiplier (1.0 = normal, reset to default after partial)"""
        if self.state["lot_reset_after_partial"] and not self.state["full_done"]:
            return 1.0  # Use default lot sizes after partial close
        return 1.0  # Normal operation
    
    def run_protection_cycle(self, candles_data=None):
        """Main protection cycle - call this regularly from bot loop"""
        try:
            # Check if cycle should reset
            if self.should_reset_cycle():
                self.reset_protection_cycle()
                return
            
            # Update baseline on first trade of session
            if not self.has_open_positions() and not self.state.get("baseline_set", False):
                self.update_session_baseline()
                self.state["baseline_set"] = True
                self.save_state()
            
            # Check drawdown blocking
            if self.check_drawdown_block():
                return {"action": "block_trades", "reason": "drawdown"}
            
            # Apply trailing stops
            self.apply_trailing_stops(candles_data)
            
            # Check equity triggers
            self.check_equity_triggers()
            
            return {"action": "continue", "lot_multiplier": self.get_lot_size_multiplier()}
            
        except Exception as e:
            print(f"❌ Error in protection cycle: {e}")
            return {"action": "continue", "lot_multiplier": 1.0}

# Global instance
protection_manager = ProtectionManager()

# Convenience functions for external use
def run_protection_cycle(candles_data=None):
    """Run the main protection cycle"""
    return protection_manager.run_protection_cycle(candles_data)

def mark_new_trade_opened():
    """Mark that a new trade was opened"""
    protection_manager.mark_new_trade_opened()

def is_drawdown_blocked():
    """Check if trading is blocked due to drawdown"""
    return protection_manager.state["blocked_for_drawdown"]

def get_protection_status():
    """Get current protection status for monitoring"""
    equity_pct = protection_manager.get_floating_equity_pct()
    return {
        "floating_equity_pct": equity_pct,
        "partial_done": protection_manager.state["partial_done"],
        "full_done": protection_manager.state["full_done"],
        "new_trade_since_partial": protection_manager.state["new_trade_since_partial"],
        "blocked_for_drawdown": protection_manager.state["blocked_for_drawdown"],
        "session_baseline": protection_manager.state["session_baseline_equity"]
    }
