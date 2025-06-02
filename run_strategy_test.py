from get_candles import fetch_mt5_data
from strategy_engine import TechnicalAnalyzer

# Pull data from MT5
df = fetch_mt5_data(symbol="EURUSD", timeframe=1, bars=300)

# Run technical analysis
analyzer = TechnicalAnalyzer(df)
results = analyzer.run_all()

# Print results
print("✅ FVGs:", results["fvg"][:3])
print("✅ OBs:", results["order_blocks"][:3])
print("✅ BOS:", results["bos"][:3])
