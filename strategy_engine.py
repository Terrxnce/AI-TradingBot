import pandas as pd

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

            if c0['low'] > c2['high']:
                fvg_signals.append((i, 'bearish', c2['high'], c0['low']))
            elif c0['high'] < c2['low']:
                fvg_signals.append((i, 'bullish', c0['high'], c2['low']))
        return fvg_signals

    def detect_order_blocks(self):
        ob_signals = []
        for i in range(1, len(self.df)):
            body = abs(self.df.iloc[i]['open'] - self.df.iloc[i]['close'])
            wick = abs(self.df.iloc[i]['high'] - self.df.iloc[i]['low']) - body
            if body > wick * 1.5:
                direction = 'bullish' if self.df.iloc[i]['close'] > self.df.iloc[i]['open'] else 'bearish'
                ob_signals.append((i, direction, self.df.iloc[i]['open'], self.df.iloc[i]['close']))
        return ob_signals

    def detect_bos(self):
        bos = []
        for i in range(2, len(self.df)):
            prev_high = self.df.iloc[i - 1]['high']
            prev_low = self.df.iloc[i - 1]['low']
            if self.df.iloc[i]['close'] > prev_high:
                bos.append((i, 'bullish'))
            elif self.df.iloc[i]['close'] < prev_low:
                bos.append((i, 'bearish'))
        return bos

    def run_all(self):
        self.calculate_ema()
        return {
            "fvg": self.detect_fvg(),
            "order_blocks": self.detect_order_blocks(),
            "bos": self.detect_bos(),
            "df": self.df
        }


def analyze_structure(candles_df):
    ta = TechnicalAnalyzer(candles_df)
    result = ta.run_all()

    latest_bos = result["bos"][-1][1] if result["bos"] else None
    trend = "bullish" if result["df"].iloc[-1]['EMA_21'] > result["df"].iloc[-1]['EMA_50'] else "bearish"

    return {
        "bos": True if latest_bos == trend else False,
        "fvg_valid": len(result["fvg"]) > 0,
        "ob_tap": len(result["order_blocks"]) > 0,
        "ema_trend": trend
    }
