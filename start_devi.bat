@echo off
echo ========================================
echo    D.E.V.I Trading Bot Startup
echo ========================================
echo.

REM Navigate to project directory
cd /d "%~dp0"

REM Activate virtual environment
echo Activating virtual environment...
call tradingbot_env\Scripts\activate.bat

REM Check if activation was successful
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo Please ensure tradingbot_env exists and is properly configured
    pause
    exit /b 1
)

echo Virtual environment activated successfully
echo.

REM Quick validation
echo Running quick validation...
python quick_validation.py

if errorlevel 1 (
    echo ERROR: Quick validation failed
    echo Please check the errors above and fix them before starting the bot
    pause
    exit /b 1
)

echo.
echo Validation successful! Starting D.E.V.I trading bot...
echo.

REM Start the bot with quarter-hour alignment
python "Bot Core\bot_runner.py" --user-id internal --align quarter

echo.
echo Bot has stopped. Press any key to exit...
pause
