# ------------------------------------------------------------------------------------
# 🎯 lot_size_manager.py — Comprehensive Lot Size Management
#
# Handles all lot size calculations with:
# - Symbol-specific volume step validation
# - PM session multiplier (0.5x)
# - Risk guard multipliers
# - Proper rounding and clamping
# - Deterministic calculation order
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import MetaTrader5 as mt5
from datetime import datetime
from typing import Dict, Optional, Tuple
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
from config import CONFIG

class LotSizeManager:
    """Comprehensive lot size management with validation and PM session support"""
    
    def __init__(self):
        self._symbol_cache = {}  # Cache symbol info for performance
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get and cache symbol information"""
        if symbol not in self._symbol_cache:
            info = mt5.symbol_info(symbol)
            if info:
                self._symbol_cache[symbol] = {
                    'volume_step': info.volume_step,
                    'volume_min': info.volume_min,
                    'volume_max': info.volume_max,
                    'digits': info.digits
                }
            else:
                self._symbol_cache[symbol] = None
        
        return self._symbol_cache[symbol]
    
    def is_pm_session(self) -> bool:
        """Check if current time is within PM session window - DEPRECATED"""
        # This function is deprecated - use session_manager instead
        return False
    
    def get_session_multiplier(self) -> float:
        """Get current session multiplier - DEPRECATED"""
        # This function is deprecated - use session_manager instead
        return 1.0
    
    def round_to_step(self, lot: float, volume_step: float) -> float:
        """Round lot size to valid volume step"""
        if volume_step <= 0:
            return lot
        
        # Round to nearest step
        rounded = round(lot / volume_step) * volume_step
        
        # Handle floating point precision issues
        return round(rounded, 6)
    
    def clamp_to_limits(self, lot: float, volume_min: float, volume_max: float) -> float:
        """Clamp lot size to symbol limits"""
        if lot < volume_min:
            return volume_min
        if lot > volume_max:
            return volume_max
        return lot
    
    def calculate_effective_lot_size(
        self, 
        symbol: str, 
        base_lot: float,
        risk_multiplier: float = 1.0,
        session_multiplier: float = 1.0
    ) -> Tuple[float, Dict]:
        """
        Calculate effective lot size with all multipliers and validation
        
        Args:
            symbol: Trading symbol
            base_lot: Base lot size from config
            risk_multiplier: Risk guard multiplier (default 1.0)
        
        Returns:
            Tuple of (effective_lot, calculation_details)
        """
        # Get symbol information
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            print(f"⚠️ Could not get symbol info for {symbol}, using defaults")
            # Use more appropriate defaults for stocks
            if symbol in ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX']:
                symbol_info = {
                    'volume_step': 1.0,
                    'volume_min': 1.0,
                    'volume_max': 10000.0,
                    'digits': 2
                }
            else:
                symbol_info = {
                    'volume_step': 0.01,
                    'volume_min': 0.01,
                    'volume_max': 100.0,
                    'digits': 2
                }
        
        # Step 1: Start with base lot size
        effective_lot = base_lot
        
        # Step 2: Apply session multiplier (PM: 0.5, else 1.0)
        effective_lot *= session_multiplier
        
        # Step 3: Apply risk guard multiplier
        effective_lot *= risk_multiplier
        
        # Step 4: Round to symbol volume step
        pre_rounded = effective_lot
        effective_lot = self.round_to_step(effective_lot, symbol_info['volume_step'])
        
        # Step 5: Clamp to min/max limits
        pre_clamped = effective_lot
        effective_lot = self.clamp_to_limits(
            effective_lot, 
            symbol_info['volume_min'], 
            symbol_info['volume_max']
        )
        
        # Prepare calculation details for logging
        calculation_details = {
            'base_lot': base_lot,
            'session_multiplier': session_multiplier,
            'risk_multiplier': risk_multiplier,
            'pre_rounded': pre_rounded,
            'pre_clamped': pre_clamped,
            'final_lot': effective_lot,
            'volume_step': symbol_info['volume_step'],
            'volume_min': symbol_info['volume_min'],
            'volume_max': symbol_info['volume_max'],
            'is_pm_session': session_multiplier != 1.0,
            'was_clamped': pre_clamped != effective_lot,
            'was_rounded': abs(pre_rounded - effective_lot) > 0.000001
        }
        
        return effective_lot, calculation_details
    
    def log_lot_calculation(self, symbol: str, details: Dict):
        """Log lot size calculation details"""
        session_status = "PM Session" if details['is_pm_session'] else "Normal Session"
        
        print(f"🎯 Lot Size Calculation for {symbol} ({session_status}):")
        print(f"   Base lot: {details['base_lot']}")
        print(f"   Session multiplier: {details['session_multiplier']}")
        print(f"   Risk multiplier: {details['risk_multiplier']}")
        print(f"   Pre-rounded: {details['pre_rounded']:.6f}")
        print(f"   Pre-clamped: {details['pre_clamped']:.6f}")
        print(f"   Final lot: {details['final_lot']:.6f}")
        print(f"   Volume step: {details['volume_step']}")
        print(f"   Min/Max: {details['volume_min']}/{details['volume_max']}")
        
        if details['was_rounded']:
            print(f"   ⚠️ Rounded to volume step")
        if details['was_clamped']:
            print(f"   ⚠️ Clamped to volume limits")
        
        print()

# Global instance
lot_manager = LotSizeManager()

def get_effective_lot_size(symbol: str, base_lot: float, risk_multiplier: float = 1.0, session_multiplier: float = 1.0) -> float:
    """
    Get effective lot size with all validations applied
    
    Args:
        symbol: Trading symbol
        base_lot: Base lot size from config
        risk_multiplier: Risk guard multiplier (default 1.0)
    
    Returns:
        Validated and calculated lot size
    """
    effective_lot, details = lot_manager.calculate_effective_lot_size(symbol, base_lot, risk_multiplier, session_multiplier)
    lot_manager.log_lot_calculation(symbol, details)
    return effective_lot

def is_pm_session() -> bool:
    """Check if currently in PM session"""
    return lot_manager.is_pm_session()

def get_session_multiplier() -> float:
    """Get current session multiplier"""
    return lot_manager.get_session_multiplier()
