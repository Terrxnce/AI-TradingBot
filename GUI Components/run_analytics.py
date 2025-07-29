#!/usr/bin/env python3
# ------------------------------------------------------------------------------------
# 🧠 run_analytics.py – Standalone D.E.V.I Analytics Dashboard
#
# Run this script to launch the comprehensive analytics dashboard independently:
# python run_analytics.py
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot
# ------------------------------------------------------------------------------------

import streamlit as st
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

def main():
    """Launch the analytics dashboard"""
    try:
        from analytics_dashboard import AnalyticsDashboard
        
        # Set page config
        st.set_page_config(
            page_title="D.E.V.I Analytics Dashboard",
            page_icon="🧠",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Initialize and render dashboard
        dashboard = AnalyticsDashboard()
        dashboard.render_dashboard()
        
    except ImportError as e:
        st.error(f"Error importing analytics dashboard: {e}")
        st.info("Please ensure analytics_dashboard.py is in the same directory")
    except Exception as e:
        st.error(f"Error running analytics dashboard: {e}")

if __name__ == "__main__":
    main() 