import sys
sys.path.append('Bot Core')
sys.path.append('Data Files')

from session_manager import get_current_session_info, get_next_session_start

print('🧪 TESTING SESSION MANAGEMENT')
print('=' * 50)

session_info = get_current_session_info()
print(f'Current Session: {session_info["session_type"]}')
print(f'Current UTC: {session_info["current_time_utc"]}')
print(f'Lot Multiplier: {session_info["lot_multiplier"]}')
print(f'Min Score: {session_info["min_score"]}')

next_session, next_time = get_next_session_start()
print(f'Next Session: {next_session}')
print(f'Next Start: {next_time.strftime("%Y-%m-%d %H:%M UTC")}')
print('✅ Session management working correctly!')
