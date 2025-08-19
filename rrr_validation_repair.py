# ------------------------------------------------------------------------------------
# 🛡️ rrr_validation_repair.py – RRR Validation & Repair System
#
# This module ensures all trades meet minimum risk-reward ratio requirements
# before execution. It can repair trades by adjusting SL/TP or cancel them.
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I - Structure-Aware Trading Bot
# ------------------------------------------------------------------------------------

import sys
import os
import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd
import numpy as np

# Add paths for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))

try:
    from config import CONFIG
except ImportError:
    print("⚠️ Could not import config, using default RRR settings")
    CONFIG = {
        "RRR_VALIDATION": {
            "MIN_RRR": 1.50,
            "MAX_SL_ATR": 2.5,
            "MIN_TP_PIPS": 15,
            "MAX_TP_PIPS": 500,
            "ALLOW_ATR_FALLBACK": True,
            "ENABLE_REPAIR": True,
            "LOG_REPAIRS": True
        }
    }

class RRRValidator:
    """RRR Validation and Repair System"""
    
    def __init__(self):
        self.config = CONFIG.get("sltp_system", {})
        self.min_rrr = self.config.get("min_rrr", 1.50)
        self.max_sl_atr = self.config.get("max_sl_atr", 2.5)
        self.min_tp_pips = self.config.get("min_tp_pips", 15)
        self.max_tp_pips = self.config.get("max_tp_pips", 500)
        self.allow_atr_fallback = self.config.get("allow_atr_fallback", True)
        self.enable_repair = self.config.get("enable_repair", True)
        self.log_repairs = self.config.get("log_repairs", True)
    
    def calculate_rrr(self, entry_price, sl_price, tp_price, direction):
        """Calculate risk-reward ratio"""
        if direction == "BUY":
            sl_distance = entry_price - sl_price
            tp_distance = tp_price - entry_price
        else:  # SELL
            sl_distance = sl_price - entry_price
            tp_distance = entry_price - tp_price
        
        if sl_distance <= 0:
            return 0.0
        
        return tp_distance / sl_distance
    
    def get_pip_size(self, symbol):
        """Get pip size for symbol"""
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return 0.0001  # Default for most pairs
            
            # JPY pairs have different pip size
            if "JPY" in symbol:
                return 0.01
            else:
                return 0.0001
        except:
            return 0.0001
    
    def price_to_pips(self, price_distance, symbol):
        """Convert price distance to pips"""
        pip_size = self.get_pip_size(symbol)
        return price_distance / pip_size
    
    def pips_to_price(self, pips, symbol):
        """Convert pips to price distance"""
        pip_size = self.get_pip_size(symbol)
        return pips * pip_size
    
    def get_broker_min_stop_distance(self, symbol):
        """Get broker minimum stop distance"""
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return 0.0010  # Default 10 pips
            
            # Convert points to price
            point = info.point
            min_stop_level = info.trade_stops_level
            
            return min_stop_level * point
        except:
            return 0.0010  # Default fallback
    
    def validate_and_repair_rrr(self, entry_price, sl_price, tp_price, direction, 
                               atr_value, symbol, structural_targets=None, structural_stops=None):
        """
        Validate and repair RRR if needed
        
        Args:
            entry_price (float): Entry price
            sl_price (float): Stop loss price
            tp_price (float): Take profit price
            direction (str): "BUY" or "SELL"
            atr_value (float): ATR value for validation
            symbol (str): Trading symbol
            structural_targets (list): List of structural TP targets
            structural_stops (list): List of structural SL levels
            
        Returns:
            tuple: (final_sl, final_tp, final_rrr) if valid, None if should cancel
        """
        
        # Initialize repair tracking
        repairs_made = []
        original_sl = sl_price
        original_tp = tp_price
        
        # Calculate initial RRR
        initial_rrr = self.calculate_rrr(entry_price, sl_price, tp_price, direction)
        
        if self.log_repairs:
            print(f"🛡️ RRR Validation: Initial RRR = {initial_rrr:.3f} (min {self.min_rrr})")
        
        # Check if RRR already meets minimum
        if initial_rrr >= self.min_rrr:
            if self.log_repairs:
                print(f"✅ RRR Validation: Passed - {initial_rrr:.3f} >= {self.min_rrr}")
            return sl_price, tp_price, initial_rrr
        
        # RRR is below minimum, attempt repair
        if not self.enable_repair:
            if self.log_repairs:
                print(f"❌ RRR Validation: Failed - {initial_rrr:.3f} < {self.min_rrr} (repair disabled)")
            return None
        
        if self.log_repairs:
            print(f"🔧 RRR Repair: Attempting to repair RRR from {initial_rrr:.3f} to >= {self.min_rrr}")
        
        # Get broker constraints
        broker_min_stop = self.get_broker_min_stop_distance(symbol)
        max_sl_distance = atr_value * self.max_sl_atr
        
        # Repair sequence: 1. Tighten SL, 2. Extend TP, 3. ATR fallback
        
        # Step 1: Try to tighten SL using structural stops
        if structural_stops:
            new_sl = self._try_tighten_sl(entry_price, sl_price, direction, 
                                        structural_stops, broker_min_stop, max_sl_distance)
            if new_sl != sl_price:
                sl_price = new_sl
                repairs_made.append(f"tightened SL from {original_sl:.5f} to {sl_price:.5f}")
                
                # Recalculate RRR
                current_rrr = self.calculate_rrr(entry_price, sl_price, tp_price, direction)
                if current_rrr >= self.min_rrr:
                    if self.log_repairs:
                        self._log_repair_success(repairs_made, current_rrr)
                    return sl_price, tp_price, current_rrr
        
        # Step 2: Try to extend TP using structural targets
        if structural_targets:
            new_tp = self._try_extend_tp(entry_price, tp_price, direction,
                                       structural_targets, symbol)
            if new_tp != tp_price:
                tp_price = new_tp
                repairs_made.append(f"extended TP from {original_tp:.5f} to {tp_price:.5f}")
                
                # Recalculate RRR
                current_rrr = self.calculate_rrr(entry_price, sl_price, tp_price, direction)
                if current_rrr >= self.min_rrr:
                    if self.log_repairs:
                        self._log_repair_success(repairs_made, current_rrr)
                    return sl_price, tp_price, current_rrr
        
        # Step 3: ATR fallback TP (last resort)
        if self.allow_atr_fallback:
            new_tp = self._calculate_atr_fallback_tp(entry_price, sl_price, direction, 
                                                   atr_value, symbol)
            if new_tp != tp_price:
                tp_price = new_tp
                repairs_made.append(f"ATR fallback TP from {original_tp:.5f} to {tp_price:.5f}")
                
                # Recalculate RRR
                current_rrr = self.calculate_rrr(entry_price, sl_price, tp_price, direction)
                if current_rrr >= self.min_rrr:
                    if self.log_repairs:
                        self._log_repair_success(repairs_made, current_rrr)
                    return sl_price, tp_price, current_rrr
        
        # Step 4: Force minimum RRR TP (final attempt)
        forced_tp = self._force_minimum_rrr_tp(entry_price, sl_price, direction, symbol)
        if forced_tp:
            tp_price = forced_tp
            repairs_made.append(f"forced minimum RRR TP to {tp_price:.5f}")
            
            # Final RRR check
            final_rrr = self.calculate_rrr(entry_price, sl_price, tp_price, direction)
            if final_rrr >= self.min_rrr:
                if self.log_repairs:
                    self._log_repair_success(repairs_made, final_rrr)
                return sl_price, tp_price, final_rrr
        
        # All repair attempts failed
        if self.log_repairs:
            print(f"❌ RRR Validation: Failed - Could not achieve minimum RRR {self.min_rrr}")
            print(f"   Final RRR: {self.calculate_rrr(entry_price, sl_price, tp_price, direction):.3f}")
            print(f"   Trade canceled: insufficient risk-reward")
        
        return None
    
    def _try_tighten_sl(self, entry_price, current_sl, direction, structural_stops, 
                       broker_min_stop, max_sl_distance):
        """Try to tighten SL using structural stops"""
        if not structural_stops:
            return current_sl
        
        # Sort structural stops by distance from entry (closest first)
        if direction == "BUY":
            # For BUY, we want SL below entry
            valid_stops = [s for s in structural_stops if s < entry_price]
            valid_stops.sort(reverse=True)  # Closest to entry first
        else:
            # For SELL, we want SL above entry
            valid_stops = [s for s in structural_stops if s > entry_price]
            valid_stops.sort()  # Closest to entry first
        
        for stop_level in valid_stops:
            # Check if this stop is tighter than current
            if direction == "BUY" and stop_level > current_sl:
                # Check constraints
                sl_distance = entry_price - stop_level
                if sl_distance >= broker_min_stop and sl_distance <= max_sl_distance:
                    return stop_level
            elif direction == "SELL" and stop_level < current_sl:
                # Check constraints
                sl_distance = stop_level - entry_price
                if sl_distance >= broker_min_stop and sl_distance <= max_sl_distance:
                    return stop_level
        
        return current_sl
    
    def _try_extend_tp(self, entry_price, current_tp, direction, structural_targets, symbol):
        """Try to extend TP using structural targets"""
        if not structural_targets:
            return current_tp
        
        # Sort structural targets by distance from entry (furthest first for better RRR)
        if direction == "BUY":
            # For BUY, we want TP above entry
            valid_targets = [t for t in structural_targets if t > entry_price]
            valid_targets.sort()  # Furthest from entry first
        else:
            # For SELL, we want TP below entry
            valid_targets = [t for t in structural_targets if t < entry_price]
            valid_targets.sort(reverse=True)  # Furthest from entry first
        
        for target in valid_targets:
            # Check if this target is further than current
            if direction == "BUY" and target > current_tp:
                tp_distance_pips = self.price_to_pips(target - entry_price, symbol)
                if self.min_tp_pips <= tp_distance_pips <= self.max_tp_pips:
                    return target
            elif direction == "SELL" and target < current_tp:
                tp_distance_pips = self.price_to_pips(entry_price - target, symbol)
                if self.min_tp_pips <= tp_distance_pips <= self.max_tp_pips:
                    return target
        
        return current_tp
    
    def _calculate_atr_fallback_tp(self, entry_price, sl_price, direction, atr_value, symbol):
        """Calculate ATR-based fallback TP"""
        # Calculate SL distance
        if direction == "BUY":
            sl_distance = entry_price - sl_price
        else:
            sl_distance = sl_price - entry_price
        
        # Calculate minimum TP distance needed for minimum RRR
        min_tp_distance = sl_distance * self.min_rrr
        
        # Convert to pips for validation
        min_tp_pips = self.price_to_pips(min_tp_distance, symbol)
        
        # Ensure within bounds
        min_tp_pips = max(min_tp_pips, self.min_tp_pips)
        min_tp_pips = min(min_tp_pips, self.max_tp_pips)
        
        # Convert back to price
        tp_distance = self.pips_to_price(min_tp_pips, symbol)
        
        # Calculate TP price
        if direction == "BUY":
            tp_price = entry_price + tp_distance
        else:
            tp_price = entry_price - tp_distance
        
        return tp_price
    
    def _force_minimum_rrr_tp(self, entry_price, sl_price, direction, symbol):
        """Force TP to minimum RRR requirement"""
        # Calculate SL distance
        if direction == "BUY":
            sl_distance = entry_price - sl_price
        else:
            sl_distance = sl_price - entry_price
        
        # Calculate minimum TP distance needed
        min_tp_distance = sl_distance * self.min_rrr
        
        # Convert to pips for validation
        min_tp_pips = self.price_to_pips(min_tp_distance, symbol)
        
        # Check if minimum TP is within bounds
        if min_tp_pips < self.min_tp_pips:
            return None  # Cannot achieve minimum RRR within bounds
        
        if min_tp_pips > self.max_tp_pips:
            return None  # Cannot achieve minimum RRR within bounds
        
        # Calculate TP price
        if direction == "BUY":
            tp_price = entry_price + min_tp_distance
        else:
            tp_price = entry_price - min_tp_distance
        
        return tp_price
    
    def _log_repair_success(self, repairs_made, final_rrr):
        """Log successful repair"""
        print(f"✅ RRR Repair: Successfully repaired RRR to {final_rrr:.3f}")
        for repair in repairs_made:
            print(f"   🔧 {repair}")
        print(f"   Final RRR: {final_rrr:.3f} (min {self.min_rrr})")

