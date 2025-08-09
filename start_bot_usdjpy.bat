@echo off
cd /d "%~dp0"
echo Starting USDJPY Trading Bot...
echo.
call tradingbot_env\Scripts\activate.bat
cd "Bot Core"
python bot_runner.py USDJPY
pause
