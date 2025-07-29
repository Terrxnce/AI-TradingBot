@echo off
echo Starting D.E.V.I Analytics Dashboard...
echo.
echo Access the dashboard at: http://localhost:8502
echo.
echo Press Ctrl+C to stop the dashboard
echo.

cd /d "%~dp0.."
tradingbot_env\Scripts\python.exe -m streamlit run "GUI Components\run_analytics.py" --server.port 8502

pause 