# Global instance
rrr_validator = RRRValidator()

def validate_and_repair_rrr(entry_price, sl_price, tp_price, direction, 
                           atr_value, symbol, structural_targets=None, structural_stops=None):
    """
    Convenience function to validate and repair RRR
    
    Returns:
        tuple: (final_sl, final_tp, final_rrr) if valid, None if should cancel
    """
    return rrr_validator.validate_and_repair_rrr(
        entry_price, sl_price, tp_price, direction,
        atr_value, symbol, structural_targets, structural_stops
    )

# Test function
def test_rrr_validation():
    """Test the RRR validation system"""
    print("🧪 Testing RRR Validation System...")
    
    # Test case 1: Valid RRR
    result = validate_and_repair_rrr(
        entry_price=1.0850,
        sl_price=1.0800,  # 50 pips SL
        tp_price=1.0950,  # 100 pips TP
        direction="BUY",
        atr_value=0.0010,
        symbol="EURUSD"
    )
    
    if result:
        sl, tp, rrr = result
        print(f"✅ Test 1: Valid RRR - SL: {sl:.5f}, TP: {tp:.5f}, RRR: {rrr:.3f}")
    else:
        print("❌ Test 1: Failed")
    
    # Test case 2: Invalid RRR (should repair)
    result = validate_and_repair_rrr(
        entry_price=1.0850,
        sl_price=1.0800,  # 50 pips SL
        tp_price=1.0825,  # 25 pips TP (RRR = 0.5)
        direction="BUY",
        atr_value=0.0010,
        symbol="EURUSD"
    )
    
    if result:
        sl, tp, rrr = result
        print(f"✅ Test 2: Repaired RRR - SL: {sl:.5f}, TP: {tp:.5f}, RRR: {rrr:.3f}")
    else:
        print("❌ Test 2: Could not repair RRR")

if __name__ == "__main__":
    test_rrr_validation()
