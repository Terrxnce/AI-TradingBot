import pandas as pd
from ta.trend import EMAIndicator


def calculate_ema(df, period):
    ema = EMAIndicator(close=df["close"], window=period).ema_indicator()
    return ema