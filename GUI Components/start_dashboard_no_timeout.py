#!/usr/bin/env python3
"""
D.E.V.I Dashboard Startup Script with Timeout Prevention
"""

import subprocess
import sys
import os

def start_dashboard():
    """Start the Streamlit dashboard with timeout prevention settings"""
    
    # Streamlit configuration to prevent timeouts
    env = os.environ.copy()
    env['STREAMLIT_SERVER_MAX_UPLOAD_SIZE'] = '200'
    env['STREAMLIT_SERVER_ADDRESS'] = 'localhost'
    env['STREAMLIT_SERVER_PORT'] = '8501'
    env['STREAMLIT_SERVER_HEADLESS'] = 'true'
    env['STREAMLIT_SERVER_ENABLE_CORS'] = 'false'
    env['STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION'] = 'false'
    
    # Add timeout prevention settings
    env['STREAMLIT_SERVER_RUN_ON_SAVE'] = 'false'
    env['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'
    
    # Command to start Streamlit with timeout prevention
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', 'streamlit_app.py',
        '--server.port', '8501',
        '--server.address', 'localhost',
        '--server.headless', 'true',
        '--server.enableCORS', 'false',
        '--server.enableXsrfProtection', 'false',
        '--server.runOnSave', 'false',
        '--server.fileWatcherType', 'none',
        '--browser.gatherUsageStats', 'false'
    ]
    
    print("🚀 Starting D.E.V.I Dashboard with timeout prevention...")
    print("📊 Dashboard will be available at: http://localhost:8501")
    print("⏰ Auto-refresh enabled to prevent timeouts")
    print("🔄 Press Ctrl+C to stop the dashboard")
    
    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    start_dashboard() 