# ------------------------------------------------------------------------------------
# ⚙️ config.py – Global Bot Settings
#
# This file controls all configurable options used across the trading bot:
#
# ✅ tech_scoring.min_score_for_trade – Minimum technical score required (SINGLE SOURCE OF TRUTH)
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

# ✅ FTMO Challenge Parameters
FTMO_PARAMS = {
    "initial_balance": 10_000,
    "max_daily_loss_pct": 0.05,
    "max_total_loss_pct": 0.10,
    "profit_target_pct": 0.10,
    "min_trading_days": 4
}

CONFIG = {
    # ✅ Core Trading Parameters
    "sl_pips": 38,            # Fallback SL distance
    "tp_pips": 76,           # Fallback TP distance
    "delay_seconds": 60 * 15,    # 15-minute loop
    # min_score_for_trade moved to tech_scoring section for consolidation
    "lot_size": 1.25,            # Keep for backward compatibility (same as default_lot_size)
    
    # ✅ Lot Size Configuration
    "default_lot_size": 1.25,    # Default trade volume
    "lot_sizes": {               # Symbol-specific lot sizes
        "XAUUSD": 0.01,
        "US500.cash": 3.5,
        "EURUSD": 1.25,
        "GBPUSD": 0.01,
        "GER40.cash": 1.5,
        "NVDA": 35.0,
        "TSLA": 35.0,
        "USDJPY": 1.25,
    },

    # ✅ Technical Analysis Toggles
    "use_engulfing": True,
    "use_bos": True,
    "use_liquidity_sweep": True,

    # ✅ EMA Configuration
    "ema_trend_threshold": {
        "M15": 0.0003,
        "H1": 0.0005,
        "H4": 0.001,
        "D1": 0.002
    },

    # ✅ D.E.V.I Equity Cycle Management - moved to PROTECTION_CONFIG

    # ✅ Session Management
    "session_hours": {
        "Asia": (1, 7),
        "London": (8, 12),
        "New York Pre-Market": (13.5, 14),
        "New York": (14, 20),
        "Post-Market": (20, 24)
    },
    
    # ✅ Off-Hours Trading Restrictions
    "restrict_off_hours_trading": True,
    "min_score_off_hours": 7.0,
    "max_lot_size_off_hours": 0.5,

    # ✅ Risk Management - SIMPLIFIED (most moved to PROTECTION_CONFIG)
    # Legacy risk parameters (may be unused):
    "max_consecutive_losses": 3,               # Consider removing if unused
    "cooldown_after_losses_minutes": 60,       # Consider removing if unused

    # ✅ USD Trading Control
    "usd_related_keywords": ["USD", "US500", "US30", "NAS100", "NVDA", "TSLA"],
    "restrict_usd_to_am": True,
    "allowed_trading_window": {
        "start_hour": 12.5,        # 12:30 UTC (1:30 PM Irish)
        "end_hour": 19,            # 19:00 UTC (8:00 PM Irish) - Extended for PM session
    },
    
    # ✅ PM Session Configuration
    "pm_session_start": 17,        # 17:00 UTC (6:00 PM Irish)
    "pm_session_end": 19,          # 19:00 UTC (8:00 PM Irish)
    "enable_pm_session_only": True, # Enable PM session trading
    "pm_session_lot_multiplier": 0.5, # Use 50% of normal lot size during PM session

    # ✅ News Protection
    "enable_news_protection": True,
    "news_protection_minutes": 20,         # Minutes before/after to block trading
    "news_impact_filter": ["High"],          # Which impacts to block (High/Medium/Low)
    "news_refresh_interval_hours": 24,
    "auto_disable_on_no_news": True,         # Automatically disable protection when no events

    # ✅ Post-Session Trading - REMOVED (Complex logic replaced by protection system)
    # Session management now handled by PROTECTION_CONFIG.session_end_utc
    
    # ✅ SL/TP System - REMOVED (Obsolete structure-aware system)
    # Old sltp_system replaced by simple ATR parameters + PROTECTION_CONFIG
    
    # ✅ Technical Scoring System
    "tech_scoring": {
        "scale": "0_to_8",
        "min_score_for_trade": 6.0, # Adjusted for simple scoring system
        "post_session_threshold": 6.0,
        "pm_usd_asset_min_score": 7.0,
        "require_ema_alignment": True,
        "ai_min_confidence": 7.0,
        "ai_override_enabled": True
    },
    
    # ✅ ATR-Based SL/TP System - MOVED to PROTECTION_CONFIG
    # These parameters moved to PROTECTION_CONFIG for consolidation
    "DEFAULT_SL_MULTIPLIER": 1.5,    # ATR multiplier for Stop Loss (legacy compatibility)
    "DEFAULT_TP_MULTIPLIER": 2.5,    # ATR multiplier for Take Profit (legacy compatibility)
    "ATR_PERIOD": 14,                # ATR calculation period (legacy compatibility)
    "MIN_RRR": 1.2,                  # Minimum Risk:Reward ratio (legacy compatibility)
    
    # ✅ System Features
    "disable_telegram": False,  # Disabled for now
}

# ✅ D.E.V.I Profit Protection System Configuration
PROTECTION_CONFIG = {
    # Equity Protection Thresholds
    "equity_partial_pct": 1.00,           # +1% → Partial close + Breakeven
    "equity_full_pct": 2.00,              # +2% → Full close (after partial)
    "drawdown_block_pct": -0.50,          # -0.5% → Block new trades
    "unblock_threshold_pct": 0.00,        # 0% → Unblock trades
    
    # Trailing Stop Configuration
    "trailing_activate_seconds": 1800,     # 30 minutes = 1800 seconds
    "trail_use_atr": True,                 # Use ATR-based trailing
    "trail_atr_period": 14,                # ATR calculation period
    "trail_atr_mult": 1.0,                 # ATR multiplier for trailing distance
    "trail_fixed_pips": 15,                # Fixed pip distance (fallback)
    
    # Breakeven Configuration
    "breakeven_tick_safety": 1,            # Ticks of safety buffer
    "apply_to_profitable_only": True,      # Only apply to profitable trades
    
    # Session Management
    "session_end_utc": "19:00",            # Session end time (UTC) - Extended for PM session
    "cycle_epsilon_pct": 0.10,             # ±0.1% tolerance for cycle reset
}

# === SL/TP System Configuration ===
SL_TP_CONFIG = {
    "min_stop_buffer_ticks": 2,         # Safety buffer beyond broker minimum
    "prefer_structure": True,           # Use structure-aware SL/TP (Phase 2)
    "structure_sl_buffer_pips": 10,     # Buffer beyond structure invalidation
    "fallback_sl_multiplier": 1.5,      # ATR fallback SL multiplier
    "fallback_tp_multiplier": 2.0,      # ATR fallback TP multiplier
    "max_sl_pips": 70,                  # Maximum SL distance (safety cap)
    "fallback_sl_pips": 25,             # Emergency fallback SL
    "fallback_tp_pips": 50,             # Emergency fallback TP
    "enable_broker_validation": True,   # Enforce broker minimum stops
}

# ✅ Feature flag for 0-8 scoring system
USE_8PT_SCORING = False  # Use simple scoring system
