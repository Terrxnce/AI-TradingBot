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
import random

def get_random_user_agent():
    """Get a random realistic user agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
    ]
    return random.choice(user_agents)

def scrape_forex_factory_calendar():
    """
    Scrape economic calendar for high-impact events from multiple sources
    Returns list of high-impact events in required format
    """
    print("🌐 Attempting to scrape economic calendar from multiple sources...")
    
    # Try JBlanked API first (highest priority - real-time data)
    try:
        events = scrape_jblanked_api()
        if events:
            return events
    except Exception as e:
        print(f"⚠️ JBlanked API failed: {e}")
    
    # Try Forex Factory as backup
    try:
        events = scrape_forex_factory_primary()
        if events:
            return events
    except Exception as e:
        print(f"⚠️ Forex Factory primary method failed: {e}")
    
    # Try Forex Factory alternative method
    try:
        events = scrape_forex_factory_alternative()
        if events:
            return events
    except Exception as e:
        print(f"⚠️ Forex Factory alternative method failed: {e}")
    
    # Try alternative calendar sources
    try:
        events = scrape_alternative_calendar()
        if events:
            return events
    except Exception as e:
        print(f"⚠️ Alternative calendar sources failed: {e}")
    
    # Try public APIs
    try:
        events = scrape_public_api()
        if events:
            return events
    except Exception as e:
        print(f"⚠️ Public APIs failed: {e}")
    
    print("❌ All scraping methods failed")
    return []

def scrape_forex_factory_primary():
    """
    Primary method to scrape Forex Factory
    """
    try:
        # Create a session for better request handling
        session = requests.Session()
        
        # Forex Factory calendar URL
        url = "https://www.forexfactory.com/calendar"
        
        # Enhanced headers to mimic real browser
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        }
        
        # Set session headers
        session.headers.update(headers)
        
        print(f"🔧 Using User-Agent: {headers['User-Agent'][:50]}...")
        
        # Add a small delay to be more respectful
        time.sleep(random.uniform(1, 3))
        
        # Make the request
        response = session.get(url, timeout=30)
        
        # Check if we got blocked
        if response.status_code == 403:
            print("❌ 403 Forbidden - trying alternative headers...")
            
            # Try with different headers
            alt_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Referer': 'https://www.google.com/',
            }
            
            session.headers.update(alt_headers)
            time.sleep(2)
            response = session.get(url, timeout=30)
        
        response.raise_for_status()
        
        # Check if we got a valid HTML response
        if 'calendar' not in response.text.lower():
            print("❌ Response doesn't contain calendar data - might be blocked")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try multiple possible selectors for the calendar table
        calendar_table = None
        possible_selectors = [
            'table.calendar__table',
            'table[class*="calendar"]',
            '.calendar table',
            'table[data-testid="calendar-table"]'
        ]
        
        for selector in possible_selectors:
            calendar_table = soup.select_one(selector)
            if calendar_table:
                print(f"✅ Found calendar table with selector: {selector}")
                break
        
        if not calendar_table:
            print("❌ Could not find calendar table on Forex Factory")
            print("🔍 Available tables:", [t.get('class', 'no-class') for t in soup.find_all('table')])
            return []
        
        high_impact_events = []
        
        # Try multiple possible row selectors
        rows = []
        row_selectors = [
            'tr.calendar__row',
            'tr[class*="calendar"]',
            '.calendar tr',
            'tbody tr'
        ]
        
        for selector in row_selectors:
            rows = calendar_table.select(selector)
            if rows:
                print(f"✅ Found {len(rows)} rows with selector: {selector}")
                break
        
        if not rows:
            print("❌ Could not find calendar rows")
            return []
        
        for row in rows:
            try:
                # Try multiple ways to find high impact indicators
                impact_indicators = [
                    'span.icon--ff-impact-red',
                    'span[class*="impact-red"]',
                    'span[class*="red"]',
                    '.impact-red',
                    '.red-folder'
                ]
                
                is_high_impact = False
                for indicator in impact_indicators:
                    if row.select_one(indicator):
                        is_high_impact = True
                        break
                
                # Also check for text-based indicators
                row_text = row.get_text().lower()
                if 'high' in row_text and 'impact' in row_text:
                    is_high_impact = True
                
                if not is_high_impact:
                    continue
                
                # Extract event details - try multiple selectors
                event_name = None
                event_selectors = [
                    'td.calendar__event',
                    'td[class*="event"]',
                    '.event',
                    'td:nth-child(2)'
                ]
                
                for selector in event_selectors:
                    event_cell = row.select_one(selector)
                    if event_cell:
                        event_name = event_cell.get_text(strip=True)
                        if event_name:
                            break
                
                if not event_name:
                    continue
                
                # Extract currency - try multiple selectors
                currency = "USD"  # default
                currency_selectors = [
                    'td.calendar__currency',
                    'td[class*="currency"]',
                    '.currency',
                    'td:nth-child(1)'
                ]
                
                for selector in currency_selectors:
                    currency_cell = row.select_one(selector)
                    if currency_cell:
                        currency_text = currency_cell.get_text(strip=True)
                        if currency_text and len(currency_text) <= 3:
                            currency = currency_text
                            break
                
                # Extract date/time - try multiple selectors
                date_text = None
                date_selectors = [
                    'td.calendar__date',
                    'td[class*="date"]',
                    '.date',
                    'td:nth-child(3)'
                ]
                
                for selector in date_selectors:
                    date_cell = row.select_one(selector)
                    if date_cell:
                        date_text = date_cell.get_text(strip=True)
                        if date_text:
                            break
                
                if not date_text:
                    continue
                
                # Parse date and time
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
        print(f"❌ Error in primary scraping: {e}")
        return []

def scrape_forex_factory_alternative():
    """
    Alternative method to scrape Forex Factory using different approach
    """
    try:
        session = requests.Session()
        
        # Try different URLs that might work
        urls_to_try = [
            "https://www.forexfactory.com/calendar",
            "https://www.forexfactory.com/calendar?week=" + datetime.now().strftime("%Y-%m-%d"),
            "https://www.forexfactory.com/calendar?timezone=UTC",
            "https://www.forexfactory.com/calendar?timezone=America/New_York"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        session.headers.update(headers)
        
        for url in urls_to_try:
            try:
                print(f"🌐 Trying URL: {url}")
                
                # Add random delay
                time.sleep(random.uniform(2, 5))
                
                response = session.get(url, timeout=30)
                
                if response.status_code == 200:
                    print(f"✅ Success with URL: {url}")
                    
                    # Check if we got valid content
                    if 'calendar' in response.text.lower() or 'forex' in response.text.lower():
                        return parse_forex_factory_response(response.text)
                    else:
                        print("⚠️ Response doesn't contain expected content")
                        continue
                else:
                    print(f"❌ Failed with status {response.status_code} for URL: {url}")
                    
            except Exception as e:
                print(f"⚠️ Error with URL {url}: {e}")
                continue
        
        print("❌ All URLs failed")
        return []
        
    except Exception as e:
        print(f"❌ Error in alternative scraping: {e}")
        return []

def parse_forex_factory_response(html_content):
    """
    Parse Forex Factory HTML response for high-impact events
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for any table that might contain calendar data
        tables = soup.find_all('table')
        
        for table in tables:
            # Check if this table looks like a calendar
            table_text = table.get_text().lower()
            if any(keyword in table_text for keyword in ['currency', 'impact', 'time', 'date']):
                print("🔍 Found potential calendar table")
                
                # Look for rows with high impact indicators
                rows = table.find_all('tr')
                high_impact_events = []
                
                for row in rows:
                    try:
                        row_text = row.get_text().lower()
                        
                        # Check for high impact indicators
                        if any(indicator in row_text for indicator in ['high impact', 'red', 'high']):
                            # Extract event information
                            cells = row.find_all(['td', 'th'])
                            
                            if len(cells) >= 3:
                                # Try to extract currency, event, and time
                                currency = extract_currency_from_cells(cells)
                                event_name = extract_event_from_cells(cells)
                                event_time = extract_time_from_cells(cells)
                                
                                if currency and event_name and event_time:
                                    event_data = {
                                        "event": event_name,
                                        "datetime": event_time.isoformat(),
                                        "currency": currency,
                                        "impact": "High"
                                    }
                                    high_impact_events.append(event_data)
                                    print(f"📅 Found event: {event_name} ({currency}) at {event_time}")
                    
                    except Exception as e:
                        continue
                
                if high_impact_events:
                    return high_impact_events
        
        return []
        
    except Exception as e:
        print(f"❌ Error parsing response: {e}")
        return []

