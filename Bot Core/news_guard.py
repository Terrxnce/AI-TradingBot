import MetaTrader5 as mt5
from datetime import datetime, timedelta
import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import CONFIG

# Cache for news events to prevent multiple loads
_news_events_cache = None
_news_cache_timestamp = None

def get_news_protection_minutes():
    """Get news protection window from config"""
    return CONFIG.get("news_protection_minutes", 30)  # Default 30 minutes

def get_news_protection_enabled():
    """Check if news protection is enabled"""
    return CONFIG.get("enable_news_protection", True)

def get_high_impact_news():
    """
    Get high-impact news events from manually updated JSON file
    Uses caching to prevent multiple loads during initialization
    """
    global _news_events_cache, _news_cache_timestamp
    
    # Check if we have recent cache (within 5 minutes)
    now = datetime.now()
    if (_news_events_cache is not None and 
        _news_cache_timestamp is not None and 
        (now - _news_cache_timestamp).total_seconds() < 300):  # 5 minutes cache
        return _news_events_cache
    
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
                        # Update cache
                        _news_events_cache = events
                        _news_cache_timestamp = now
                        return events
            except Exception as e:
                print(f"⚠️ Error loading from {file_path}: {e}")
                continue
        
        print("⚠️ No news data available - trading without news protection")
        _news_events_cache = []
        _news_cache_timestamp = now
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
        'EURUSD': ('EUR', 'USD'), 'GBPUSD': ('GBP', 'USD'), 'USDJPY': ('USD', 'JPY'),
        'USDCHF': ('USD', 'CHF'), 'AUDUSD': ('AUD', 'USD'), 'USDCAD': ('USD', 'CAD'),
        'NZDUSD': ('NZD', 'USD'), 'EURJPY': ('EUR', 'JPY'), 'GBPJPY': ('GBP', 'JPY'),
        'EURGBP': ('EUR', 'GBP'), 'AUDCAD': ('AUD', 'CAD'), 'CADJPY': ('CAD', 'JPY'),
        'NZDJPY': ('NZD', 'JPY'), 'GBPAUD': ('GBP', 'AUD'), 'EURAUD': ('EUR', 'AUD'),
        'GBPNZD': ('GBP', 'NZD'), 'EURNZD': ('EUR', 'NZD'), 'AUDNZD': ('AUD', 'NZD'),
        'GBPCAD': ('GBP', 'CAD'), 'EURCAD': ('EUR', 'CAD'), 'AUDCHF': ('AUD', 'CHF'),
        'CADCHF': ('CAD', 'CHF'), 'NZDCHF': ('NZD', 'CHF'), 'GBPCHF': ('GBP', 'CHF'),
        'EURCHF': ('EUR', 'CHF'), 'CHFJPY': ('CHF', 'JPY'),
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

def is_trading_blocked_by_news(symbol=None):
    """
    🎯 MAIN FUNCTION: Check if trading should be blocked due to news
    
    Args:
        symbol (str, optional): Specific symbol to check. If None, checks all symbols.
    
    Returns:
        bool: True if trading should be blocked
        str: Reason for blocking (if blocked)
    """
    # Check if news protection is enabled
    if not get_news_protection_enabled():
        return False, "News protection disabled"
    
    # Get impact filter from config
    impact_filter = CONFIG.get("news_impact_filter", ["High"])
    
    # Check if auto-disable is enabled and no real news events exist
    if CONFIG.get("auto_disable_on_no_news", True):
        events = get_high_impact_news()
        if events and all(event.get("impact") == "None" or event.get("category") == "Market Status" for event in events):
            return False, "No high-impact news today - protection auto-disabled"
    
    try:
        now = datetime.now()
        events = get_high_impact_news()
        protection_minutes = get_news_protection_minutes()
        
        if not events:
            return False, "No news events found"
        
        # Check each event
        for event in events:
            try:
                event_time_str = event.get('datetime')
                if not event_time_str:
                    continue
                
                event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                protection_start = event_time - timedelta(minutes=protection_minutes)
                protection_end = event_time + timedelta(minutes=protection_minutes)
                
                # Check if current time is in protection window
                if protection_start <= now <= protection_end:
                    event_currency = event.get('currency', '').upper()
                    event_impact = event.get('impact', 'High')
                    
                    # Check if event impact matches our filter
                    if event_impact not in impact_filter:
                        continue  # Skip this event if impact doesn't match filter
                    
                    # If no specific symbol, block all trading
                    if symbol is None:
                        print(f"🚫 News protection active:")
                        print(f"   Event: {event.get('event', 'High-impact news')}")
                        print(f"   Currency: {event_currency}")
                        print(f"   Impact: {event_impact}")
                        print(f"   Event time: {event_time.strftime('%Y-%m-%d %H:%M')} UTC")
                        print(f"   Protection window: {protection_start.strftime('%H:%M')} - {protection_end.strftime('%H:%M')} UTC")
                        print(f"   Current time: {now.strftime('%H:%M')} UTC")
                        return True, f"News protection: {event.get('event', 'High-impact news')}"
                    
                    # If specific symbol, check currency match
                    base_currency, quote_currency = extract_currencies_from_symbol(symbol)
                    if event_currency in [base_currency, quote_currency]:
                        print(f"🚫 News protection active for {symbol}:")
                        print(f"   Event: {event.get('event', 'High-impact news')}")
                        print(f"   Currency: {event_currency}")
                        print(f"   Impact: {event_impact}")
                        print(f"   Event time: {event_time.strftime('%Y-%m-%d %H:%M')} UTC")
                        print(f"   Protection window: {protection_start.strftime('%H:%M')} - {protection_end.strftime('%H:%M')} UTC")
                        print(f"   Current time: {now.strftime('%H:%M')} UTC")
                        return True, f"News protection for {symbol}: {event.get('event', 'High-impact news')}"
            
            except Exception as e:
                print(f"⚠️ Error processing news event: {e}")
                continue
        
        return False, "No news restrictions"
        
    except Exception as e:
        print(f"❌ Error checking news protection: {e}")
        return False, f"Error: {e}"

def get_macro_sentiment(symbol):
    """Get macro sentiment for a symbol (existing function)"""
    try:
        # Your existing macro sentiment logic here
        return "neutral"
    except Exception as e:
        print(f"❌ Error getting macro sentiment: {e}")
        return "neutral"

def refresh_news_data():
    """
    Refresh news data by reloading the manually updated JSON file
    """
    global _news_events_cache, _news_cache_timestamp
    
    try:
        print("🔄 Reloading manually updated news data...")
        # Clear cache to force reload
        _news_events_cache = None
        _news_cache_timestamp = None
        
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

# 🎯 SIMPLIFIED INTERFACE FUNCTIONS (for backward compatibility)
def should_block_trading():
    """Check if trading should be blocked (all symbols)"""
    blocked, reason = is_trading_blocked_by_news()
    return blocked

def is_news_protection_active():
    """Check if news protection is active (all symbols)"""
    blocked, reason = is_trading_blocked_by_news()
    return blocked

def check_news_before_trade(symbol):
    """Check if it's safe to trade a specific symbol"""
    blocked, reason = is_trading_blocked_by_news(symbol)
    return not blocked, reason

def is_trade_blocked_by_news(symbol, events, now):
    """Legacy function - redirects to new system"""
    blocked, reason = is_trading_blocked_by_news(symbol)
    return blocked
