import json
import os
from datetime import datetime

STATE_FILE = "trade_state.json"

def load_trade_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_trade_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def mark_partial_closed(ticket):
    state = load_trade_state()
    state[str(ticket)] = {
        "partial_closed": True,
        "trailing_sl_applied": False,
        "reason": "partial",
        "last_updated": datetime.now().isoformat()
    }
    save_trade_state(state)

def should_apply_trailing_sl(ticket, open_time):
    state = load_trade_state()
    entry = state.get(str(ticket), {})
    if entry.get("trailing_sl_applied"):
        return False
    thirty_min_passed = (datetime.now() - open_time).total_seconds() >= 30 * 60
    return thirty_min_passed or entry.get("partial_closed", False)

def mark_trailing_applied(ticket, reason="30min"):
    state = load_trade_state()
    entry = state.get(str(ticket), {})
    entry.update({
        "trailing_sl_applied": True,
        "reason": reason,
        "last_updated": datetime.now().isoformat()
    })
    state[str(ticket)] = entry
    save_trade_state(state)
