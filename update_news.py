#!/usr/bin/env python3
# ------------------------------------------------------------------------------------
# 📰 update_news.py – News Filter Update Utility
#
# This script helps update the high_impact_news.json file with today's events.
# Usage:
#   - For no news days: python update_news.py --clear
#   - For adding events: python update_news.py --add "Event Name" "Time" "Currency"
#   - For viewing events: python update_news.py --show
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot - News Management
# ------------------------------------------------------------------------------------

import json
import argparse
from datetime import datetime, time

def load_current_news():
    """Load current news events"""
    try:
        with open("high_impact_news.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading news: {e}")
        return []

def save_news_events(events):
    """Save news events to file"""
    try:
        with open("high_impact_news.json", "w") as f:
            json.dump(events, f, indent=2)
        print(f"✅ Successfully updated news file with {len(events)} events")
        return True
    except Exception as e:
        print(f"❌ Error saving news: {e}")
        return False

def clear_news():
    """Clear all events for a no-news day"""
    today = datetime.now().strftime("%Y-%m-%d")
    no_news_entry = [{
        "event": "No High-Impact Events Today",
        "datetime": f"{today}T12:00:00",
        "currency": "N/A",
        "impact": "None",
        "forecast": None,
        "previous": None,
        "actual": None,
        "outcome": "Clear trading conditions",
        "strength": "No News",
        "category": "Market Status",
        "note": f"Updated for {today} - No major economic events scheduled"
    }]
    
    if save_news_events(no_news_entry):
        print(f"📈 News filter cleared for {today} - trading unrestricted")

def add_news_event(event_name, event_time, currency, impact="High"):
    """Add a high-impact news event"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Parse time (accept formats like "14:30" or "2:30 PM")
    try:
        if ":" in event_time:
            if "PM" in event_time.upper() or "AM" in event_time.upper():
                # 12-hour format
                event_time_obj = datetime.strptime(event_time.upper(), "%I:%M %p").time()
            else:
                # 24-hour format
                event_time_obj = datetime.strptime(event_time, "%H:%M").time()
        else:
            raise ValueError("Invalid time format")
    except Exception as e:
        print(f"❌ Invalid time format '{event_time}'. Use HH:MM or HH:MM AM/PM")
        return
    
    # Create datetime string
    datetime_str = f"{today}T{event_time_obj.strftime('%H:%M')}:00"
    
    # Load existing events
    events = load_current_news()
    
    # Remove "no news" placeholder if it exists
    events = [e for e in events if e.get("category") != "Market Status"]
    
    # Add new event
    new_event = {
        "event": event_name,
        "datetime": datetime_str,
        "currency": currency.upper(),
        "impact": impact,
        "forecast": None,
        "previous": None,
        "actual": None,
        "outcome": "",
        "strength": "Strong Data",
        "category": "Economic Data"
    }
    
    events.append(new_event)
    
    if save_news_events(events):
        print(f"📰 Added event: {event_name} at {event_time} ({currency})")

def show_news():
    """Display current news events"""
    events = load_current_news()
    if not events:
        print("📭 No news events found")
        return
    
    print(f"\n📰 Current News Events ({len(events)}):")
    print("-" * 60)
    
    for i, event in enumerate(events, 1):
        event_time = datetime.fromisoformat(event['datetime']).strftime('%H:%M')
        print(f"{i}. {event['event']}")
        print(f"   Time: {event_time} | Currency: {event['currency']} | Impact: {event['impact']}")
        if event.get('note'):
            print(f"   Note: {event['note']}")
        print()

def main():
    parser = argparse.ArgumentParser(description="Update news filter for D.E.V.I Trading Bot")
    parser.add_argument("--clear", action="store_true", help="Clear all events (no news day)")
    parser.add_argument("--add", nargs=3, metavar=("EVENT", "TIME", "CURRENCY"), 
                       help="Add news event: 'Event Name' 'HH:MM' 'USD'")
    parser.add_argument("--show", action="store_true", help="Show current events")
    
    args = parser.parse_args()
    
    if args.clear:
        clear_news()
    elif args.add:
        add_news_event(args.add[0], args.add[1], args.add[2])
    elif args.show:
        show_news()
    else:
        # Default: show current events
        print("📰 D.E.V.I News Filter Manager")
        print("=" * 40)
        show_news()
        print("\nUsage:")
        print("  python update_news.py --clear              # Clear for no-news day")
        print("  python update_news.py --add 'NFP' '14:30' 'USD'  # Add event")
        print("  python update_news.py --show               # Show current events")

if __name__ == "__main__":
    main()
