# ------------------------------------------------------------------------------------
# 📊 strategy_engine.py – Full Technical Analysis Pipeline
#
# This module defines the full candle-based logic for identifying trade conditions.
# It performs structural and trend analysis using EMAs, BOS, FVGs, OBs, false breaks,
# engulfings, and rejection confirmation zones.
#
# ✅ TechnicalAnalyzer – Class that detects all key price action structures
# ✅ analyze_structure() – Packs all signals and returns a clean decision dictionary
#
# Indicators Detected:
#   - EMA Trend (21/50/200)
#   - Fair Value Gaps (FVG)
#   - Order Blocks (OB)
#   - Break of Structure (BOS)
#   - False Breakouts / Liquidity Sweeps
#   - Bullish Engulfing Candles
#   - Rejection from OB/FVG Zones
#
# Used by: decision_engine.py for signal evaluation
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
from config import CONFIG
from session_manager import get_current_session_info
from impulse_detector import detect_impulsive_move
from rsi_fib_confluence import fib_confluence, rsi_support



class TechnicalAnalyzer:
    def __init__(self, df):
        self.df = df.copy()

    def calculate_ema(self, periods=[21, 50, 200]):
        for period in periods:
            self.df[f'EMA_{period}'] = self.df['close'].ewm(span=period, adjust=False).mean()

    def detect_fvg(self):
        fvg_signals = []
        for i in range(2, len(self.df)):
            c0 = self.df.iloc[i - 2]
            c2 = self.df.iloc[i]
            if c0['low'] > c2['high']:  # Bearish FVG
                fvg_signals.append((i, 'bearish', c2['high'], c0['low'], (c2['high'] + c0['low']) / 2))
            elif c0['high'] < c2['low']:  # Bullish FVG
                fvg_signals.append((i, 'bullish', c0['high'], c2['low'], (c0['high'] + c2['low']) / 2))
        return fvg_signals

    def detect_order_blocks(self):
        ob_signals = []
        for i in range(1, len(self.df)):
            c = self.df.iloc[i]
            body = abs(c['close'] - c['open'])
            wick = (c['high'] - c['low']) - body
            if body > wick * 1.5:
                direction = 'bullish' if c['close'] > c['open'] else 'bearish'
                ob_signals.append((i, direction, min(c['open'], c['close']), max(c['open'], c['close'])))
        return ob_signals

    def detect_engulfing(self):
        engulfings = []
        for i in range(1, len(self.df)):
            prev, curr = self.df.iloc[i - 1], self.df.iloc[i]

        # Bullish Engulfing
            if prev['close'] < prev['open'] and curr['close'] > curr['open']:
                if curr['close'] > prev['open'] and curr['open'] < prev['close']:
                    engulfings.append((i, 'bullish'))

        # Bearish Engulfing
            elif prev['close'] > prev['open'] and curr['close'] < curr['open']:
                if curr['close'] < prev['open'] and curr['open'] > prev['close']:
                    engulfings.append((i, 'bearish'))

        return engulfings

    def detect_bos(self, swing_lookback=5):
        bos = []

        for i in range(swing_lookback * 2, len(self.df)):
             prev_candles = self.df.iloc[i - swing_lookback * 2:i]

             # Detect recent swing levels
             swing_high = prev_candles['high'].rolling(window=swing_lookback).max().iloc[-1]
             swing_low = prev_candles['low'].rolling(window=swing_lookback).min().iloc[-1]

        current_close = self.df.iloc[i]['close']

        # Confirmed BOS based on close
        if current_close > swing_high:
            bos.append((i, 'bullish', swing_high))
        elif current_close < swing_low:
            bos.append((i, 'bearish', swing_low))

        return bos


    def detect_liquidity_sweeps(self, lookback=10, epsilon=0.001):
        sweeps = []
        for i in range(lookback, len(self.df)):
            c = self.df.iloc[i]
            prior_high = self.df['high'][i - lookback:i].max()
            prior_low = self.df['low'][i - lookback:i].min()

            # Bullish Liquidity Sweep (break high, close below it)
            if c['high'] > prior_high * (1 + epsilon) and c['close'] < prior_high:
                sweeps.append((i, 'bullish', prior_high))

            # Bearish Liquidity Sweep (break low, close above it)
            elif c['low'] < prior_low * (1 - epsilon) and c['close'] > prior_low:
                sweeps.append((i, 'bearish', prior_low))

        return sweeps


    def check_ob_fvg_rejection(self, max_lookahead=10):
        rejections, all_zones = [], []
        for i, dir, low, high in self.detect_order_blocks():
            all_zones.append({"type": "OB", "index": i, "direction": dir, "low": low, "high": high})
        for i, dir, low, high, _ in self.detect_fvg():
            all_zones.append({"type": "FVG", "index": i, "direction": dir, "low": low, "high": high})

        for zone in all_zones:
            for j in range(zone["index"] + 1, min(zone["index"] + 1 + max_lookahead, len(self.df))):
                c = self.df.iloc[j]
                if zone["direction"] == "bullish" and zone["low"] <= c['low'] <= zone["high"] and c['close'] > c['open']:
                    rejections.append({**zone, "rejected_at": j})
                    break
                elif zone["direction"] == "bearish" and zone["low"] <= c['high'] <= zone["high"] and c['close'] < c['open']:
                    rejections.append({**zone, "rejected_at": j})
                    break
        return rejections

    def run_all(self):
        self.calculate_ema()
        return {
            "fvg": self.detect_fvg(),
            "order_blocks": self.detect_order_blocks(),
            "bos": self.detect_bos(),
            "liquidity_sweeps": self.detect_liquidity_sweeps(),
            "engulfings": self.detect_engulfing(),
            "rejections": self.check_ob_fvg_rejection(),
            "df": self.df
        }

