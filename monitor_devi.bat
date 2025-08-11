@echo off
echo ========================================
echo    D.E.V.I Monitoring Dashboard
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

REM Start Streamlit dashboard
echo Starting D.E.V.I monitoring dashboard...
echo Dashboard will be available at: http://localhost:8501
echo Press Ctrl+C to stop the dashboard
echo.

python "GUI Components\streamlit_app.py"

echo.
echo Dashboard stopped. Press any key to exit...
pause
