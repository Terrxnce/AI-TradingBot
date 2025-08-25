# ------------------------------------------------------------------------------------
# 🧪 test_news_protection.py – Test News Protection System
#
# Tests the news protection system with Fed Chair Powell event
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import sys
import os
from datetime import datetime, timedelta

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'Bot Core'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))

from news_guard import get_high_impact_news, is_trading_blocked_by_news

def test_news_protection():
    """Test news protection system"""
    
    print("🧪 TESTING NEWS PROTECTION SYSTEM")
    print("=" * 50)
    
    # Test 1: Load news events
    print("\n📋 Test 1: Loading News Events")
    print("-" * 40)
    
    events = get_high_impact_news()
    print(f"✅ Loaded {len(events)} news events:")
    
    for event in events:
        print(f"   📰 {event['event']} - {event['datetime']} ({event['currency']})")
    
    # Test 2: Check Fed Chair Powell event
    print("\n📋 Test 2: Fed Chair Powell Event")
    print("-" * 40)
    
    powell_event = None
    for event in events:
        if "Powell" in event['event']:
            powell_event = event
            break
    
    if powell_event:
        print(f"✅ Found Fed Chair Powell event:")
        print(f"   📅 Date: {powell_event['datetime']}")
        print(f"   💰 Currency: {powell_event['currency']}")
        print(f"   ⚡ Impact: {powell_event['impact']}")
        print(f"   📂 Category: {powell_event['category']}")
    else:
        print("❌ Fed Chair Powell event not found!")
        return
    
    # Test 3: Check protection windows
    print("\n📋 Test 3: Protection Windows")
    print("-" * 40)
    
    # Parse the event time
    event_time = datetime.fromisoformat(powell_event['datetime'].replace('Z', '+00:00'))
    protection_minutes = 20  # From config
    
    # Calculate protection windows
    protection_start = event_time - timedelta(minutes=protection_minutes)
    protection_end = event_time + timedelta(minutes=protection_minutes)
    
    print(f"📰 Event Time: {event_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"🛡️ Protection Start: {protection_start.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"🛡️ Protection End: {protection_end.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"⏱️ Protection Duration: {protection_minutes * 2} minutes total")
    
    # Test 4: Check Irish time conversion
    print("\n📋 Test 4: Irish Time Conversion")
    print("-" * 40)
    
    # Irish time is UTC+1 in summer
    irish_event_time = event_time + timedelta(hours=1)
    irish_protection_start = protection_start + timedelta(hours=1)
    irish_protection_end = protection_end + timedelta(hours=1)
    
    print(f"🇮🇪 Event Time (Irish): {irish_event_time.strftime('%Y-%m-%d %H:%M Irish')}")
    print(f"🇮🇪 Protection Start (Irish): {irish_protection_start.strftime('%Y-%m-%d %H:%M Irish')}")
    print(f"🇮🇪 Protection End (Irish): {irish_protection_end.strftime('%Y-%m-%d %H:%M Irish')}")
    
    # Test 5: Test trading block scenarios
    print("\n📋 Test 5: Trading Block Scenarios")
    print("-" * 40)
    
    # Test during protection window
    test_time = event_time  # Exactly at event time
    print(f"🕐 Testing at event time: {test_time.strftime('%H:%M UTC')}")
    
    # Mock the current time for testing
    import time
    original_time = time.time
    
    def mock_time():
        return test_time.timestamp()
    
    time.time = mock_time
    
    try:
        blocked, reason = is_trading_blocked_by_news("USDJPY")
        print(f"   USDJPY Trading: {'❌ BLOCKED' if blocked else '✅ ALLOWED'}")
        if blocked:
            print(f"   Reason: {reason}")
        
        blocked, reason = is_trading_blocked_by_news("EURUSD")
        print(f"   EURUSD Trading: {'❌ BLOCKED' if blocked else '✅ ALLOWED'}")
        if blocked:
            print(f"   Reason: {reason}")
            
        blocked, reason = is_trading_blocked_by_news("AUDJPY")
        print(f"   AUDJPY Trading: {'❌ BLOCKED' if blocked else '✅ ALLOWED'}")
        if blocked:
            print(f"   Reason: {reason}")
            
    finally:
        time.time = original_time
    
    print("\n" + "=" * 50)
    print("✅ News Protection Test Complete!")

if __name__ == "__main__":
    test_news_protection()
