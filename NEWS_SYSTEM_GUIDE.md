# 📰 D.E.V.I News Protection System Guide (Improved)

## 🎯 **Simple & Clean News Protection**

The news protection system is designed to be **user-friendly** and **broker-safe**. Users simply add news events, and D.E.V.I automatically pauses trading during the protection window.

## 📋 **How to Add News Events**

### **Step 1: Edit the News File**

Open `high_impact_news.json` and add events in this format:

```json
[
  {
    "event": "Flash Manufacturing PMI",
    "datetime": "2025-08-21T13:45:00", 
    "currency": "USD",
    "impact": "High",
    "category": "Economic Data"
  }
]
```

⚠️ **Important: All times must be in UTC, not local time.**

For example:
- **Irish time 14:45 (2:45 pm)** = **13:45 UTC** in JSON

### **Step 2: Bot Automatically Handles Protection**

- **Before Event**: Stops trading 30 minutes before (13:15 UTC / 14:15 Irish)
- **During Event**: Trading stays blocked
- **After Event**: Resumes 30 minutes after (14:15 UTC / 15:15 Irish)
- **Currency Matching**: Only affects pairs and instruments linked to that currency (e.g. USDJPY, EURUSD, XAUUSD, US500)

## ⚙️ **Configuration Options**

In `config.py`:

```python
CONFIG = {
    "enable_news_protection": True,          # Turn system on/off
    "news_protection_minutes": 30,           # Minutes before/after
    "news_impact_filter": ["High"],          # Which impacts to block
    "auto_disable_on_no_news": True          # Auto-disable if no events in file
}
```

✨ **Tip**: You can add "Medium" or "Low" to the impact filter if you want more cautious blocking.

## 🔧 **How It Works**

### **Check News Protection Status**
```python
from news_guard import is_trading_blocked_by_news

# Check global status
blocked, reason = is_trading_blocked_by_news()

# Check symbol-specific
blocked, reason = is_trading_blocked_by_news("USDJPY")
```

### **Example Output**
```
📰 Loaded 1 high-impact event from high_impact_news.json
🚫 Trading blocked for USDJPY
   Event: Flash Manufacturing PMI
   Currency: USD
   Event time: 2025-08-21 13:45 UTC
   Protection window: 13:15 – 14:15 UTC (14:15 – 15:15 Irish time)
   Current time: 13:30 UTC
```

## 🚀 **Benefits of New System**

- **Timezone-Safe**: Always UTC in JSON
- **Flexible**: Impact filter lets you choose caution level
- **Overlap Handling**: If events overlap, protection window extends automatically
- **Error Handling**: If file is empty/malformed, bot continues trading (unless disabled in config)
- **Transparent**: Logs exactly which event is blocking trading

## 📝 **News Event Format (Quick Reference)**

```json
{
  "event": "Event Name",
  "datetime": "YYYY-MM-DDTHH:MM:SS",  # Must be in UTC
  "currency": "USD/EUR/GBP/etc",
  "impact": "High/Medium/Low",
  "category": "Economic Data/News/etc"
}
```

## ✅ **Example for Today**

**Irish Time**: 14:45 (2:45 pm)  
**UTC Time**: 13:45

```json
[
  {
    "event": "Flash Manufacturing PMI",
    "datetime": "2025-08-21T13:45:00",
    "currency": "USD",
    "impact": "High",
    "category": "Economic Data"
  }
]
```

**Trading will be blocked from 13:15 – 14:15 UTC (14:15 – 15:15 Irish time).**
