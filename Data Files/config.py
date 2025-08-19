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
    "sl_pips": 50,               # Fallback SL distance
    "tp_pips": 100,              # Fallback TP distance
    "delay_seconds": 60 * 15,    # 15-minute loop
    # min_score_for_trade moved to tech_scoring section for consolidation
    "lot_size": 1.25,            # Default lot size (legacy compatibility)
    
    # ✅ Lot Size Configuration
    "default_lot_size": 1.25,    # Default trade volume
    "lot_sizes": {               # Symbol-specific lot sizes
        "XAUUSD": 0.01,
        "US500.cash": 3.5,
        "EURUSD": 0.01,
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

    # ✅ D.E.V.I Equity Cycle Management
    "equity_cycle": {
        "stage_1_threshold": 1.0,   # +1.0% - Close 50% + Breakeven
        "stage_2_threshold": 1.5,   # +1.5% - Close all + Reset
        "stage_3_threshold": 2.0,   # +2.0% - Pause trades
        "breakeven_buffer_pips": 5, # Breakeven buffer
        "enable_logging": True      # Log all cycle triggers
    },

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

    # ✅ Risk Management
    "drawdown_limit_percent": -0.5,  # Changed from -1.0 to -0.5 for D.E.V.I
    "cooldown_minutes_after_recovery": 15,
    "global_profit_lock_cooldown_minutes": 0,
    "max_consecutive_losses": 3,
    "cooldown_after_losses_minutes": 60,

    # ✅ USD Trading Control
    "usd_related_keywords": ["USD", "US500", "US30", "NAS100", "NVDA", "TSLA"],
    "restrict_usd_to_am": True,
    "allowed_trading_window": {
        "start_hour": 13,#ondon session
        "end_hour": 16, 
    },

    # ✅ News Protection
    "enable_news_protection": True,
    "news_protection_minutes": 20,
    "news_refresh_interval_hours": 24,
    "auto_disable_on_no_news": True,  # Automatically disable protection when no events

    # ✅ Post-Session Trading
    "post_session": {
        "enabled": True,
        "score_threshold": 8.0,           # Must be 8.0 for post-session
        "min_ai_confidence": 8,           # Increased for post-session safety
        "lot_multiplier": 0.75,           # Reduced for post-session safety
        "trailing_stop_after_profit_minutes": 30,
        "soft_extension_cutoff_utc": "20:00",
        "enable_reentry": True,
        "max_reentries_per_symbol": 1,
        "partial_close_percent": 0.5,     # Faster profit taking
        "full_close_percent": 1.0,        # Faster profit taking
        "extension_min_pnl": 0.5,         # Lower threshold for extension
        "max_extension_minutes": 45,      # More time for profit development
    },
    
    # ✅ SL/TP System (Consolidated)
    "sltp_system": {
        # RRR Validation
        "min_rrr": 1.50,
        "max_sl_atr": 2.5,
        "min_tp_pips": 15,
        "max_tp_pips": 500,
        "allow_atr_fallback": True,
        "enable_repair": True,
        "log_repairs": True,
        
        # Adaptive ATR
        "enable_adaptive_atr": True,
        "adaptive_atr": {
            "low_vol_percentile": 0.3,
            "high_vol_percentile": 0.7,
            "mult_low": 1.2,
            "mult_mid": 1.5,
            "mult_high": 1.8,
            "lookback": 90
        },
        
        # HTF Validation
        "enable_htf_validation": True,
        "htf_timeframe": "H1",
        "htf_min_score": 0.6,
        
        # TP Split (DISABLED for D.E.V.I equity cycle system)
        "enable_tp_split": False,
        "tp_split": {
            "tp1_ratio": 1.0,           # 1:1
            "tp1_size": 0.30,           
            "tp2_ratio": 2.0,           # 2:1
            "tp2_size": 0.70,
            "breakeven_buffer_pips": 5
        },
        
        # Structure-Aware Features
        "enable_distance_filters": True,
        "enable_rrr_lot_sizing": False,
        "enable_detailed_logging": True,
        
        # RRR-Based Lot Sizing
        "lot_multipliers": {
            "high": 1.0,      # RRR >= 2.0
            "moderate": 0.75,  # RRR 1.5-1.99
            "low": 0.5,       # RRR 1.0-1.49
            "very_low": 0.25  # RRR < 1.0
        }
    },
    
    # ✅ Technical Scoring System
    "tech_scoring": {
        "scale": "0_to_8",
        "min_score_for_trade": 6.5, # Added: Use 6.0 as requested
        "post_session_threshold": 6.5,
        "pm_usd_asset_min_score": 6.0,
        "require_ema_alignment": True,
        "ai_min_confidence": 7.0,
        "ai_override_enabled": True
    },
    
    # ✅ System Features
    "disable_telegram": False,  # Disabled for now
}

# ✅ Feature flag for 0-8 scoring system
USE_8PT_SCORING = True