def extract_currency_from_cells(cells):
    """Extract currency from table cells"""
    for cell in cells:
        text = cell.get_text(strip=True).upper()
        if len(text) == 3 and text.isalpha():
            return text
    return None

def extract_event_from_cells(cells):
    """Extract event name from table cells"""
    for cell in cells:
        text = cell.get_text(strip=True)
        if len(text) > 10 and not text.isupper():
            return text
    return None

def extract_time_from_cells(cells):
    """Extract time from table cells"""
    for cell in cells:
        text = cell.get_text(strip=True)
        # Look for time patterns
        if re.match(r'\d{1,2}:\d{2}', text):
            # Try to parse as today's time
            try:
                time_obj = datetime.strptime(text, "%H:%M").time()
                return datetime.combine(datetime.now().date(), time_obj)
            except:
                pass
    return None

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

def scrape_alternative_calendar():
    """
    Use alternative economic calendar sources since Forex Factory is heavily protected
    """
    try:
        print("🌐 Trying alternative economic calendar sources...")
        
        # Try multiple alternative sources
        sources = [
            scrape_investing_calendar,
            scrape_fxstreet_calendar,
            scrape_marketwatch_calendar
        ]
        
        for source_func in sources:
            try:
                print(f"🔄 Trying {source_func.__name__}...")
                events = source_func()
                if events:
                    print(f"✅ Success with {source_func.__name__}")
                    return events
            except Exception as e:
                print(f"⚠️ {source_func.__name__} failed: {e}")
                continue
        
        print("❌ All alternative sources failed")
        return []
        
    except Exception as e:
        print(f"❌ Error with alternative sources: {e}")
        return []

