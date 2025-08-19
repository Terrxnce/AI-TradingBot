import json
import os
from datetime import datetime, timedelta

# State file for tracking trailing stop applications
TRAILING_STATE_FILE = "trailing_stop_state.json"

def load_trailing_state():
    """Load trailing stop state"""
    try:
        if os.path.exists(TRAILING_STATE_FILE):
            with open(TRAILING_STATE_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load trailing state: {e}")
    return {}

def save_trailing_state(state):
    """Save trailing stop state"""
    try:
        with open(TRAILING_STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"⚠️ Failed to save trailing state: {e}")

def should_apply_trailing_sl(ticket, open_time):
    """
    Check if trailing stop should be applied to a position
    
    Args:
        ticket: Position ticket
        open_time: Position open time
    
    Returns:
        bool: True if trailing stop should be applied
    """
    try:
        state = load_trailing_state()
        ticket_str = str(ticket)
        
        # If already applied, don't apply again
        if ticket_str in state:
            return False
        
        # Check if position is old enough (30 minutes)
        time_since_open = datetime.now() - open_time
        if time_since_open >= timedelta(minutes=30):
            return True
        
        # For newer positions, check if partial close logic applies
        # This would depend on your specific partial close strategy
        # For now, return True for positions older than 5 minutes
        return time_since_open >= timedelta(minutes=5)
        
    except Exception as e:
        print(f"⚠️ Error checking trailing SL eligibility: {e}")
        return False

def mark_trailing_applied(ticket, reason="30min"):
    """
    Mark that trailing stop has been applied to a position
    
    Args:
        ticket: Position ticket
        reason: Reason for applying trailing stop
    """
    try:
        state = load_trailing_state()
        ticket_str = str(ticket)
        
        state[ticket_str] = {
            "applied_at": datetime.now().isoformat(),
            "reason": reason
        }
        
        save_trailing_state(state)
        print(f"📝 Trailing stop marked as applied for ticket {ticket} ({reason})")
        
    except Exception as e:
        print(f"⚠️ Error marking trailing applied: {e}")

def mark_partial_closed(ticket):
    """
    Mark that a position has been partially closed
    
    Args:
        ticket: Position ticket
    """
    try:
        state = load_trailing_state()
        ticket_str = str(ticket)
        
        if ticket_str in state:
            state[ticket_str]["partial_closed"] = True
            state[ticket_str]["partial_closed_at"] = datetime.now().isoformat()
            save_trailing_state(state)
            print(f"📝 Partial close marked for ticket {ticket}")
        
    except Exception as e:
        print(f"⚠️ Error marking partial closed: {e}")

def clear_trailing_state(ticket=None):
    """
    Clear trailing state for a specific ticket or all tickets
    
    Args:
        ticket: Specific ticket to clear, or None to clear all
    """
    try:
        if ticket is None:
            # Clear all state
            save_trailing_state({})
            print("🗑️ All trailing state cleared")
        else:
            # Clear specific ticket
            state = load_trailing_state()
            ticket_str = str(ticket)
            if ticket_str in state:
                del state[ticket_str]
                save_trailing_state(state)
                print(f"🗑️ Trailing state cleared for ticket {ticket}")
                
    except Exception as e:
        print(f"⚠️ Error clearing trailing state: {e}")
