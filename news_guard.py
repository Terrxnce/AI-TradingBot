import MetaTrader5 as mt5
from datetime import datetime, timedelta
import requests
import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import CONFIG

# News protection settings
NEWS_PROTECTION_MINUTES = 15  # 15 minutes before and after
NEWS_API_KEY = "your_news_api_key_here"  # Replace with your actual key
NEWS_API_URL = "https://newsapi.org/v2/everything"

def get_high_impact_news():
    """Get high-impact news events for today"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Keywords for high-impact news
        keywords = [
            "NFP", "Non-Farm Payrolls", "Federal Reserve", "FOMC", "ECB", "BOE", "BOJ",
            "CPI", "Inflation", "GDP", "Employment", "Interest Rate", "Central Bank",
            "FOMC Meeting", "ECB Meeting", "BOE Meeting", "BOJ Meeting"
        ]
        
        # For now, return a simple structure - you can integrate with NewsAPI later
        # This is a placeholder that you can replace with actual API calls
        return []
        
    except Exception as e:
        print(f"❌ Error fetching news: {e}")
        return []

def is_news_protection_active():
    """
    Check if we're in a news protection window (15min before/after high-impact news)
    Returns True if trading should be blocked due to news
    """
    try:
        # Get current time
        now = datetime.now()
        
        # Get high-impact news events
        news_events = get_high_impact_news()
        
        for event in news_events:
            event_time = event.get('time')
            if not event_time:
                continue
                
            # Convert to datetime if it's a string
            if isinstance(event_time, str):
                try:
                    event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                except:
                    continue
            
            # Calculate protection window
            protection_start = event_time - timedelta(minutes=NEWS_PROTECTION_MINUTES)
            protection_end = event_time + timedelta(minutes=NEWS_PROTECTION_MINUTES)
            
            # Check if current time is in protection window
            if protection_start <= now <= protection_end:
                print(f"🚫 News protection active: {event.get('title', 'High-impact news')}")
                print(f"   Protection window: {protection_start.strftime('%H:%M')} - {protection_end.strftime('%H:%M')}")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error checking news protection: {e}")
        return False

def get_macro_sentiment(symbol):
    """Get macro sentiment for a symbol (existing function)"""
    try:
        # Your existing macro sentiment logic here
        return "neutral"
    except Exception as e:
        print(f"❌ Error getting macro sentiment: {e}")
        return "neutral"

def check_news_before_trade(symbol):
    """
    Check if it's safe to trade given current news conditions
    Returns (can_trade, reason)
    """
    if is_news_protection_active():
        return False, "High-impact news protection active"
    
    return True, "No news restrictions"

# Enhanced news protection with time-based blocking
def should_block_trading():
    """
    Main function to check if trading should be blocked due to news
    Returns True if trading should be blocked
    """
    return is_news_protection_active()
