@echo off
echo Starting D.E.V.I Trading Bot GUI...
echo.
echo Access the dashboard at: http://localhost:8501
echo.
echo Press Ctrl+C to stop the GUI
echo.

cd /d "%~dp0.."
tradingbot_env\Scripts\python.exe -m streamlit run "GUI Components\streamlit_app.py" --server.port 8501

pause