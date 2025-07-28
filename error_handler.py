#!/usr/bin/env python3
"""
Enhanced Error Handling for AI Trading Bot
"""

import MetaTrader5 as mt5
import time
import logging
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('error_log.txt', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class MT5ErrorHandler:
    def __init__(self, max_retries=3, retry_delay=5):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection_attempts = 0
        self.last_connection_time = None
        
    def robust_mt5_initialize(self):
        """Robust MT5 initialization with retry logic"""
        for attempt in range(self.max_retries):
            try:
                if mt5.initialize():
                    self.connection_attempts = 0
                    self.last_connection_time = datetime.now()
                    logging.info("✅ MT5 initialized successfully")
                    return True
                else:
                    error = mt5.last_error()
                    logging.error(f"❌ MT5 initialization failed (attempt {attempt + 1}): {error}")
                    
            except Exception as e:
                logging.error(f"❌ MT5 initialization exception (attempt {attempt + 1}): {e}")
            
            if attempt < self.max_retries - 1:
                logging.info(f"🔄 Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
                self.retry_delay *= 2  # Exponential backoff
        
        logging.critical("❌ MT5 initialization failed after all retries")
        return False
    
    def check_mt5_connection(self):
        """Check if MT5 connection is healthy"""
        try:
            if not mt5.terminal_info():
                logging.warning("⚠️ MT5 terminal info unavailable")
                return False
            
            if not mt5.version():
                logging.warning("⚠️ MT5 version info unavailable")
                return False
            
            # Test account info access
            account = mt5.account_info()
            if account is None:
                logging.warning("⚠️ MT5 account info unavailable")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"❌ MT5 connection check failed: {e}")
            return False
    
    def reconnect_mt5(self):
        """Reconnect to MT5 with proper cleanup"""
        try:
            logging.info("🔄 Attempting MT5 reconnection...")
            mt5.shutdown()
            time.sleep(2)
            return self.robust_mt5_initialize()
        except Exception as e:
            logging.error(f"❌ MT5 reconnection failed: {e}")
            return False

class DataValidator:
    def __init__(self):
        self.last_validation_time = None
        
    def validate_price_data(self, candles_df):
        """Validate price data for anomalies"""
        try:
            if candles_df.empty:
                logging.error("❌ Empty price data received")
                return False
            
            # Check for missing values
            if candles_df.isnull().any().any():
                logging.warning("⚠️ Price data contains missing values")
                return False
            
            # Check for price anomalies (gaps, extreme values)
            for col in ['open', 'high', 'low', 'close']:
                if col in candles_df.columns:
                    # Check for negative prices
                    if (candles_df[col] <= 0).any():
                        logging.error(f"❌ Negative prices found in {col}")
                        return False
                    
                    # Check for extreme price changes (>50% in one candle)
                    if col == 'close' and len(candles_df) > 1:
                        price_changes = candles_df[col].pct_change().abs()
                        if (price_changes > 0.5).any():
                            logging.warning(f"⚠️ Extreme price change detected: {price_changes.max():.2%}")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Price data validation failed: {e}")
            return False
    
    def validate_pnl_data(self, pnl_value):
        """Validate PnL data"""
        try:
            if pnl_value is None:
                logging.error("❌ PnL value is None")
                return False
            
            # Check for extreme PnL values (more than 100% of balance)
            if abs(pnl_value) > 10000:  # Assuming $10k balance
                logging.warning(f"⚠️ Extreme PnL value detected: ${pnl_value:.2f}")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ PnL validation failed: {e}")
            return False

class PerformanceMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.errors = []
        self.warnings = []
        
    def log_error(self, error_msg, context=""):
        """Log an error with context"""
        error_entry = {
            'timestamp': datetime.now(),
            'error': error_msg,
            'context': context
        }
        self.errors.append(error_entry)
        logging.error(f"❌ {error_msg} | Context: {context}")
    
    def log_warning(self, warning_msg, context=""):
        """Log a warning with context"""
        warning_entry = {
            'timestamp': datetime.now(),
            'warning': warning_msg,
            'context': context
        }
        self.warnings.append(warning_entry)
        logging.warning(f"⚠️ {warning_msg} | Context: {context}")
    
    def get_error_summary(self):
        """Get summary of errors and warnings"""
        return {
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'uptime': datetime.now() - self.start_time,
            'recent_errors': self.errors[-10:] if self.errors else [],
            'recent_warnings': self.warnings[-10:] if self.warnings else []
        }

# Global instances
mt5_handler = MT5ErrorHandler()
data_validator = DataValidator()
performance_monitor = PerformanceMonitor()

def safe_mt5_operation(operation_func, *args, **kwargs):
    """Safely execute MT5 operations with error handling"""
    try:
        # Check connection first
        if not mt5_handler.check_mt5_connection():
            logging.warning("⚠️ MT5 connection unhealthy, attempting reconnection...")
            if not mt5_handler.reconnect_mt5():
                performance_monitor.log_error("MT5 reconnection failed", "safe_mt5_operation")
                return None
        
        # Execute operation
        result = operation_func(*args, **kwargs)
        
        # Validate result if it's price data
        if hasattr(result, 'shape') and hasattr(result, 'columns'):  # DataFrame
            if not data_validator.validate_price_data(result):
                performance_monitor.log_error("Price data validation failed", "safe_mt5_operation")
                return None
        
        return result
        
    except Exception as e:
        performance_monitor.log_error(f"MT5 operation failed: {e}", "safe_mt5_operation")
        return None

def validate_trade_parameters(symbol, lot_size, sl, tp):
    """Validate trade parameters before execution"""
    try:
        # Validate symbol
        if not symbol or not isinstance(symbol, str):
            performance_monitor.log_error("Invalid symbol", "validate_trade_parameters")
            return False
        
        # Validate lot size
        if lot_size <= 0 or lot_size > 100:
            performance_monitor.log_error(f"Invalid lot size: {lot_size}", "validate_trade_parameters")
            return False
        
        # Validate SL/TP
        if sl is not None and sl <= 0:
            performance_monitor.log_error(f"Invalid stop loss: {sl}", "validate_trade_parameters")
            return False
        
        if tp is not None and tp <= 0:
            performance_monitor.log_error(f"Invalid take profit: {tp}", "validate_trade_parameters")
            return False
        
        return True
        
    except Exception as e:
        performance_monitor.log_error(f"Trade parameter validation failed: {e}", "validate_trade_parameters")
        return False 