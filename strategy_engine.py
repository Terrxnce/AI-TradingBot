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
from config import CONFIG

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
                low = c2['high']
                high = c0['low']
                mid = (low + high) / 2
                fvg_signals.append((i, 'bearish', low, high, mid))
            elif c0['high'] < c2['low']:  # Bullish FVG
                low = c0['high']
                high = c2['low']
                mid = (low + high) / 2
                fvg_signals.append((i, 'bullish', low, high, mid))
        return fvg_signals

    def detect_order_blocks(self):
        ob_signals = []
        for i in range(1, len(self.df)):
            c = self.df.iloc[i]
            body = abs(c['close'] - c['open'])
            wick = (c['high'] - c['low']) - body
            if body > wick * 1.5:
                direction = 'bullish' if c['close'] > c['open'] else 'bearish'
                ob_top = max(c['open'], c['close'])
                ob_bottom = min(c['open'], c['close'])
                ob_signals.append((i, direction, ob_bottom, ob_top))
        return ob_signals

    def detect_engulfing(self):
        engulfings = []
        for i in range(1, len(self.df)):
            prev = self.df.iloc[i - 1]
            curr = self.df.iloc[i]
            if prev['close'] < prev['open'] and curr['close'] > curr['open']:
                if curr['close'] > prev['open'] and curr['open'] < prev['close']:
                    engulfings.append((i, 'bullish'))
        return engulfings

    def detect_bos(self, swing_lookback=3):
        bos = []
        for i in range(swing_lookback * 2, len(self.df)):
            prev_candles = self.df.iloc[i - swing_lookback*2:i]
            swing_high = prev_candles['high'][swing_lookback:-swing_lookback].max()
            swing_low = prev_candles['low'][swing_lookback:-swing_lookback].min()
            if self.df.iloc[i]['close'] > swing_high:
                bos.append((i, 'bullish', swing_high))
            if self.df.iloc[i]['close'] < swing_low:
                bos.append((i, 'bearish', swing_low))
        return bos

    def detect_false_breaks(self, swing_lookback=5):
        sweeps = []
        for i in range(swing_lookback, len(self.df)):
            local_high = self.df['high'][i - swing_lookback:i].max()
            local_low = self.df['low'][i - swing_lookback:i].min()
            curr = self.df.iloc[i]
            if curr['high'] > local_high and curr['close'] < local_high:
                sweeps.append((i, 'bullish', local_high))
            elif curr['low'] < local_low and curr['close'] > local_low:
                sweeps.append((i, 'bearish', local_low))
        return sweeps

    def check_ob_fvg_rejection(self, max_lookahead=10):
        rejections = []
        all_zones = []

        for i, dir, low, high in self.detect_order_blocks():
            all_zones.append({"type": "OB", "index": i, "direction": dir, "low": low, "high": high})
        for i, dir, low, high, _ in self.detect_fvg():
            all_zones.append({"type": "FVG", "index": i, "direction": dir, "low": low, "high": high})

        for zone in all_zones:
            for j in range(zone["index"] + 1, min(zone["index"] + 1 + max_lookahead, len(self.df))):
                c = self.df.iloc[j]
                if zone["direction"] == "bullish":
                    if zone["low"] <= c['low'] <= zone["high"] and c['close'] > c['open']:
                        rejections.append({**zone, "rejected_at": j})
                        break
                elif zone["direction"] == "bearish":
                    if zone["low"] <= c['high'] <= zone["high"] and c['close'] < c['open']:
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
    bullish = e21 > e50 > e200
    bearish = e21 < e50 < e200
    if bullish and (e21 - e50) > min_separation and (e50 - e200) > min_separation:
        return "bullish"
    elif bearish and (e50 - e21) > min_separation and (e200 - e50) > min_separation:
        return "bearish"
    else:
        return "neutral"

def analyze_structure(candles_df, timeframe=mt5.TIMEFRAME_M15):
    ta = TechnicalAnalyzer(candles_df)
    result = ta.run_all()
    row = result["df"].iloc[-1]

    tf_str = tf_to_str(timeframe)
    min_sep = CONFIG.get("ema_trend_thresholds", {}).get(tf_str, 0.0001)

    trend = detect_ema_trend(row, min_separation=min_sep)

    print("📈 EMA Values → EMA_21:", row['EMA_21'], "| EMA_50:", row['EMA_50'], "| EMA_200:", row['EMA_200'])
    print("📊 Final EMA trend classification:", trend)

    latest_bos = None
    for bos in reversed(result["bos"]):
        if bos[1] == trend or trend == "neutral":
            latest_bos = bos[1]
            break

    print("🔍 Latest BOS:", latest_bos)

    return {
        "bos": latest_bos,
        "fvg_valid": any(fvg[1] == trend for fvg in result["fvg"]),
        "ob_tap": any(ob[1] == trend for ob in result["order_blocks"]),
        "rejection": len(result["rejections"]) > 0,
        "false_break": len(result["false_breaks"]) > 0,
        "engulfing": len(result["engulfings"]) > 0,
        "ema_trend": trend
    }
