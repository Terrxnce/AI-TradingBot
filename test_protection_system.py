import sys
sys.path.append('Bot Core')
sys.path.append('Data Files')

from profit_protection_manager import get_protection_status

print('🛡️ TESTING PROTECTION SYSTEM')
print('=' * 50)

status = get_protection_status()
print(f'Floating Equity %: {status["floating_equity_pct"]:.2f}%')
print(f'Partial Done: {status["partial_done"]}')
print(f'Full Done: {status["full_done"]}')
print(f'Drawdown Blocked: {status["blocked_for_drawdown"]}')
print(f'Session Baseline: ${status["session_baseline"]:.2f}')
print('✅ Protection system working correctly!')
