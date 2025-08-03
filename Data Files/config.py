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
    "disable_telegram": False,  # Set to False to enable


    # ✅ Trade Requirements
    "min_score_for_trade": 6,
    "sl_pips": 50,
    "tp_pips": 100,
    "delay_seconds": 60 * 15,  # 15-minute loop

    # ✅ Symbol-Specific Lot Sizes
    "lot_size": 1.25,
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
    "drawdown_limit_percent": -1.0,
    "cooldown_minutes_after_recovery": 15,
    "global_profit_lock_cooldown_minutes": 0,


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

    # ✅ News Protection Settings (Red Folder Filter)
    "enable_news_protection": True,  # Set to False to disable news protection temporarily
    "news_protection_minutes": 30,   # minutes before/after red folder events (±30 min = 1 hour total)
    "news_refresh_interval_hours": 24,  # how often to refresh news data

    # ✅ Post-Session Trading Settings
    "post_session_enabled": True,
    "post_session_score_threshold": 8.0,
    "post_session_min_ai_confidence": 70,
    "post_session_lot_multiplier": 0.75,  # 0.75x base lot for all post-session trades
    "post_session_trailing_stop_after_profit_minutes": 30,
    "post_session_soft_extension_cutoff_utc": "19:30",
    "post_session_enable_reentry": True,
    "post_session_max_reentries_per_symbol": 1,
    "post_session_partial_close_percent": 0.75,
    "post_session_full_close_percent": 1.5,
    "post_session_extension_min_pnl": 1.0,
    "post_session_max_extension_minutes": 30,
}

# Add any other configuration options you need here
