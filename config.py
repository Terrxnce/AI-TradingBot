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

CONFIG = {
    "min_score_for_trade": 2,
    "sl_pips": 50,
    "tp_pips": 100,
    "lot_size": 0.1,
    "use_engulfing": False,
    "use_bos": True,
    "use_liquidity_sweep": True,
    "ema_trend_threshold": {
        "M15": 0.0003,
        "H1": 0.0005,
        "H4": 0.001,
        "D1": 0.002
    }

}
# Add any other configuration options you need here
