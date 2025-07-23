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
    "initial_balance": 10_000,
    "max_daily_loss_pct": 0.05,
    "max_total_loss_pct": 0.10,
    "profit_target_pct": 0.10,
    "min_trading_days": 4
}

CONFIG = {

    # ✅ Trade Requirements
    "min_score_for_trade": 4.5,
    "sl_pips": 50,
    "tp_pips": 100,
    "delay_seconds": 60 * 15,  # 15-minute loop

    # ✅ Symbol-Specific Lot Sizes
    "lot_size": 1.0,
    "LOT_SIZES": {
        "XAUUSD": 0.01,
        "US500.cash": 3.5,
        "EURUSD": 0.01,
        "GBPUSD": 0.01,
        "GER40.cash": 1.5,
    },

    # ✅ Structure Toggles
    "use_engulfing": True,
    "use_bos": True,
    "use_liquidity_sweep": True,

    # ✅ EMA Threshold by Timeframe
    "ema_trend_threshold": {
        "M15": 0.0003,
        "H1": 0.0005,
        "H4": 0.001,
        "D1": 0.002
    },

    # ✅ Partial + Full Close Settings (Profit Guard)
    "partial_close_trigger_percent": 1.0,
    "full_close_trigger_percent": 2.0,

    # ✅ Session Hours
    "session_hours": {
        "Asia": (1, 7),
        "London": (8, 12),
        "New York Pre-Market": (13.5, 14),
        "New York": (14, 20),
        "Post-Market": (20, 24)
    },

    # ✅ Cooldown Settings
    "pnl_drawdown_limit": -0.5,
    "cooldown_minutes_after_recovery": 15,

    # ✅ PM Filters
    "pm_session_start": 17,
    "pm_session_end": 21,
    "pm_usd_asset_min_score": 6,

    # ✅ USD Control (Trading Window + Filter)
    "usd_related_keywords": ["USD", "US500", "US30", "NAS100"],
    "restrict_usd_to_am": True,
    "allowed_trading_window": {
        "start_hour": 14,
        "end_hour": 16,
    },

    # ✅ RSI Settings
    "use_rsi": True,
    "rsi_period": 14,
    "rsi_upper": 70,
    "rsi_lower": 30,

    # ✅ Fibonacci Settings
    "use_fib": True,
    "fib_window": 30,  # candles to look back for swing
    "fib_zone": (0.5, 0.618),
}

# Add any other configuration options you need here
