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
from config import CONFIG
from session_utils import detect_session


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


    def detect_false_breaks(self, swing_lookback=5):
        sweeps = []
        for i in range(swing_lookback, len(self.df)):
            local_high = self.df['high'][i - swing_lookback:i].max()
            local_low = self.df['low'][i - swing_lookback:i].min()
            c = self.df.iloc[i]
            if c['high'] > local_high and c['close'] < local_high:
                sweeps.append((i, 'bullish', local_high))
            elif c['low'] < local_low and c['close'] > local_low:
                sweeps.append((i, 'bearish', local_low))
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
            "false_breaks": self.detect_false_breaks(),
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

    print("📈 EMA Values → EMA_21:", row['EMA_21'], "| EMA_50:", row['EMA_50'], "| EMA_200:", row['EMA_200'])
    print("📊 Final EMA trend classification:", trend)
    print("🔍 Latest BOS:", latest_bos)
    print("🕐 Current Session:", detect_session())
    print("✅ analyze_structure() completed for", candles_df.iloc[-1]["time"])

    if h1_trend:
        print("🧭 H1 Trend Confirmation:", h1_trend)

    return {
        "bos": latest_bos,
        "fvg_valid": any(fvg[1] == trend for fvg in result["fvg"]),
        "ob_tap": any(ob[1] == trend for ob in result["order_blocks"]),
        "rejection": len(result["rejections"]) > 0,
        "false_break": len(result["false_breaks"]) > 0,
        "engulfing": any(e[1] == trend for e in result["engulfings"]),
        "ema_trend": trend,
        "h1_trend": h1_trend,
     "session": "London"  # ← Hardcoded for now

    }
