import sys
sys.path.append('Bot Core')
sys.path.append('Data Files')

print('🧪 FINAL INTEGRATION TEST')
print('=' * 50)

# Test all systems
from session_manager import get_current_session_info
from profit_protection_manager import get_protection_status
from news_guard import get_high_impact_news
from decision_engine import evaluate_trade_decision_legacy

# Session test
session = get_current_session_info()
print(f'✅ Session: {session["session_type"]}')

# Protection test
protection = get_protection_status()
print(f'✅ Protection: {protection["floating_equity_pct"]:.2f}%')

# News test
news_events = get_high_impact_news()
print(f'✅ News Events: {len(news_events)} loaded')

# Decision engine test
test_signals = {
    'bos': 'bearish', 
    'fvg_valid': True, 
    'ob_tap': True, 
    'rejection': True, 
    'liquidity_sweep': True, 
    'engulfing': True, 
    'ema_trend': 'bearish', 
    'session': 'PM'
}
decision = evaluate_trade_decision_legacy(test_signals, '')
print(f'✅ Decision Engine: {decision}')

print('🎯 ALL SYSTEMS OPERATIONAL - D.E.V.I READY FOR ASIAN SESSION!')
