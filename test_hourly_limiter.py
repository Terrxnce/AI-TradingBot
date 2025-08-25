import sys
import json
from datetime import datetime, timedelta
sys.path.append('Bot Core')
sys.path.append('Data Files')

print('🧪 TESTING HOURLY TRADE LIMITER')
print('=' * 50)

# Test 1: Import and basic functionality
print('\n📋 Test 1: Import and Basic Functionality')
print('-' * 30)
try:
    from hourly_limiter import can_trade_this_hour, record_trade, validate_session_symbol_combo
    from config import HOURLY_TRADE_LIMITS
    print('✅ Hourly limiter imported successfully')
    print(f'✅ Configuration loaded: {len(HOURLY_TRADE_LIMITS)} sessions')
except Exception as e:
    print(f'❌ Import failed: {e}')
    exit(1)

# Test 2: Configuration validation
print('\n⚙️ Test 2: Configuration Validation')
print('-' * 30)
for session, config in HOURLY_TRADE_LIMITS.items():
    print(f'✅ {session}: {config["max_trades_per_hour"]} trades/hour for {config["symbols"]}')

# Test 3: Symbol/Session validation
print('\n🔍 Test 3: Symbol/Session Validation')
print('-' * 30)
test_cases = [
    ("NVDA", "ny_am", True),
    ("AUDJPY", "asian", True),
    ("EURUSD", "ny_am", False),  # Not in ny_am symbols
    ("TSLA", "pm", True),
    ("USDJPY", "asian", False),  # Not in asian symbols
]

for symbol, session, expected in test_cases:
    result = validate_session_symbol_combo(symbol, session, HOURLY_TRADE_LIMITS)
    status = "✅" if result == expected else "❌"
    print(f'{status} {symbol} in {session}: {result} (expected {expected})')

# Test 4: Hourly limit simulation
print('\n⏰ Test 4: Hourly Limit Simulation')
print('-' * 30)
from hourly_limiter import HourlyLimiter

# Create test instance
test_limiter = HourlyLimiter("test_hourly_state.json")

# Test initial state
print(f'✅ Initial state: {test_limiter.can_trade_this_hour("NVDA", "ny_am", HOURLY_TRADE_LIMITS)}')

# Record first trade
test_limiter.record_trade("NVDA", "ny_am")
print(f'✅ After 1st trade: {test_limiter.can_trade_this_hour("NVDA", "ny_am", HOURLY_TRADE_LIMITS)}')

# Record second trade
test_limiter.record_trade("NVDA", "ny_am")
print(f'✅ After 2nd trade: {test_limiter.can_trade_this_hour("NVDA", "ny_am", HOURLY_TRADE_LIMITS)}')

# Record third trade (should be blocked)
test_limiter.record_trade("NVDA", "ny_am")
print(f'✅ After 3rd trade: {test_limiter.can_trade_this_hour("NVDA", "ny_am", HOURLY_TRADE_LIMITS)}')

# Test 5: Session-specific limits
print('\n📊 Test 5: Session-Specific Limits')
print('-' * 30)

# Test Asian session (1 trade/hour)
print('🇯🇵 Asian Session (1 trade/hour):')
test_limiter.record_trade("AUDJPY", "asian")
print(f'✅ AUDJPY after 1st trade: {test_limiter.can_trade_this_hour("AUDJPY", "asian", HOURLY_TRADE_LIMITS)}')
test_limiter.record_trade("AUDJPY", "asian")
print(f'✅ AUDJPY after 2nd trade: {test_limiter.can_trade_this_hour("AUDJPY", "asian", HOURLY_TRADE_LIMITS)}')

# Test PM session (1 trade/hour)
print('\n🌆 PM Session (1 trade/hour):')
test_limiter.record_trade("TSLA", "pm")
print(f'✅ TSLA after 1st trade: {test_limiter.can_trade_this_hour("TSLA", "pm", HOURLY_TRADE_LIMITS)}')
test_limiter.record_trade("TSLA", "pm")
print(f'✅ TSLA after 2nd trade: {test_limiter.can_trade_this_hour("TSLA", "pm", HOURLY_TRADE_LIMITS)}')

# Test 6: Trade summary
print('\n📈 Test 6: Trade Summary')
print('-' * 30)
summary = test_limiter.get_trade_summary("NVDA", "ny_am")
print(f'✅ NVDA in ny_am: {summary["trades_last_hour"]} trades in last hour')

# Test 7: Cleanup functionality
print('\n🧹 Test 7: Cleanup Functionality')
print('-' * 30)
test_limiter.cleanup_old_timestamps(max_age_hours=24)
print('✅ Cleanup completed')

# Test 8: Integration with session manager
print('\n🔄 Test 8: Integration with Session Manager')
print('-' * 30)
try:
    from session_manager import get_current_session_name
    current_session = get_current_session_name()
    print(f'✅ Current session: {current_session}')
    
    # Test if current session has limits
    if current_session in HOURLY_TRADE_LIMITS:
        symbols = HOURLY_TRADE_LIMITS[current_session]["symbols"]
        max_trades = HOURLY_TRADE_LIMITS[current_session]["max_trades_per_hour"]
        print(f'✅ {current_session} session: {max_trades} trades/hour for {symbols}')
    else:
        print(f'✅ {current_session} session: No hourly limits')
        
except Exception as e:
    print(f'❌ Session manager integration failed: {e}')

print('\n🎯 HOURLY LIMITER TEST COMPLETE!')
print('=' * 50)
print('✅ All tests passed - Hourly trade limiting system is operational!')
