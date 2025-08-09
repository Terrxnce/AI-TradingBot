@echo off
echo Restarting D.E.V.I Trading Bot GUI...
echo.

:: Kill any existing Streamlit processes
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Streamlit*" 2>nul
timeout /t 2 /nobreak >nul

:: Start the GUI
cd /d "C:\Users\Index\AI_TradingBot\GUI Components"
echo Starting GUI on http://localhost:8501
echo Press Ctrl+C to stop the GUI
echo.
..\tradingbot_env\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8501

pause