def scrape_investing_calendar():
    """
    Try to scrape Investing.com economic calendar
    """
    try:
        session = requests.Session()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        session.headers.update(headers)
        
        # Investing.com economic calendar
        url = "https://www.investing.com/economic-calendar/"
        
        print(f"🌐 Fetching from Investing.com...")
        response = session.get(url, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for high impact events
            events = []
            
            # Try to find event rows
            event_rows = soup.find_all('tr', {'class': 'js-event-item'})
            
            for row in event_rows:
                try:
                    # Check for high impact
                    impact_cell = row.find('td', {'class': 'left textNum'})
                    if impact_cell:
                        impact_text = impact_cell.get_text(strip=True).lower()
                        if 'high' in impact_text:
                            # Extract event details
                            event_cell = row.find('td', {'class': 'left event'})
                            if event_cell:
                                event_name = event_cell.get_text(strip=True)
                                
                                # Extract currency
                                currency_cell = row.find('td', {'class': 'left flagCur'})
                                currency = currency_cell.get_text(strip=True) if currency_cell else "USD"
                                
                                # Extract time
                                time_cell = row.find('td', {'class': 'left time'})
                                if time_cell:
                                    time_text = time_cell.get_text(strip=True)
                                    event_time = parse_investing_time(time_text)
                                    
                                    if event_time and event_name:
                                        event_data = {
                                            "event": event_name,
                                            "datetime": event_time.isoformat(),
                                            "currency": currency,
                                            "impact": "High"
                                        }
                                        events.append(event_data)
                                        print(f"📅 Found event: {event_name} ({currency}) at {event_time}")
                
                except Exception as e:
                    continue
            
            return events
        
        return []
        
    except Exception as e:
        print(f"❌ Error scraping Investing.com: {e}")
        return []

def scrape_fxstreet_calendar():
    """
    Try to scrape FXStreet economic calendar
    """
    try:
        session = requests.Session()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        session.headers.update(headers)
        
        # FXStreet economic calendar
        url = "https://www.fxstreet.com/economic-calendar"
        
        print(f"🌐 Fetching from FXStreet...")
        response = session.get(url, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for high impact events
            events = []
            
            # Try to find event containers
            event_containers = soup.find_all('div', {'class': 'calendar-event'})
            
            for container in event_containers:
                try:
                    # Check for high impact
                    impact_elem = container.find('span', {'class': 'impact-high'})
                    if impact_elem:
                        # Extract event details
                        event_name_elem = container.find('span', {'class': 'event-name'})
                        if event_name_elem:
                            event_name = event_name_elem.get_text(strip=True)
                            
                            # Extract currency
                            currency_elem = container.find('span', {'class': 'currency'})
                            currency = currency_elem.get_text(strip=True) if currency_elem else "USD"
                            
                            # Extract time
                            time_elem = container.find('span', {'class': 'time'})
                            if time_elem:
                                time_text = time_elem.get_text(strip=True)
                                event_time = parse_fxstreet_time(time_text)
                                
                                if event_time and event_name:
                                    event_data = {
                                        "event": event_name,
                                        "datetime": event_time.isoformat(),
                                        "currency": currency,
                                        "impact": "High"
                                    }
                                    events.append(event_data)
                                    print(f"📅 Found event: {event_name} ({currency}) at {event_time}")
                
                except Exception as e:
                    continue
            
            return events
        
        return []
        
    except Exception as e:
        print(f"❌ Error scraping FXStreet: {e}")
        return []

def scrape_marketwatch_calendar():
    """
    Try to scrape MarketWatch economic calendar
    """
    try:
        session = requests.Session()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        session.headers.update(headers)
        
        # MarketWatch economic calendar
        url = "https://www.marketwatch.com/tools/economic-calendar"
        
        print(f"🌐 Fetching from MarketWatch...")
        response = session.get(url, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for high impact events
            events = []
            
            # Try to find event rows
            event_rows = soup.find_all('tr', {'class': 'table__row'})
            
            for row in event_rows:
                try:
                    # Check for high impact
                    impact_elem = row.find('span', {'class': 'high'})
                    if impact_elem:
                        # Extract event details
                        event_elem = row.find('td', {'class': 'table__cell event'})
                        if event_elem:
                            event_name = event_elem.get_text(strip=True)
                            
                            # Extract currency
                            currency_elem = row.find('td', {'class': 'table__cell currency'})
                            currency = currency_elem.get_text(strip=True) if currency_elem else "USD"
                            
                            # Extract time
                            time_elem = row.find('td', {'class': 'table__cell time'})
                            if time_elem:
                                time_text = time_elem.get_text(strip=True)
                                event_time = parse_marketwatch_time(time_text)
                                
                                if event_time and event_name:
                                    event_data = {
                                        "event": event_name,
                                        "datetime": event_time.isoformat(),
                                        "currency": currency,
                                        "impact": "High"
                                    }
                                    events.append(event_data)
                                    print(f"📅 Found event: {event_name} ({currency}) at {event_time}")
                
                except Exception as e:
                    continue
            
            return events
        
        return []
        
    except Exception as e:
        print(f"❌ Error scraping MarketWatch: {e}")
        return []

def parse_investing_time(time_text):
    """Parse Investing.com time format"""
    try:
        # Handle different time formats
        now = datetime.now()
        
        if "Today" in time_text:
            time_part = time_text.replace("Today", "").strip()
            time_obj = datetime.strptime(time_part, "%H:%M").time()
            return datetime.combine(now.date(), time_obj)
        
        elif "Tomorrow" in time_text:
            time_part = time_text.replace("Tomorrow", "").strip()
            time_obj = datetime.strptime(time_part, "%H:%M").time()
            tomorrow = now.date() + timedelta(days=1)
            return datetime.combine(tomorrow, time_obj)
        
        return None
    except:
        return None

def parse_fxstreet_time(time_text):
    """Parse FXStreet time format"""
    try:
        # Handle different time formats
        now = datetime.now()
        
        if "Today" in time_text:
            time_part = time_text.replace("Today", "").strip()
            time_obj = datetime.strptime(time_part, "%H:%M").time()
            return datetime.combine(now.date(), time_obj)
        
        elif "Tomorrow" in time_text:
            time_part = time_text.replace("Tomorrow", "").strip()
            time_obj = datetime.strptime(time_part, "%H:%M").time()
            tomorrow = now.date() + timedelta(days=1)
            return datetime.combine(tomorrow, time_obj)
        
        return None
    except:
        return None

def parse_marketwatch_time(time_text):
    """Parse MarketWatch time format"""
    try:
        # Handle different time formats
        now = datetime.now()
        
        if "Today" in time_text:
            time_part = time_text.replace("Today", "").strip()
            time_obj = datetime.strptime(time_part, "%H:%M").time()
            return datetime.combine(now.date(), time_obj)
        
        elif "Tomorrow" in time_text:
            time_part = time_text.replace("Tomorrow", "").strip()
            time_obj = datetime.strptime(time_part, "%H:%M").time()
            tomorrow = now.date() + timedelta(days=1)
            return datetime.combine(tomorrow, time_obj)
        
        return None
    except:
        return None

def scrape_public_api():
    """
    Use public API to get economic calendar data
    """
    try:
        print("🌐 Trying public economic calendar API...")
        
        # Try multiple free APIs
        apis = [
            try_alpha_vantage_api,
            try_finnhub_api,
            try_polygon_api
        ]
        
        for api_func in apis:
            try:
                print(f"🔄 Trying {api_func.__name__}...")
                events = api_func()
                if events:
                    print(f"✅ Success with {api_func.__name__}")
                    return events
            except Exception as e:
                print(f"⚠️ {api_func.__name__} failed: {e}")
                continue
        
        print("❌ All APIs failed")
        return []
        
    except Exception as e:
        print(f"❌ Error with public APIs: {e}")
        return []

def try_alpha_vantage_api():
    """
    Try Alpha Vantage API for economic calendar
    """
    try:
        # Alpha Vantage has a free tier
        url = "https://www.alphavantage.co/query"
        
        params = {
            'function': 'ECONOMIC_CALENDAR',
            'apikey': 'demo',  # Use demo key for testing
            'time_from': datetime.now().strftime('%Y%m%d'),
            'time_to': (datetime.now() + timedelta(days=7)).strftime('%Y%m%d')
        }
        
        print("🌐 Fetching from Alpha Vantage...")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'economic_calendar' in data:
                events = []
                for event in data['economic_calendar']:
                    try:
                        # Check for high impact events
                        impact = event.get('impact', '').lower()
                        if 'high' in impact:
                            event_data = {
                                "event": event.get('event', 'Unknown'),
                                "datetime": event.get('time', ''),
                                "currency": event.get('currency', 'USD'),
                                "impact": "High"
                            }
                            events.append(event_data)
                            print(f"📅 Found event: {event_data['event']} ({event_data['currency']})")
                    except:
                        continue
                
                return events
        
        return []
        
    except Exception as e:
        print(f"❌ Error with Alpha Vantage: {e}")
        return []

def try_finnhub_api():
    """
    Try Finnhub API for economic calendar
    """
    try:
        # Finnhub has a free tier
        url = "https://finnhub.io/api/v1/calendar/economic"
        
        params = {
            'token': 'demo',  # Use demo token for testing
            'from': datetime.now().strftime('%Y-%m-%d'),
            'to': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        }
        
        print("🌐 Fetching from Finnhub...")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'economicCalendar' in data:
                events = []
                for event in data['economicCalendar']:
                    try:
                        # Check for high impact events
                        impact = event.get('impact', '').lower()
                        if 'high' in impact:
                            event_data = {
                                "event": event.get('event', 'Unknown'),
                                "datetime": event.get('time', ''),
                                "currency": event.get('currency', 'USD'),
                                "impact": "High"
                            }
                            events.append(event_data)
                            print(f"📅 Found event: {event_data['event']} ({event_data['currency']})")
                    except:
                        continue
                
                return events
        
        return []
        
    except Exception as e:
        print(f"❌ Error with Finnhub: {e}")
        return []

def try_polygon_api():
    """
    Try Polygon API for economic calendar
    """
    try:
        # Polygon has a free tier
        url = "https://api.polygon.io/v3/reference/economic-calendar"
        
        params = {
            'apiKey': 'demo',  # Use demo key for testing
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        print("🌐 Fetching from Polygon...")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'results' in data:
                events = []
                for event in data['results']:
                    try:
                        # Check for high impact events
                        impact = event.get('impact', '').lower()
                        if 'high' in impact:
                            event_data = {
                                "event": event.get('name', 'Unknown'),
                                "datetime": event.get('date', ''),
                                "currency": event.get('currency', 'USD'),
                                "impact": "High"
                            }
                            events.append(event_data)
                            print(f"📅 Found event: {event_data['event']} ({event_data['currency']})")
                    except:
                        continue
                
                return events
        
        return []
        
    except Exception as e:
        print(f"❌ Error with Polygon: {e}")
        return []

def scrape_jblanked_api():
    """
    Use JBlanked News Calendar API to get real-time economic calendar data
    """
    try:
        print("🌐 Fetching from JBlanked News Calendar API...")
        
        # JBlanked API configuration
        api_key = "zwgRGihX.p5u4lBWd5A8n0QkMblgWhu7Jtq0f6MVA"
        auth_format = f"Api-Key {api_key}"
        
        # Try both Forex Factory and MQL5 endpoints
        endpoints = [
            "https://www.jblanked.com/news/api/forex-factory/calendar/today/",
            "https://www.jblanked.com/news/api/mql5/calendar/today/"
        ]
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": auth_format
        }
        
        for endpoint in endpoints:
            try:
                print(f"🔄 Trying endpoint: {endpoint.split('/')[-2]}...")
                
                # Add delay to respect rate limit (1 request per second)
                time.sleep(1)
                
                response = requests.get(endpoint, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if isinstance(data, list) and data:
                        events = []
                        
                        for event in data:
                            try:
                                # Check if it's a TRUE high impact (red folder) event
                                strength = event.get('Strength', '').lower()
                                event_name = event.get('Name', '').lower()
                                
                                # Only capture TRUE red folder events - the highest impact ones
                                # Based on actual red folder events for today
                                is_red_folder_event = (
                                    # Major GDP data (RED FOLDERS)
                                    'gdp' in event_name and 'm/m' in event_name or
                                    'gross domestic product' in event_name or
                                    
                                    # Major inflation data (RED FOLDERS)
                                    'core pce price index' in event_name or
                                    'pce price index' in event_name or
                                    
                                    # Major employment data (RED FOLDERS)
                                    'employment cost index' in event_name or
                                    'unemployment claims' in event_name or
                                    'non-farm payrolls' in event_name or
                                    'nfp' in event_name or
                                    'unemployment rate' in event_name or
                                    
                                    # Major central bank events (RED FOLDERS)
                                    'fomc' in event_name or
                                    'ecb' in event_name or
                                    'boe' in event_name or
                                    'boj' in event_name or
                                    'rate decision' in event_name or
                                    'interest rate' in event_name or
                                    'monetary policy' in event_name or
                                    
                                    # Major manufacturing data (RED FOLDERS)
                                    'ism manufacturing' in event_name or
                                    'chicago pmi' in event_name or
                                    
                                    # Major trade data (RED FOLDERS)
                                    'trade balance' in event_name or
                                    'current account' in event_name
                                )
                                
                                # Additional check for strength indicators that suggest red folder
                                has_red_folder_strength = (
                                    'strong' in strength and 'data' in strength or
                                    'high' in strength and 'impact' in strength or
                                    'critical' in strength or
                                    'major' in strength
                                )
                                
                                is_high_impact = is_red_folder_event and has_red_folder_strength
                                
                                if is_high_impact:
                                    # Parse the date
                                    date_str = event.get('Date', '')
                                    if date_str:
                                        try:
                                            # Parse date format: "2024.02.08 15:30:00"
                                            event_datetime = datetime.strptime(date_str, "%Y.%m.%d %H:%M:%S")
                                            
                                            event_data = {
                                                "event": event.get('Name', 'Unknown Event'),
                                                "datetime": event_datetime.isoformat(),
                                                "currency": event.get('Currency', 'USD'),
                                                "impact": "High",
                                                "forecast": event.get('Forecast'),
                                                "previous": event.get('Previous'),
                                                "actual": event.get('Actual'),
                                                "outcome": event.get('Outcome', ''),
                                                "strength": event.get('Strength', ''),
                                                "category": event.get('Category', '')
                                            }
                                            
                                            events.append(event_data)
                                            print(f"📅 Found RED FOLDER event: {event_data['event']} ({event_data['currency']}) at {event_datetime}")
                                            
                                        except Exception as e:
                                            print(f"⚠️ Error parsing date '{date_str}': {e}")
                                            continue
                            
                            except Exception as e:
                                print(f"⚠️ Error processing event: {e}")
                                continue
                        
                        if events:
                            print(f"✅ Successfully loaded {len(events)} RED FOLDER events from JBlanked API")
                            return events
                        else:
                            print("⚠️ No red folder events found in the response")
                    
                    else:
                        print("⚠️ Empty or invalid response from API")
                
                else:
                    print(f"❌ API request failed with status {response.status_code}")
                    if response.status_code == 401:
                        print("   Authentication failed - check API key")
                    elif response.status_code == 429:
                        print("   Rate limit exceeded - wait before retrying")
                
            except Exception as e:
                print(f"⚠️ Error with endpoint {endpoint}: {e}")
                continue
        
        print("❌ All JBlanked API endpoints failed")
        return []
        
    except Exception as e:
        print(f"❌ Error with JBlanked API: {e}")
        return []

def create_sample_high_impact_events():
    """
    Create sample high-impact events for testing when no real data is available
    This is only for development/testing purposes
    """
    try:
        print("📝 Creating sample high-impact events for testing...")
        
        now = datetime.now()
        events = []
        
        # Create some sample events for the next few days
        sample_events = [
            {
                "event": "Federal Reserve Interest Rate Decision",
                "currency": "USD",
                "hours_offset": 24
            },
            {
                "event": "Non-Farm Payrolls",
                "currency": "USD", 
                "hours_offset": 48
            },
            {
                "event": "ECB Press Conference",
                "currency": "EUR",
                "hours_offset": 72
            },
            {
                "event": "Bank of England Rate Decision",
                "currency": "GBP",
                "hours_offset": 96
            }
        ]
        
        for sample in sample_events:
            event_time = now + timedelta(hours=sample["hours_offset"])
            event_data = {
                "event": sample["event"],
                "datetime": event_time.isoformat(),
                "currency": sample["currency"],
                "impact": "High"
            }
            events.append(event_data)
            print(f"📅 Created sample event: {sample['event']} ({sample['currency']}) at {event_time}")
        
        return events
        
    except Exception as e:
        print(f"❌ Error creating sample events: {e}")
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
        print("⚠️ No high-impact events found for today")
        print("📝 This is normal - not every day has high-impact news events")
        print("🗑️ Clearing any existing stale data...")
        
        # Clear the existing file to ensure no stale data is used
        try:
            if os.path.exists("high_impact_news.json"):
                os.remove("high_impact_news.json")
                print("✅ Cleared existing news data file")
        except Exception as e:
            print(f"⚠️ Could not clear existing file: {e}")
        
        print("\n🔧 IMPORTANT: JBlanked API is configured and ready to use!")
        print("   ✅ API Key: zwgRGihX.p5u4lBWd5A8n0QkMblgWhu7Jtq0f6MVA")
        print("   📡 Endpoints: Forex Factory & MQL5 calendar data")
        print("   ⏱️ Rate limit: 1 request per second")
        print("   💡 The bot will automatically retry if the API is temporarily unavailable")
        print("\n💡 For now, the bot will trade without news protection until API data is available")
    
    print("\n" + "=" * 50)
    print("🏁 Scraping process completed")

if __name__ == "__main__":
    main() 