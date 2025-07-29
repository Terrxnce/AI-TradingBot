@echo off
echo ========================================
echo D.E.V.I Trading Bot Dashboard Launcher
echo ========================================
echo.
echo Starting secure dashboard access...
echo.

REM Check if cloudflared is available (local or system)
if exist "cloudflared.exe" (
    set CLOUDFLARED=cloudflared.exe
) else (
    where cloudflared >nul 2>nul
    if %errorlevel% equ 0 (
        set CLOUDFLARED=cloudflared
    ) else (
        echo ❌ ERROR: cloudflared not found!
        echo.
        echo Please install cloudflared first:
        echo 1. Run: Setup\install_cloudflared.bat
        echo 2. Or download from: https://developers.cloudflare.com/cloudflared/install/
        echo.
        pause
        exit /b 1
    )
)

echo cloudflared found - proceeding with secure tunnel setup
echo.

REM Change to project directory
cd /d "%~dp0.."

echo Starting Streamlit Dashboard on port 8501...
start "D.E.V.I Dashboard" cmd /k "tradingbot_env\Scripts\python.exe -m streamlit run \"GUI Components\streamlit_app.py\" --server.port 8501"

echo Waiting for dashboard to initialize...
timeout /t 10 /nobreak >nul

echo Launching secure Cloudflare Tunnel...
echo.
echo IMPORTANT: Copy the tunnel URL below and share with your team
echo Password: devipass2025
echo.
echo ========================================
start "Cloudflare Tunnel" cmd /k "%CLOUDFLARED% tunnel --url http://localhost:8501"

echo.
echo Setup complete! 
echo.
echo Team Access Instructions:
echo 1. Copy the tunnel URL from the new window
echo 2. Share URL + password with Roni and Enoch
echo 3. They can access from any browser - no installation needed
echo.
echo Security: Dashboard is password protected
echo Access: Works from anywhere with internet
echo.
pause 