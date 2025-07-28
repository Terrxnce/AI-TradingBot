#!/usr/bin/env python3
"""
Test heartbeat system
"""

import json
import os
from datetime import datetime

def test_heartbeat():
    """Test heartbeat creation and reading"""
    print("🧪 Testing Heartbeat System...")
    
    # Create test heartbeat
    test_heartbeat = {
        "last_heartbeat": datetime.now().isoformat(),
        "bot_status": "running",
        "current_symbols": ["USDJPY", "EURUSD"],
        "loop_count": 42,
        "last_analysis": datetime.now().isoformat(),
        "mt5_connected": True,
        "news_protection_active": False
    }
    
    # Write heartbeat
    try:
        with open("bot_heartbeat.json", "w") as f:
            json.dump(test_heartbeat, f)
        print("✅ Heartbeat file created successfully")
    except Exception as e:
        print(f"❌ Failed to create heartbeat: {e}")
        return False
    
    # Read heartbeat
    try:
        with open("bot_heartbeat.json", "r") as f:
            loaded_heartbeat = json.load(f)
        print("✅ Heartbeat file read successfully")
        print(f"   Status: {loaded_heartbeat.get('bot_status')}")
        print(f"   Symbols: {loaded_heartbeat.get('current_symbols')}")
        print(f"   Loops: {loaded_heartbeat.get('loop_count')}")
        print(f"   MT5 Connected: {loaded_heartbeat.get('mt5_connected')}")
        print(f"   News Protection: {loaded_heartbeat.get('news_protection_active')}")
    except Exception as e:
        print(f"❌ Failed to read heartbeat: {e}")
        return False
    
    # Clean up
    try:
        os.remove("bot_heartbeat.json")
        print("✅ Test heartbeat file cleaned up")
    except:
        pass
    
    print("🎉 Heartbeat system test passed!")
    return True

if __name__ == "__main__":
    test_heartbeat() 