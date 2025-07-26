#!/bin/bash
# D.E.V.I GUI Startup Script

echo "🤖 Starting D.E.V.I Trading Bot GUI..."
echo "📍 Access URL will be shown below"
echo "🔑 Default password: devi2025beta"
echo "=================================================="

# Add local bin to PATH for this session
export PATH="$HOME/.local/bin:$PATH"

# Start Streamlit
python3 -m streamlit run streamlit_app.py --server.port 8501 --server.headless true