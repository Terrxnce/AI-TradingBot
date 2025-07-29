import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'Bot Core'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))

def debug_mt5_data():
    """Debug MT5 data fetching to see what's wrong with profit calculations"""
    
    print("🔍 DEBUGGING MT5 DATA FETCHING")
    print("=" * 50)
    
    # Initialize MT5
    if not mt5.initialize():
        print("❌ Failed to initialize MT5")
        return
    
    print("✅ MT5 initialized")
    
    # Get all deals from July 21st onwards
    utc_from = datetime(2025, 7, 21)
    utc_to = datetime.now()
    
    print(f"📅 Fetching deals from {utc_from} to {utc_to}")
    
    deals = mt5.history_deals_get(utc_from, utc_to)
    mt5.shutdown()
    
    if not deals:
        print("❌ No deals found")
        return
    
    print(f"✅ Found {len(deals)} total deals")
    
    # Convert to DataFrame
    deals_df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    
    print(f"📊 DataFrame shape: {deals_df.shape}")
    print(f"📊 Columns: {list(deals_df.columns)}")
    
    # Show all USDJPY deals
    usdjpy_deals = deals_df[deals_df['symbol'] == 'USDJPY'].copy()
    print(f"✅ Found {len(usdjpy_deals)} USDJPY deals")
    
    if not usdjpy_deals.empty:
        # Show all USDJPY deals with details
        print("\n📋 ALL USDJPY DEALS:")
        print("-" * 80)
        for idx, deal in usdjpy_deals.iterrows():
            deal_time = pd.to_datetime(deal['time'], unit='s')
            direction = "BUY" if deal['type'] == 0 else "SELL"
            print(f"Deal {idx}: {deal_time} | {direction} | Volume: {deal['volume']} | Price: {deal['price']} | Profit: ${deal['profit']:.2f}")
        
        # Filter for actual trades only (BUY/SELL)
        actual_trades = usdjpy_deals[usdjpy_deals['type'].isin([0, 1])].copy()
        print(f"\n✅ Found {len(actual_trades)} actual USDJPY trades (BUY/SELL)")
        
        if not actual_trades.empty:
            actual_trades['timestamp'] = pd.to_datetime(actual_trades['time'], unit='s')
            actual_trades['direction'] = actual_trades['type'].apply(lambda x: "BUY" if x == 0 else "SELL")
            actual_trades = actual_trades.sort_values('timestamp', ascending=False)
            
            print("\n📋 ACTUAL USDJPY TRADES (BUY/SELL):")
            print("-" * 80)
            total_profit = 0
            for idx, trade in actual_trades.iterrows():
                print(f"Trade: {trade['timestamp']} | {trade['direction']} | Volume: {trade['volume']} | Price: {trade['price']} | Profit: ${trade['profit']:.2f}")
                total_profit += trade['profit']
            
            print(f"\n💰 TOTAL PROFIT: ${total_profit:.2f}")
            
            # Show the latest 3 trades specifically
            print(f"\n🎯 LATEST 3 TRADES:")
            print("-" * 40)
            latest_3 = actual_trades.head(3)
            for idx, trade in latest_3.iterrows():
                print(f"Latest {3-idx}: {trade['timestamp']} | {trade['direction']} | Profit: ${trade['profit']:.2f}")
            
            # Calculate expected total from your screenshot
            expected_trades = [53.32, 70.91, 50.56]
            expected_total = sum(expected_trades)
            print(f"\n📊 EXPECTED (from screenshot): ${expected_total:.2f}")
            print(f"📊 ACTUAL (from MT5): ${total_profit:.2f}")
            print(f"📊 DIFFERENCE: ${total_profit - expected_total:.2f}")
    
    # Also check what's in the CSV trade log
    print("\n" + "=" * 50)
    print("📄 CHECKING CSV TRADE LOG")
    print("=" * 50)
    
    try:
        csv_trades = pd.read_csv("logs/trade_log.csv")
        print(f"✅ CSV trade log shape: {csv_trades.shape}")
        print(f"✅ CSV columns: {list(csv_trades.columns)}")
        
        if not csv_trades.empty:
            print("\n📋 CSV TRADES:")
            print("-" * 40)
            for idx, trade in csv_trades.iterrows():
                print(f"CSV {idx}: {trade['timestamp']} | {trade['direction']} | Lot: {trade['lot']} | Result: {trade['result']}")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")

if __name__ == "__main__":
    debug_mt5_data() 