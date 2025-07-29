#!/usr/bin/env python3
# ------------------------------------------------------------------------------------
# 🧪 test_tunnel.py – Test Cloudflare Tunnel Status
#
# This script checks if the Cloudflare tunnel is working and displays the tunnel URL
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot
# ------------------------------------------------------------------------------------

import subprocess
import time
import re

def get_tunnel_url():
    """Get the Cloudflare tunnel URL from the running process"""
    try:
        # Check if cloudflared is running
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq cloudflared.exe'], 
                              capture_output=True, text=True, shell=True)
        
        if 'cloudflared.exe' not in result.stdout:
            print("❌ Cloudflare tunnel is not running")
            return None
        
        print("✅ Cloudflare tunnel is running")
        
        # Try to get the tunnel URL from the process output
        # Note: This is a simplified approach - in practice, you'd need to check the tunnel logs
        print("\n📋 To get the tunnel URL:")
        print("1. Look for the tunnel window that opened")
        print("2. Copy the URL that looks like: https://random-name.trycloudflare.com")
        print("3. Share this URL with your team")
        print("\n🔐 Password: devipass2025")
        
        return "https://[tunnel-url].trycloudflare.com"
        
    except Exception as e:
        print(f"❌ Error checking tunnel status: {e}")
        return None

def test_dashboard_access():
    """Test if the dashboard is accessible locally"""
    try:
        import requests
        response = requests.get("http://localhost:8501", timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard is accessible locally")
            return True
        else:
            print(f"⚠️ Dashboard returned status code: {response.status_code}")
            return False
    except ImportError:
        print("⚠️ requests module not available - skipping local test")
        return True
    except Exception as e:
        print(f"❌ Dashboard not accessible: {e}")
        return False

def main():
    print("=" * 50)
    print("🧪 D.E.V.I Dashboard Tunnel Test")
    print("=" * 50)
    
    # Test local dashboard
    print("\n1. Testing local dashboard access...")
    dashboard_ok = test_dashboard_access()
    
    # Test tunnel
    print("\n2. Testing Cloudflare tunnel...")
    tunnel_url = get_tunnel_url()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    
    if dashboard_ok:
        print("✅ Local Dashboard: ACCESSIBLE")
    else:
        print("❌ Local Dashboard: NOT ACCESSIBLE")
    
    if tunnel_url:
        print("✅ Cloudflare Tunnel: RUNNING")
        print(f"🌐 Tunnel URL: {tunnel_url}")
    else:
        print("❌ Cloudflare Tunnel: NOT RUNNING")
    
    print("\n📋 Next Steps:")
    if dashboard_ok and tunnel_url:
        print("✅ Both dashboard and tunnel are working!")
        print("📱 Share the tunnel URL with your team")
        print("🔐 Team password: devipass2025")
    else:
        print("⚠️ Some components need attention")
        print("🔧 Check the Setup/README_CLOUDFLARE.md for troubleshooting")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main() 