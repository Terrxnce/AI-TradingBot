@echo off
echo 🚀 Starting D.E.V.I Dashboard with Timeout Prevention...
echo.

cd /d "%~dp0"
cd ..

echo 📊 Starting Streamlit with timeout prevention settings...
echo ⏰ Auto-refresh enabled to prevent disconnections
echo 🔄 Dashboard will be available at: http://localhost:8501
echo.

tradingbot_env\Scripts\python.exe -m streamlit run "GUI Components\streamlit_app.py" ^
    --server.port 8501 ^
    --server.address localhost ^
    --server.headless true ^
    --server.enableCORS false ^
    --server.enableXsrfProtection false ^
    --server.runOnSave false ^
    --server.fileWatcherType none ^
    --browser.gatherUsageStats false

echo.
echo 🛑 Dashboard stopped.
pause 