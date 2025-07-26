#!/usr/bin/env python3
# ------------------------------------------------------------------------------------
# 🚀 D.E.V.I GUI Setup Script
#
# This script helps set up and deploy the D.E.V.I trading bot GUI:
#
# ✅ Install dependencies
# ✅ Check configuration files
# ✅ Set up hosting with ngrok/cloudflare
# ✅ Initialize environment
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot GUI Setup
# ------------------------------------------------------------------------------------

import os
import sys
import subprocess
import platform

def print_banner():
    """Print setup banner"""
    print("🤖" + "="*60)
    print("🚀 D.E.V.I Trading Bot GUI Setup")
    print("📋 Internal Shared Beta - Team Access Setup")
    print("="*62)
    print()

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required. Current version:", platform.python_version())
        return False
    print(f"✅ Python {platform.python_version()} - OK")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def check_files():
    """Check required files exist"""
    print("\n📁 Checking required files...")
    
    required_files = [
        "config.py",
        "bot_runner.py", 
        "streamlit_app.py",
        "utils/config_manager.py",
        "utils/log_utils.py"
    ]
    
    optional_files = [
        "ai_decision_log.jsonl",
        "trade_log.csv"
    ]
    
    all_good = True
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - REQUIRED")
            all_good = False
    
    for file in optional_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"⚠️ {file} - Will be created when bot runs")
    
    # Check directories
    if not os.path.exists("backups"):
        os.makedirs("backups")
        print("✅ Created backups directory")
    else:
        print("✅ backups/ directory exists")
    
    return all_good

def create_startup_script():
    """Create startup script for the GUI"""
    print("\n📝 Creating startup script...")
    
    script_content = """#!/bin/bash
# D.E.V.I GUI Startup Script

echo "🤖 Starting D.E.V.I Trading Bot GUI..."
echo "📍 Access URL will be shown below"
echo "🔑 Default password: devi2025beta"
echo "="*50

# Start Streamlit
streamlit run streamlit_app.py --server.port 8501 --server.headless true
"""
    
    with open("start_gui.sh", "w") as f:
        f.write(script_content)
    
    # Make executable on Unix systems
    if platform.system() != "Windows":
        os.chmod("start_gui.sh", 0o755)
    
    print("✅ Created start_gui.sh")
    
    # Create Windows batch file
    batch_content = """@echo off
echo 🤖 Starting D.E.V.I Trading Bot GUI...
echo 📍 Access URL will be shown below
echo 🔑 Default password: devi2025beta
echo ==================================================

streamlit run streamlit_app.py --server.port 8501 --server.headless true
pause
"""
    
    with open("start_gui.bat", "w") as f:
        f.write(batch_content)
    
    print("✅ Created start_gui.bat")

def setup_hosting_info():
    """Provide hosting setup information"""
    print("\n🌐 Hosting Setup Information")
    print("="*40)
    
    print("\n📋 Option 1: Local Network Access")
    print("   • Run: streamlit run streamlit_app.py")
    print("   • Access: http://localhost:8501")
    print("   • Share on LAN: Add --server.address 0.0.0.0")
    
    print("\n📋 Option 2: ngrok (Recommended for team access)")
    print("   • Install: https://ngrok.com/download")
    print("   • Start GUI: ./start_gui.sh (or start_gui.bat)")
    print("   • In another terminal: ngrok http 8501")
    print("   • Share the ngrok URL with team")
    
    print("\n📋 Option 3: Cloudflare Tunnel")
    print("   • Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/")
    print("   • Run: cloudflared tunnel --url http://localhost:8501")
    
    print("\n📋 Option 4: VPS Deployment")
    print("   • Upload files to VPS")
    print("   • Install dependencies: pip install -r requirements.txt")
    print("   • Run: streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0")
    print("   • Access via VPS IP:8501")
    
    print("\n🔐 Security Notes:")
    print("   • Change password in streamlit_app.py (line 47)")
    print("   • Consider adding IP restrictions")
    print("   • Use HTTPS in production")

def test_streamlit():
    """Test if streamlit works"""
    print("\n🧪 Testing Streamlit installation...")
    try:
        result = subprocess.run([sys.executable, "-c", "import streamlit; print('Streamlit version:', streamlit.__version__)"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
            return True
        else:
            print("❌ Streamlit test failed")
            return False
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        print("❌ Streamlit test failed")
        return False

def main():
    """Main setup function"""
    print_banner()
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Test streamlit
    if not test_streamlit():
        return False
    
    # Check files
    if not check_files():
        print("\n❌ Missing required files. Please ensure all files are present.")
        return False
    
    # Create startup scripts
    create_startup_script()
    
    # Setup hosting info
    setup_hosting_info()
    
    print("\n" + "="*60)
    print("🎉 Setup Complete!")
    print("🚀 To start the GUI:")
    print("   • Linux/Mac: ./start_gui.sh")
    print("   • Windows: start_gui.bat")
    print("   • Manual: streamlit run streamlit_app.py")
    print("\n🔑 Default password: devi2025beta")
    print("👥 Team: Enoch, Roni, Terry")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)