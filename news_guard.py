import feedparser
from datetime import datetime
import re

FEED_URL = "https://www.forexfactory.com/calendar.php?week=thisweek&rss=1"

def get_macro_sentiment(symbol):
    currency = extract_currency(symbol)
    if not currency:
        return "No macro context for this symbol."

    feed = feedparser.parse(FEED_URL)
    today = datetime.utcnow().strftime("%b %d")  # e.g., 'Jul 16'
    relevant = []

    for entry in feed.entries:
        title = entry.title
        summary = entry.summary

        # Match currency + high impact
        if currency not in title:
            continue
        if "High" not in summary:
            continue
        if today not in summary:
            continue

        # Try to extract forecast vs actual
        actual = extract_metric(summary, "Actual")
        forecast = extract_metric(summary, "Forecast")
        bias = "neutral"
        if actual is not None and forecast is not None:
            try:
                actual_val = float(actual)
                forecast_val = float(forecast)
                if actual_val > forecast_val:
                    bias = "hawkish"
                elif actual_val < forecast_val:
                    bias = "dovish"
            except:
                pass

        time = extract_time(summary)
        relevant.append(f"{title} at {time} → {bias} ({actual} vs {forecast})")

    return " | ".join(relevant) if relevant else "No high-impact news for today."

def extract_currency(symbol):
    for code in ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]:
        if code in symbol.upper():
            return code
    return None

def extract_metric(text, label):
    match = re.search(rf"{label}:\s*([-+]?[0-9]*\.?[0-9]+)", text)
    return match.group(1) if match else None

def extract_time(text):
    match = re.search(r"(\d{1,2}:\d{2}[ap]m)", text)
    return match.group(1) if match else "unknown"
