from datetime import datetime
from config import CONFIG

def detect_session():
    now = datetime.now()
    hour = now.hour + now.minute / 60  # e.g. 13.5 at 13:30

    for session, (start, end) in CONFIG.get("session_hours", {}).items():
        if start <= hour < end:
            return session
    return "Unknown"
