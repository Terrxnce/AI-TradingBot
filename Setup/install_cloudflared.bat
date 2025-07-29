@echo off
echo ========================================
echo 🔧 Cloudflare Tunnel Installer
echo ========================================
echo.
echo Installing cloudflared for secure dashboard access...
echo.

REM Check if winget is available
where winget >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ ERROR: winget not found!
    echo.
    echo Please install Windows Package Manager (winget) first:
    echo https://docs.microsoft.com/en-us/windows/package-manager/winget/
    echo.
    pause
    exit /b 1
)

echo 📦 Installing cloudflared via winget...
winget install Cloudflare.cloudflared

if %errorlevel% equ 0 (
    echo.
    echo ✅ cloudflared installed successfully!
    echo.
    echo 🚀 You can now run: Setup\start_dashboard.bat
    echo.
    echo 📋 Next steps:
    echo 1. Run start_dashboard.bat
    echo 2. Copy the tunnel URL
    echo 3. Share URL + password with your team
    echo.
) else (
    echo.
    echo ❌ Installation failed!
    echo.
    echo 🔧 Manual installation:
    echo 1. Download from: https://developers.cloudflare.com/cloudflared/install/
    echo 2. Extract cloudflared.exe to project root
    echo.
)

pause 