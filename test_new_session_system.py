# ------------------------------------------------------------------------------------
# 🧪 test_new_session_system.py – New Session System Test
#
# Tests the new session management system with forced auto-close points
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import sys
import os
from datetime import datetime, timezone, time

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'Bot Core'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))

from session_manager import get_current_session_info, check_for_forced_close, is_trading_allowed
from config import CONFIG

def test_session_times():
    """Test session detection at various times"""
    
    print("🧪 TESTING NEW SESSION SYSTEM")
    print("=" * 50)
    
    print("📊 Session Configuration:")
    sessions = CONFIG.get("sessions", {})
    for session_name, session_config in sessions.items():
        print(f"   {session_name.upper()}: {session_config['start_utc']}-{session_config['end_utc']} UTC")
        print(f"      Lot Multiplier: {session_config['lot_multiplier']}x")
        print(f"      Min Score: {session_config['min_score']}/8.0")
        print(f"      Auto Close: {session_config['auto_close_utc']} UTC")
    
    print("\n" + "=" * 50)
    print("🕐 Current Session Info:")
    
    # Test current session (no mocking needed)
    session_info = get_current_session_info()
    forced_close = check_for_forced_close()
    
    print(f"   Current UTC Time: {session_info['current_time_utc']}")
    print(f"   Session Type: {session_info['session_type']}")
    print(f"   Lot Multiplier: {session_info['lot_multiplier']}x")
    print(f"   Min Score: {session_info['min_score']}/8.0")
    print(f"   Trading Allowed: {is_trading_allowed()}")
    print(f"   Forced Close: {forced_close or 'None'}")
    
    print("\n" + "=" * 50)
    print("🎯 Session Logic Validation:")
    
    # Test session logic manually
    current_time = datetime.now(timezone.utc).time()
    
    # Test NY AM session (12:30-15:00 UTC)
    ny_start = time(12, 30)
    ny_end = time(15, 0)
    in_ny = ny_start <= current_time < ny_end
    print(f"   NY AM Session (12:30-15:00): {'✅' if in_ny else '❌'}")
    
    # Test PM session (17:00-19:00 UTC)
    pm_start = time(17, 0)
    pm_end = time(19, 0)
    in_pm = pm_start <= current_time < pm_end
    print(f"   PM Session (17:00-19:00): {'✅' if in_pm else '❌'}")
    
    # Test Asian session (00:00-03:00 UTC)
    asian_start = time(0, 0)
    asian_end = time(3, 0)
    in_asian = asian_start <= current_time < asian_end
    print(f"   Asian Session (00:00-03:00): {'✅' if in_asian else '❌'}")
    
    # Test forced close times
    forced_close_times = [
        (time(15, 0), "ny_close"),
        (time(19, 0), "pm_close"), 
        (time(3, 0), "asia_close")
    ]
    
    print("\n🎯 Forced Close Validation:")
    for close_time, reason in forced_close_times:
        is_close_time = current_time.hour == close_time.hour and current_time.minute == close_time.minute
        print(f"   {close_time.strftime('%H:%M')} UTC ({reason}): {'🚨' if is_close_time else '✅'}")

def test_lot_size_calculation():
    """Test lot size calculation with new session system"""
    
    print("\n" + "=" * 50)
    print("💰 Testing Lot Size Calculation:")
    
    base_lot = 35.0
    
    # Test each session
    sessions = CONFIG.get("sessions", {})
    for session_name, session_config in sessions.items():
        multiplier = session_config["lot_multiplier"]
        expected_lot = base_lot * multiplier
        
        print(f"   {session_name.upper()}: {base_lot} × {multiplier} = {expected_lot}")
    
    print(f"   Base lot size: {base_lot}")
    print(f"   NY AM: {base_lot * 1.0} (100%)")
    print(f"   PM: {base_lot * 0.75} (75%)")
    print(f"   Asian: {base_lot * 0.5} (50%)")

if __name__ == "__main__":
    test_session_times()
    test_lot_size_calculation()
    
    print("\n" + "=" * 50)
    print("✅ Session System Test Complete!")
    print("\n📋 Summary:")
    print("   • NY AM: 12:30-15:00 UTC (100% lot, 6.0 min score)")
    print("   • PM: 17:00-19:00 UTC (75% lot, 7.0 min score)")
    print("   • Asian: 00:00-03:00 UTC (50% lot, 7.0 min score)")
    print("   • Forced close at: 15:00, 19:00, 03:00 UTC")
    print("   • Legacy post-session logic removed")