def tf_to_str(tf):
    return {
        mt5.TIMEFRAME_M1:  "M1",
        mt5.TIMEFRAME_M5:  "M5",
        mt5.TIMEFRAME_M15: "M15",
        mt5.TIMEFRAME_M30: "M30",
        mt5.TIMEFRAME_H1:  "H1",
        mt5.TIMEFRAME_H4:  "H4",
        mt5.TIMEFRAME_D1:  "D1",
    }.get(tf, "M15")

def detect_ema_trend(row, min_separation=0):
    e21, e50, e200 = row['EMA_21'], row['EMA_50'], row['EMA_200']
    if e21 > e50 > e200 and (e21 - e50) > min_separation and (e50 - e200) > min_separation:
        return "bullish"
    elif e21 < e50 < e200 and (e50 - e21) > min_separation and (e200 - e50) > min_separation:
        return "bearish"
    return "neutral"

def analyze_structure(candles_df, candles_df_h1=None, timeframe=mt5.TIMEFRAME_M15):
    ta = TechnicalAnalyzer(candles_df)
    result = ta.run_all()
    row = result["df"].iloc[-1]

    tf_str = tf_to_str(timeframe)
    min_sep = CONFIG.get("ema_trend_threshold", {}).get(tf_str, 0.0001)
    trend = detect_ema_trend(row, min_sep)

    # Confirm H1 trend alignment
    h1_trend = None
    if candles_df_h1 is not None:
        ta_h1 = TechnicalAnalyzer(candles_df_h1)
        ta_h1.calculate_ema()
        h1_row = ta_h1.df.iloc[-1]
        h1_min_sep = CONFIG.get("ema_trend_threshold", {}).get("H1", 0.0005)
        h1_trend = detect_ema_trend(h1_row, h1_min_sep)

    latest_bos = result["bos"][-1][1] if result["bos"] else None

    # ✅ Impulse Detection
    impulse = detect_impulsive_move(candles_df)
    confluence_context = []

    if impulse:
        # Only check Fib/RSI if impulse is valid
        fib_hit, fib_text = fib_confluence(candles_df, impulse)
        rsi_ok, rsi_text = rsi_support(candles_df)

        if fib_hit:
            confluence_context.append(fib_text)
        if rsi_ok:
            confluence_context.append(rsi_text)

    # 🔍 Logs - Using structured logging instead of print statements
    # Note: These logs are now handled by the calling function for better organization

    # Enhanced structure analysis for new scoring system
    bos_confirmed = latest_bos is not None
    bos_direction = latest_bos if latest_bos else "NEUTRAL"
    
    fvg_valid = any(fvg[1] == trend for fvg in result["fvg"] if isinstance(fvg, (list, tuple)) and len(fvg) >= 4)
    # FVG fill detection - check if price has moved through the FVG
    fvg_filled = False
    if fvg_valid and len(candles_df) > 1:
        current_price = candles_df.iloc[-1]['close']
        for fvg in result["fvg"]:
            # Validate FVG structure before accessing
            if not isinstance(fvg, (list, tuple)) or len(fvg) < 4:
                continue
            try:
                if fvg[1] == trend:  # FVG in trend direction
                    fvg_high, fvg_low = fvg[2], fvg[3]
                    if trend == "bullish" and current_price > fvg_high:
                        fvg_filled = True
                        break
                    elif trend == "bearish" and current_price < fvg_low:
                        fvg_filled = True
                        break
            except (IndexError, KeyError, TypeError) as e:
                print(f"⚠️ Error processing FVG data: {e}")
                continue
    fvg_direction = trend if fvg_valid else "NEUTRAL"
    
    ob_tap = any(ob[1] == trend for ob in result["order_blocks"] if isinstance(ob, (list, tuple)) and len(ob) >= 2)
    ob_direction = trend if ob_tap else "NEUTRAL"
    
    rejection_at_key_level = len(result["rejections"]) > 0
    # Next candle confirmation - check if rejection was followed by continuation
    rejection_confirmed_next = False
    if rejection_at_key_level and len(candles_df) > 2:
        for rejection in result["rejections"]:
            # Validate rejection structure before accessing
            if not isinstance(rejection, (list, tuple)) or len(rejection) < 2:
                continue
            try:
                rejection_idx = rejection[0]
                if rejection_idx < len(candles_df) - 1:
                    next_candle = candles_df.iloc[rejection_idx + 1]
                    rejection_candle = candles_df.iloc[rejection_idx]
                    # Check if next candle continued in rejection direction
                    if rejection[1] == "bullish" and next_candle['close'] > rejection_candle['close']:
                        rejection_confirmed_next = True
                        break
                    elif rejection[1] == "bearish" and next_candle['close'] < rejection_candle['close']:
                        rejection_confirmed_next = True
                        break
            except (IndexError, KeyError, TypeError) as e:
                print(f"⚠️ Error processing rejection data: {e}")
                continue
    rejection_direction = trend if rejection_at_key_level else "NEUTRAL"
    
    sweep_recent = len(result["liquidity_sweeps"]) > 0
    # Reversal confirmation - check if sweep was followed by reversal
    sweep_reversal_confirmed = False
    if sweep_recent and len(candles_df) > 2:
        for sweep in result["liquidity_sweeps"]:
            # Validate sweep structure before accessing
            if not isinstance(sweep, (list, tuple)) or len(sweep) < 2:
                continue
            try:
                sweep_idx = sweep[0]
                if sweep_idx < len(candles_df) - 1:
                    next_candle = candles_df.iloc[sweep_idx + 1]
                    sweep_candle = candles_df.iloc[sweep_idx]
                    # Check if next candle reversed from sweep direction
                    if sweep[1] == "bullish" and next_candle['close'] < sweep_candle['close']:
                        sweep_reversal_confirmed = True
                        break
                    elif sweep[1] == "bearish" and next_candle['close'] > sweep_candle['close']:
                        sweep_reversal_confirmed = True
                        break
            except (IndexError, KeyError, TypeError) as e:
                print(f"⚠️ Error processing sweep data: {e}")
                continue
    sweep_direction = trend if sweep_recent else "NEUTRAL"
    
    engulfing_present = any(e[1] == trend for e in result["engulfings"] if isinstance(e, (list, tuple)) and len(e) >= 2)
    engulfing_direction = trend if engulfing_present else "NEUTRAL"
    
    # EMA alignment checks
    ema_aligned_m15 = trend in ["bullish", "bearish"]
    ema_aligned_h1 = h1_trend in ["bullish", "bearish"] if h1_trend else False
    
    return {
        # Legacy format (for backward compatibility)
        "bos": latest_bos,
        "fvg_valid": fvg_valid,
        "ob_tap": ob_tap,
        "rejection": rejection_at_key_level,
        "liquidity_sweep": sweep_recent,
        "engulfing": engulfing_present,
        "ema_trend": trend,
        "h1_trend": h1_trend,
        "session": get_current_session_info()["session_type"],
        "impulse_move": impulse,
        "confluence_context": confluence_context,  # ✅ For AI only
        
        # NEW: Enhanced structure data for 0-8 scoring
        "bos_confirmed": bos_confirmed,
        "bos_direction": bos_direction,
        "fvg_filled": fvg_filled,
        "fvg_direction": fvg_direction,
        "ob_direction": ob_direction,
        "rejection_confirmed_next": rejection_confirmed_next,
        "rejection_direction": rejection_direction,
        "sweep_reversal_confirmed": sweep_reversal_confirmed,
        "sweep_direction": sweep_direction,
        "engulfing_direction": engulfing_direction,
        "ema_aligned_m15": ema_aligned_m15,
        "ema_aligned_h1": ema_aligned_h1,
        
        # EMA values for scoring context
        "ema21": row['EMA_21'],
        "ema50": row['EMA_50'],
        "ema200": row['EMA_200'],
        "price": row['close']
    }