# ------------------------------------------------------------------------------------
# ⚙️ config.py – Global Bot Settings
#
# This file controls all configurable options used across the trading bot:
#
# ✅ min_score_for_trade – Minimum technical score required before considering AI
# ✅ sl_pips / tp_pips – Fallback SL/TP distances (used if dynamic SL/TP not supplied)
# ✅ lot_size – Default trade volume
# ✅ use_engulfing / use_bos / use_liquidity_sweep – Toggles for logic modules
# ✅ ema_trend_threshold – Minimum EMA separation by timeframe for valid trend
#
# Extend as needed with risk %, max trades per day, cooldown logic, etc.
#
# Used by: decision_engine.py, strategy_engine.py, broker_interface.py
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------


FTMO_PARAMS = {
    "initial_balance": 10_000,  # Replace with actual
    "max_daily_loss_pct": 0.05,
    "max_total_loss_pct": 0.10,
    "profit_target_pct": 0.10,
    "min_trading_days": 4
}



CONFIG = {

    "min_score_for_trade": 4.5,
    "sl_pips": 50,
    "delay_seconds": 60 * 15,  # 15 minutes
    "tp_pips": 100,
    "lot_size": 0.25,
    "LOT_SIZES": {
        "XAUUSD": 0.5,
        "US500.cash": 3.5,
        "EURUSD": 0.25,
        "GBPUSD": 0.25,
        "GER40.cash": 1.5,
    },
    "use_engulfing": True,
    "use_bos": True,
    "use_liquidity_sweep": True,
    "ema_trend_threshold": {
        "M15": 0.0003,
        "H1": 0.0005,
        "H4": 0.001,
        "D1": 0.002
    },

    "partial_close_trigger_percent": 1.0,  # 1% of balance

    "session_hours": {
    "Asia": [1,7],
    "London": [8,12],
    "New York Pre-Market": [13.5, 14],
    "New York": [14, 20],
    "Post-Market": [20, 24]
}
}




# Add any other configuration options you need here
