@echo off
echo ========================================
echo D.E.V.I Dashboard Status Check
echo ========================================
echo.

REM Check if dashboard is running
netstat -ano | findstr :8501 >nul
if %errorlevel% equ 0 (
    echo [OK] Dashboard running on port 8501
) else (
    echo [ERROR] Dashboard not running on port 8501
)

REM Check if cloudflared is running
tasklist | findstr cloudflared.exe >nul
if %errorlevel% equ 0 (
    echo [OK] Cloudflare tunnel is running
) else (
    echo [ERROR] Cloudflare tunnel not running
)

echo.
echo ========================================
echo Access Information:
echo ========================================
echo.
echo 1. Look for the Cloudflare tunnel window
echo 2. Copy the tunnel URL (https://*.trycloudflare.com)
echo 3. Share URL + password with team
echo.
echo Password: devipass2025
echo.
echo ========================================
pause 