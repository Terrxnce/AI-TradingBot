#!/usr/bin/env python3
"""
Forex Factory Economic Calendar Scraper
Extracts high-impact (red folder) economic events for news protection
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import os
import time
import re

def scrape_forex_factory_calendar():
    """
    Scrape Forex Factory economic calendar for high-impact events
    Returns list of high-impact events in required format
    """
    try:
        # Forex Factory calendar URL
        url = "https://www.forexfactory.com/calendar"
        
        # Headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        print("🌐 Fetching Forex Factory calendar...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find calendar table
        calendar_table = soup.find('table', {'class': 'calendar__table'})
        if not calendar_table:
            print("❌ Could not find calendar table on Forex Factory")
            return []
        
        high_impact_events = []
        
        # Find all calendar rows
        rows = calendar_table.find_all('tr', {'class': 'calendar__row'})
        
        for row in rows:
            try:
                # Check for high impact (red folder)
                impact_cell = row.find('td', {'class': 'calendar__impact'})
                if not impact_cell:
                    continue
                
                # Look for red folder icon (high impact)
                red_folder = impact_cell.find('span', {'class': 'icon--ff-impact-red'})
                if not red_folder:
                    continue
                
                # Extract event details
                event_cell = row.find('td', {'class': 'calendar__event'})
                if not event_cell:
                    continue
                
                event_name = event_cell.get_text(strip=True)
                if not event_name:
                    continue
                
                # Extract currency
                currency_cell = row.find('td', {'class': 'calendar__currency'})
                currency = currency_cell.get_text(strip=True) if currency_cell else "USD"
                
                # Extract date/time
                date_cell = row.find('td', {'class': 'calendar__date'})
                if not date_cell:
                    continue
                
                # Parse date and time
                date_text = date_cell.get_text(strip=True)
                event_datetime = parse_forex_factory_datetime(date_text)
                
                if event_datetime:
                    event_data = {
                        "event": event_name,
                        "datetime": event_datetime.isoformat(),
                        "currency": currency,
                        "impact": "High"
                    }
                    high_impact_events.append(event_data)
                    print(f"📅 Found high-impact event: {event_name} ({currency}) at {event_datetime}")
                
            except Exception as e:
                print(f"⚠️ Error parsing row: {e}")
                continue
        
        print(f"✅ Found {len(high_impact_events)} high-impact events")
        return high_impact_events
        
    except Exception as e:
        print(f"❌ Error scraping Forex Factory: {e}")
        return []

def parse_forex_factory_datetime(date_text):
    """
    Parse Forex Factory date/time format
    Returns datetime object or None if parsing fails
    """
    try:
        # Remove extra whitespace
        date_text = date_text.strip()
        
        # Handle different date formats
        now = datetime.now()
        
        # Pattern 1: "Today 14:30" or "Tomorrow 14:30"
        if "Today" in date_text:
            time_part = date_text.replace("Today", "").strip()
            time_obj = datetime.strptime(time_part, "%H:%M").time()
            return datetime.combine(now.date(), time_obj)
        
        elif "Tomorrow" in date_text:
            time_part = date_text.replace("Tomorrow", "").strip()
            time_obj = datetime.strptime(time_part, "%H:%M").time()
            tomorrow = now.date() + timedelta(days=1)
            return datetime.combine(tomorrow, time_obj)
        
        # Pattern 2: "Dec 15 14:30" or "15 Dec 14:30"
        elif re.match(r'\w{3}\s+\d{1,2}\s+\d{1,2}:\d{2}', date_text):
            # Try "Dec 15 14:30" format
            try:
                return datetime.strptime(date_text, "%b %d %H:%M").replace(year=now.year)
            except:
                pass
            
            # Try "15 Dec 14:30" format
            try:
                return datetime.strptime(date_text, "%d %b %H:%M").replace(year=now.year)
            except:
                pass
        
        # Pattern 3: Full date "2024-12-15 14:30"
        elif re.match(r'\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}', date_text):
            return datetime.strptime(date_text, "%Y-%m-%d %H:%M")
        
        print(f"⚠️ Could not parse date format: {date_text}")
        return None
        
    except Exception as e:
        print(f"❌ Error parsing datetime '{date_text}': {e}")
        return None

def save_high_impact_news(events):
    """
    Save high-impact events to JSON file
    """
    try:
        output_file = "high_impact_news.json"
        
        with open(output_file, 'w') as f:
            json.dump(events, f, indent=2)
        
        print(f"💾 Saved {len(events)} events to {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving events: {e}")
        return False

def load_high_impact_news():
    """
    Load high-impact events from JSON file
    """
    try:
        output_file = "high_impact_news.json"
        
        if not os.path.exists(output_file):
            return []
        
        with open(output_file, 'r') as f:
            events = json.load(f)
        
        return events
        
    except Exception as e:
        print(f"❌ Error loading events: {e}")
        return []

def main():
    """
    Main function to scrape and save high-impact events
    """
    print("🚀 Starting Forex Factory Economic Calendar Scraper")
    print("=" * 50)
    
    # Scrape high-impact events
    events = scrape_forex_factory_calendar()
    
    if events:
        # Save to JSON file
        if save_high_impact_news(events):
            print("✅ Scraping completed successfully!")
            
            # Display summary
            print("\n📊 Summary:")
            print(f"   Total high-impact events: {len(events)}")
            
            # Group by currency
            currency_counts = {}
            for event in events:
                currency = event.get('currency', 'Unknown')
                currency_counts[currency] = currency_counts.get(currency, 0) + 1
            
            print("   Events by currency:")
            for currency, count in currency_counts.items():
                print(f"     {currency}: {count}")
            
            # Show next few events
            print("\n📅 Next events:")
            sorted_events = sorted(events, key=lambda x: x['datetime'])
            for i, event in enumerate(sorted_events[:5]):
                dt = datetime.fromisoformat(event['datetime'])
                print(f"     {i+1}. {event['event']} ({event['currency']}) - {dt.strftime('%Y-%m-%d %H:%M')}")
        else:
            print("❌ Failed to save events")
    else:
        print("❌ No high-impact events found")
    
    print("\n" + "=" * 50)
    print("🏁 Scraping process completed")

if __name__ == "__main__":
    main() 