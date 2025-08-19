import MetaTrader5 as mt5
from datetime import datetime, timedelta
import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import CONFIG

def get_news_protection_minutes():
    """Get news protection window from config"""
    return CONFIG.get("news_protection_minutes", 30)  # Default 30 minutes

def get_news_protection_enabled():
    """Check if news protection is enabled"""
    return CONFIG.get("enable_news_protection", True)

def get_high_impact_news():
    """
    Get high-impact news events from manually updated JSON file
    """
    try:
        # Load from manually updated JSON file
        possible_paths = [
            "high_impact_news.json",  # Current directory
            "../high_impact_news.json",  # Parent directory
            "Bot Core/high_impact_news.json",  # Bot Core subdirectory
        ]
        
        for file_path in possible_paths:
            try:
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        events = json.load(f)
                    if events:
                        print(f"📰 Loaded {len(events)} high-impact events from {file_path}")
                        return events
            except Exception as e:
                print(f"⚠️ Error loading from {file_path}: {e}")
                continue
        
        print("⚠️ No news data available - trading without news protection")
        return []
        
    except Exception as e:
        print(f"❌ Error loading high-impact news: {e}")
        return []

def extract_currencies_from_symbol(symbol):
    """
    Extract base and quote currencies from a trading symbol
    Returns tuple of (base_currency, quote_currency)
    """
    # Common currency pairs
    currency_pairs = {
        'EURUSD': ('EUR', 'USD'),
        'GBPUSD': ('GBP', 'USD'),
        'USDJPY': ('USD', 'JPY'),
        'USDCHF': ('USD', 'CHF'),
        'AUDUSD': ('AUD', 'USD'),
        'USDCAD': ('USD', 'CAD'),
        'NZDUSD': ('NZD', 'USD'),
        'EURJPY': ('EUR', 'JPY'),
        'GBPJPY': ('GBP', 'JPY'),
        'EURGBP': ('EUR', 'GBP'),
        'AUDCAD': ('AUD', 'CAD'),
        'CADJPY': ('CAD', 'JPY'),
        'NZDJPY': ('NZD', 'JPY'),
        'GBPAUD': ('GBP', 'AUD'),
        'EURAUD': ('EUR', 'AUD'),
        'GBPNZD': ('GBP', 'NZD'),
        'EURNZD': ('EUR', 'NZD'),
        'AUDNZD': ('AUD', 'NZD'),
        'GBPCAD': ('GBP', 'CAD'),
        'EURCAD': ('EUR', 'CAD'),
        'AUDCHF': ('AUD', 'CHF'),
        'CADCHF': ('CAD', 'CHF'),
        'NZDCHF': ('NZD', 'CHF'),
        'GBPCHF': ('GBP', 'CHF'),
        'EURCHF': ('EUR', 'CHF'),
        'CHFJPY': ('CHF', 'JPY'),
    }
    
    # Check if it's a known currency pair
    if symbol.upper() in currency_pairs:
        return currency_pairs[symbol.upper()]
    
    # Try to extract from symbol (e.g., "EURUSD" -> "EUR", "USD")
    if len(symbol) >= 6:
        base = symbol[:3].upper()
        quote = symbol[3:6].upper()
        return (base, quote)
    
    # Default fallback
    return ('USD', 'USD')

