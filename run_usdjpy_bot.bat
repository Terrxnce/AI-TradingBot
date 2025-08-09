@echo off
echo Starting USDJPY Trading Bot...
echo.
cd /d "C:\Users\Index\AI_TradingBot\Bot Core"
..\tradingbot_env\Scripts\python.exe bot_runner.py USDJPY
echo.
echo Bot finished. Press any key to close...
pause
