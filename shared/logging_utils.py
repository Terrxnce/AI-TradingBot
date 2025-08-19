#!/usr/bin/env python3
"""
Centralized logging utilities for the AI Trading Bot
Provides consistent logging format and configuration across all modules
"""

import logging
import os
from datetime import datetime
from typing import Optional

# Global logger instance
_logger = None

def setup_logger(
    name: str = "ai_trading_bot",
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    Setup and configure the main logger for the trading bot
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        console_output: Whether to output to console
    
    Returns:
        Configured logger instance
    """
    global _logger
    
    if _logger is not None:
        return _logger
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    _logger = logger
    return logger

def get_logger(name: str = "ai_trading_bot") -> logging.Logger:
    """
    Get the configured logger instance
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    global _logger
    
    if _logger is None:
        # Setup default logger
        setup_logger(name)
    
    return _logger

def log_trade_decision(
    symbol: str,
    decision: str,
    score: float,
    ai_confidence: float,
    session: str,
    logger: Optional[logging.Logger] = None
):
    """Log trade decision with consistent format"""
    if logger is None:
        logger = get_logger()
    
    logger.info(
        f"📊 Trade Decision | Symbol: {symbol} | Decision: {decision} | "
        f"Score: {score:.2f} | AI Confidence: {ai_confidence:.2f} | Session: {session}"
    )

def log_trade_execution(
    symbol: str,
    action: str,
    lot_size: float,
    sl: float,
    tp: float,
    rrr: float,
    logger: Optional[logging.Logger] = None
):
    """Log trade execution with consistent format"""
    if logger is None:
        logger = get_logger()
    
    logger.info(
        f"🚀 Trade Executed | Symbol: {symbol} | Action: {action} | "
        f"Lot: {lot_size} | SL: {sl:.5f} | TP: {tp:.5f} | RRR: {rrr:.3f}"
    )

def log_error(
    error: Exception,
    context: str = "",
    logger: Optional[logging.Logger] = None
):
    """Log errors with consistent format"""
    if logger is None:
        logger = get_logger()
    
    error_msg = f"❌ Error in {context}: {type(error).__name__}: {str(error)}"
    logger.error(error_msg)

def log_warning(
    message: str,
    context: str = "",
    logger: Optional[logging.Logger] = None
):
    """Log warnings with consistent format"""
    if logger is None:
        logger = get_logger()
    
    warning_msg = f"⚠️ Warning in {context}: {message}"
    logger.warning(warning_msg)

def log_success(
    message: str,
    context: str = "",
    logger: Optional[logging.Logger] = None
):
    """Log success messages with consistent format"""
    if logger is None:
        logger = get_logger()
    
    success_msg = f"✅ Success in {context}: {message}"
    logger.info(success_msg)

def log_info(
    message: str,
    context: str = "",
    logger: Optional[logging.Logger] = None
):
    """Log info messages with consistent format"""
    if logger is None:
        logger = get_logger()
    
    info_msg = f"ℹ️ Info in {context}: {message}"
    logger.info(info_msg)

# Initialize default logger
setup_logger()