def is_trade_blocked_by_news(symbol, events, now):
    """
    Check if a trade should be blocked due to high-impact news
    Returns True if trade should be blocked
    """
    if not events:
        return False
    
    # Extract currencies from symbol
    base_currency, quote_currency = extract_currencies_from_symbol(symbol)
    
    # Get protection window
    protection_minutes = get_news_protection_minutes()
    
    for event in events:
        try:
            # Parse event datetime
            event_time_str = event.get('datetime')
            if not event_time_str:
                continue
            
            event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
            
            # Calculate protection window
            protection_start = event_time - timedelta(minutes=protection_minutes)
            protection_end = event_time + timedelta(minutes=protection_minutes)
            
            # Check if current time is in protection window
            if protection_start <= now <= protection_end:
                # Check if event currency matches symbol currencies
                event_currency = event.get('currency', '').upper()
                if event_currency in [base_currency, quote_currency]:
                    print(f"🚫 News protection active for {symbol}:")
                    print(f"   Event: {event.get('event', 'High-impact news')}")
                    print(f"   Currency: {event_currency}")
                    print(f"   Event time: {event_time.strftime('%Y-%m-%d %H:%M')}")
                    print(f"   Protection window: {protection_start.strftime('%H:%M')} - {protection_end.strftime('%H:%M')}")
                    print(f"   Current time: {now.strftime('%H:%M')}")
                    return True
        
        except Exception as e:
            print(f"⚠️ Error processing news event: {e}")
            continue
    
    return False

def is_news_protection_active():
    """
    Check if we're in a news protection window (30min before/after high-impact news)
    Returns True if trading should be blocked due to news
    """
    # Check if news protection is enabled
    if not get_news_protection_enabled():
        return False
    
    try:
        # Get current time
        now = datetime.now()
        
        # Get high-impact news events
        news_events = get_high_impact_news()
        
        # Check if any event is blocking trading
        for event in news_events:
            try:
                event_time_str = event.get('datetime')
                if not event_time_str:
                    continue
                
                event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                protection_minutes = get_news_protection_minutes()
                
                # Calculate protection window
                protection_start = event_time - timedelta(minutes=protection_minutes)
                protection_end = event_time + timedelta(minutes=protection_minutes)
                
                # Check if current time is in protection window
                if protection_start <= now <= protection_end:
                    print(f"🚫 News protection active: {event.get('event', 'High-impact news')}")
                    print(f"   Protection window: {protection_start.strftime('%H:%M')} - {protection_end.strftime('%H:%M')}")
                    print(f"   Current time: {now.strftime('%H:%M')}")
                    return True
            
            except Exception as e:
                print(f"⚠️ Error processing news event: {e}")
                continue
        
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
    if not get_news_protection_enabled():
        return True, "News protection disabled"
    
    if is_news_protection_active():
        return False, "High-impact news protection active"
    
    return True, "No news restrictions"

def should_block_trading():
    """
    Main function to check if trading should be blocked due to news
    Returns True if trading should be blocked
    """
    # Check if auto-disable is enabled and no real news events exist
    if CONFIG.get("auto_disable_on_no_news", True):
        events = get_high_impact_news()
        # Check if events are just placeholder/no-news entries
        if events and all(event.get("impact") == "None" or event.get("category") == "Market Status" for event in events):
            print("📈 No high-impact news today - news protection auto-disabled")
            return False
    
    return is_news_protection_active()

def refresh_news_data():
    """
    Refresh news data by reloading the manually updated JSON file
    """
    try:
        print("🔄 Reloading manually updated news data...")
        events = get_high_impact_news()
        if events:
            print(f"✅ Successfully reloaded {len(events)} news events")
            return True
        else:
            print("⚠️ No news events found in manual JSON file")
            return False
    except Exception as e:
        print(f"❌ Error refreshing news data: {e}")
        return False

def get_upcoming_news_events(hours_ahead=24):
    """
    Get upcoming news events within specified hours
    """
    try:
        events = get_high_impact_news()
        now = datetime.now()
        
        upcoming = []
        for event in events:
            try:
                event_time = datetime.fromisoformat(event['datetime'].replace('Z', '+00:00'))
                if event_time > now and (event_time - now).total_seconds() <= hours_ahead * 3600:
                    upcoming.append(event)
            except:
                continue
        
        return sorted(upcoming, key=lambda x: x['datetime'])
        
    except Exception as e:
        print(f"❌ Error getting upcoming events: {e}")
        return []
