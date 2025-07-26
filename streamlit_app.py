# ------------------------------------------------------------------------------------
# 🚀 D.E.V.I Trading Bot GUI (Internal Shared Beta)
#
# This Streamlit app provides a comprehensive interface for the D.E.V.I trading bot:
#
# ✅ Live Config Editing with Validation & Backup
# ✅ Trade Log Viewer with Advanced Filtering
# ✅ AI Decision Log Analysis with Matching
# ✅ Performance Metrics & Analytics
# ✅ Password Protection for Team Access
# ✅ Export Functionality (CSV/Excel)
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot - Internal Beta
# ------------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import json
import MetaTrader5 as mt5
from datetime import datetime, timedelta, date
import plotly.express as px
import plotly.graph_objects as go
from utils.config_manager import config_manager
from utils.log_utils import log_processor
import os
import time

# === App Configuration ===
st.set_page_config(
    page_title="D.E.V.I Trading Bot GUI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === Authentication ===
def check_password():
    """Basic password protection for team access"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 D.E.V.I Trading Bot Access")
        st.markdown("### Internal Shared Beta - Team Access Only")
        
        password = st.text_input("Enter Access Password:", type="password")
        
        if st.button("🚀 Access Dashboard"):
            # TODO: Replace with your team password
            if password == "devi2025beta":  # Change this password
                st.session_state.authenticated = True
                st.success("✅ Access Granted! Redirecting...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Invalid password. Contact Terry for access.")
        
        st.markdown("---")
        st.markdown("**Team Members:** Enoch, Roni, Terry")
        st.markdown("**Version:** Internal Beta v1.0")
        return False
    
    return True

# === Utility Functions ===
@st.cache_data(ttl=60)  # Cache for 1 minute
def load_mt5_positions():
    """Load current MT5 positions"""
    try:
        if not mt5.initialize():
            return pd.DataFrame()
        
        positions = mt5.positions_get()
        mt5.shutdown()
        
        if not positions:
            return pd.DataFrame()
        
        positions_df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
        return positions_df[["symbol", "type", "volume", "price_open", "profit", "time"]]
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_mt5_trade_history(days=7):
    """Load MT5 trade history"""
    try:
        if not mt5.initialize():
            return pd.DataFrame()

        utc_from = datetime.now() - timedelta(days=days)
        utc_to = datetime.now()

        deals = mt5.history_deals_get(utc_from, utc_to)
        mt5.shutdown()

        if not deals:
            return pd.DataFrame()

        deals_df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
        deals_df = deals_df[["symbol", "time", "type", "volume", "price", "profit"]]
        deals_df["time"] = pd.to_datetime(deals_df["time"], unit="s")
        deals_df["type"] = deals_df["type"].apply(lambda x: "BUY" if x == 0 else "SELL")
        return deals_df
    except:
        return pd.DataFrame()

def render_config_editor():
    """Render the configuration editor section"""
    st.header("⚙️ Live Configuration Editor")
    
    # Load current config
    config_data = config_manager.load_config()
    
    if not config_data or not config_data.get("CONFIG"):
        st.error("❌ Failed to load configuration file")
        return
    
    config = config_data["CONFIG"]
    ftmo_params = config_data["FTMO_PARAMS"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Trading Parameters")
        
        # Core trading settings
        min_score = st.number_input(
            "Minimum Score for Trade",
            min_value=0,
            max_value=10,
            value=config.get("min_score_for_trade", 6),
            help="Minimum technical score required before considering AI decision"
        )
        
        lot_size = st.number_input(
            "Default Lot Size",
            min_value=0.01,
            max_value=100.0,
            value=config.get("lot_size", 1.25),
            step=0.01,
            help="Default trade volume"
        )
        
        sl_pips = st.number_input(
            "Stop Loss (Pips)",
            min_value=1,
            max_value=500,
            value=config.get("sl_pips", 50),
            help="Fallback SL distance"
        )
        
        tp_pips = st.number_input(
            "Take Profit (Pips)",
            min_value=1,
            max_value=1000,
            value=config.get("tp_pips", 100),
            help="Fallback TP distance"
        )
        
        delay_seconds = st.number_input(
            "Loop Delay (Seconds)",
            min_value=60,
            max_value=3600,
            value=config.get("delay_seconds", 900),
            step=60,
            help="Time between bot cycles"
        )
        
        # Profit Guard Settings
        st.subheader("💰 Profit Guard")
        partial_close = st.number_input(
            "Partial Close Trigger (%)",
            min_value=0.1,
            max_value=10.0,
            value=config.get("partial_close_trigger_percent", 1.0),
            step=0.1,
            help="Profit % to trigger partial close"
        )
        
        full_close = st.number_input(
            "Full Close Trigger (%)",
            min_value=0.1,
            max_value=20.0,
            value=config.get("full_close_trigger_percent", 2.0),
            step=0.1,
            help="Profit % to trigger full close"
        )
    
    with col2:
        st.subheader("🎚️ Strategy Toggles")
        
        # Strategy toggles
        use_engulfing = st.checkbox(
            "Use Engulfing Patterns",
            value=config.get("use_engulfing", True)
        )
        
        use_bos = st.checkbox(
            "Use Break of Structure",
            value=config.get("use_bos", True)
        )
        
        use_liquidity_sweep = st.checkbox(
            "Use Liquidity Sweep",
            value=config.get("use_liquidity_sweep", True)
        )
        
        use_rsi = st.checkbox(
            "Use RSI Indicator",
            value=config.get("use_rsi", True)
        )
        
        use_fib = st.checkbox(
            "Use Fibonacci",
            value=config.get("use_fib", True)
        )
        
        # USD Trading Control
        st.subheader("🇺🇸 USD Trading Control")
        restrict_usd = st.checkbox(
            "Restrict USD to AM Session",
            value=config.get("restrict_usd_to_am", True),
            help="Limit USD pairs to morning session only"
        )
        
        if restrict_usd:
            allowed_window = config.get("allowed_trading_window", {"start_hour": 14, "end_hour": 16})
            start_hour = st.slider(
                "USD Window Start Hour",
                min_value=0,
                max_value=23,
                value=allowed_window.get("start_hour", 14)
            )
            
            end_hour = st.slider(
                "USD Window End Hour",
                min_value=0,
                max_value=23,
                value=allowed_window.get("end_hour", 16)
            )
        
        # FTMO Parameters
        st.subheader("🏆 FTMO Parameters")
        initial_balance = st.number_input(
            "Initial Balance",
            min_value=1000,
            max_value=1000000,
            value=ftmo_params.get("initial_balance", 10000),
            step=1000
        )
        
        max_daily_loss = st.number_input(
            "Max Daily Loss (%)",
            min_value=1,
            max_value=10,
            value=int(ftmo_params.get("max_daily_loss_pct", 0.05) * 100),
            help="Maximum daily loss percentage"
        )
    
    # Save Configuration
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("💾 Save Configuration", type="primary"):
            # Build updated config
            updated_config = config.copy()
            updated_config.update({
                "min_score_for_trade": min_score,
                "lot_size": lot_size,
                "sl_pips": sl_pips,
                "tp_pips": tp_pips,
                "delay_seconds": delay_seconds,
                "partial_close_trigger_percent": partial_close,
                "full_close_trigger_percent": full_close,
                "use_engulfing": use_engulfing,
                "use_bos": use_bos,
                "use_liquidity_sweep": use_liquidity_sweep,
                "use_rsi": use_rsi,
                "use_fib": use_fib,
                "restrict_usd_to_am": restrict_usd,
            })
            
            if restrict_usd:
                updated_config["allowed_trading_window"] = {
                    "start_hour": start_hour,
                    "end_hour": end_hour
                }
            
            updated_ftmo = ftmo_params.copy()
            updated_ftmo.update({
                "initial_balance": initial_balance,
                "max_daily_loss_pct": max_daily_loss / 100
            })
            
            # Validate and save
            new_config_data = {
                "CONFIG": updated_config,
                "FTMO_PARAMS": updated_ftmo
            }
            
            is_valid, errors = config_manager.validate_config(new_config_data)
            
            if is_valid:
                success = config_manager.save_config(new_config_data)
                if success:
                    st.success("✅ Configuration saved successfully! Bot will reload config automatically.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to save configuration")
            else:
                st.error("❌ Configuration validation failed:")
                for error in errors:
                    st.error(f"• {error}")
    
    with col2:
        if st.button("🔄 Reload Config"):
            st.rerun()
    
    with col3:
        if st.button("📦 View Backups"):
            st.session_state.show_backups = True

def render_trade_logs():
    """Render the trade logs section"""
    st.header("📊 Trade Logs & History")
    
    # Load trade data
    csv_trades = log_processor.load_trade_log()
    mt5_trades = load_mt5_trade_history()
    
    tab1, tab2, tab3 = st.tabs(["📈 CSV Trade Log", "🔴 Live MT5 History", "⚡ Current Positions"])
    
    with tab1:
        st.subheader("CSV Trade Log")
        
        if not csv_trades.empty:
            # Filters
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                symbols = log_processor.get_unique_symbols(csv_trades)
                selected_symbols = st.multiselect("Filter Symbols", symbols)
            
            with col2:
                actions = csv_trades['action'].unique().tolist() if 'action' in csv_trades.columns else []
                selected_actions = st.multiselect("Filter Actions", actions)
            
            with col3:
                start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=7))
            
            with col4:
                end_date = st.date_input("End Date", value=datetime.now().date())
            
            # Apply filters
            filters = {
                'symbols': selected_symbols,
                'actions': selected_actions,
                'start_date': start_date,
                'end_date': end_date
            }
            
            filtered_trades = log_processor.filter_trade_log(csv_trades, **filters)
            
            # Display metrics
            if not filtered_trades.empty:
                metrics = log_processor.calculate_trade_metrics(filtered_trades)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Trades", metrics.get('total_trades', 0))
                with col2:
                    st.metric("Executed", metrics.get('executed_trades', 0))
                with col3:
                    st.metric("Total Volume", f"{metrics.get('total_volume', 0):.2f}")
                with col4:
                    st.metric("Avg Lot Size", f"{metrics.get('average_lot_size', 0):.2f}")
                
                # Display table
                st.dataframe(filtered_trades, use_container_width=True)
                
                # Export options
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📥 Export CSV"):
                        filename = f"trade_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        log_processor.export_to_csv(filtered_trades, filename)
                        st.success(f"✅ Exported to {filename}")
                
                with col2:
                    if st.button("📊 Export Excel"):
                        filename = f"trade_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        log_processor.export_to_excel(filtered_trades, filename)
                        st.success(f"✅ Exported to {filename}")
            else:
                st.warning("No trades found with current filters")
        else:
            st.info("No CSV trade log data available")
    
    with tab2:
        st.subheader("Live MT5 Trade History")
        
        if not mt5_trades.empty:
            st.dataframe(mt5_trades, use_container_width=True)
            
            # Quick stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Deals", len(mt5_trades))
            with col2:
                total_profit = mt5_trades['profit'].sum()
                st.metric("Total P&L", f"${total_profit:.2f}")
            with col3:
                avg_volume = mt5_trades['volume'].mean()
                st.metric("Avg Volume", f"{avg_volume:.2f}")
        else:
            st.info("No MT5 trade history available")
    
    with tab3:
        st.subheader("Current Open Positions")
        
        positions = load_mt5_positions()
        if not positions.empty:
            st.dataframe(positions, use_container_width=True)
            
            # Position metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Open Positions", len(positions))
            with col2:
                total_profit = positions['profit'].sum()
                st.metric("Unrealized P&L", f"${total_profit:.2f}")
            with col3:
                total_volume = positions['volume'].sum()
                st.metric("Total Volume", f"{total_volume:.2f}")
        else:
            st.info("No open positions")

def render_ai_decisions():
    """Render the AI decisions section"""
    st.header("🤖 AI Decision Analysis")
    
    # Load AI decision data
    ai_log = log_processor.load_ai_decision_log()
    
    if ai_log.empty:
        st.info("No AI decision log data available")
        return
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        symbols = log_processor.get_unique_symbols(ai_log)
        selected_symbols = st.multiselect("Filter Symbols", symbols, key="ai_symbols")
    
    with col2:
        decisions = ai_log['ai_decision'].unique().tolist() if 'ai_decision' in ai_log.columns else []
        selected_decisions = st.multiselect("Filter Decisions", decisions, key="ai_decisions")
    
    with col3:
        executed_only = st.checkbox("Executed Only", key="ai_executed")
    
    with col4:
        override_only = st.checkbox("AI Override Only", key="ai_override")
    
    # Date range
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=7), key="ai_start")
    with col2:
        end_date = st.date_input("End Date", value=datetime.now().date(), key="ai_end")
    
    # Apply filters
    filters = {
        'symbols': selected_symbols,
        'decisions': selected_decisions,
        'executed_only': executed_only,
        'override_only': override_only,
        'start_date': start_date,
        'end_date': end_date
    }
    
    filtered_ai = log_processor.filter_ai_log(ai_log, **filters)
    
    # Display metrics
    if not filtered_ai.empty:
        metrics = log_processor.calculate_ai_metrics(filtered_ai)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Decisions", metrics.get('total_decisions', 0))
        with col2:
            execution_rate = metrics.get('execution_rate', 0)
            st.metric("Execution Rate", f"{execution_rate:.1f}%")
        with col3:
            override_rate = metrics.get('override_rate', 0)
            st.metric("Override Rate", f"{override_rate:.1f}%")
        with col4:
            avg_confidence = metrics.get('average_confidence', 0)
            if avg_confidence:
                st.metric("Avg Confidence", f"{avg_confidence:.1f}")
            else:
                st.metric("Avg Confidence", "N/A")
        
        # Decision distribution chart
        if 'decision_distribution' in metrics:
            decision_dist = metrics['decision_distribution']
            if decision_dist:
                fig = px.pie(values=list(decision_dist.values()), 
                           names=list(decision_dist.keys()), 
                           title="Decision Distribution")
                st.plotly_chart(fig, use_container_width=True)
        
        # Display table
        st.dataframe(filtered_ai, use_container_width=True)
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export AI Log CSV", key="export_ai_csv"):
                filename = f"ai_decisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                log_processor.export_to_csv(filtered_ai, filename)
                st.success(f"✅ Exported to {filename}")
        
        with col2:
            if st.button("📊 Export AI Log Excel", key="export_ai_excel"):
                filename = f"ai_decisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                log_processor.export_to_excel(filtered_ai, filename)
                st.success(f"✅ Exported to {filename}")
    else:
        st.warning("No AI decisions found with current filters")

def render_analytics():
    """Render analytics and matching section"""
    st.header("📈 Performance Analytics")
    
    # Load data
    ai_log = log_processor.load_ai_decision_log()
    trade_log = log_processor.load_trade_log()
    
    if ai_log.empty and trade_log.empty:
        st.info("No data available for analytics")
        return
    
    # AI Decision vs Trade Matching
    if not ai_log.empty and not trade_log.empty:
        st.subheader("🔄 AI Decision vs Trade Matching")
        
        tolerance = st.slider("Matching Tolerance (minutes)", 1, 60, 5)
        matched_data = log_processor.match_ai_with_trades(ai_log, trade_log, tolerance)
        
        if not matched_data.empty:
            match_rate = (matched_data['trade_matched'].sum() / len(matched_data)) * 100
            st.metric("Match Rate", f"{match_rate:.1f}%")
            
            # Show matched decisions
            matched_only = matched_data[matched_data['trade_matched'] == True]
            if not matched_only.empty:
                st.subheader("✅ Matched Decisions")
                st.dataframe(matched_only[['timestamp', 'symbol', 'ai_decision', 'confidence', 
                                         'trade_price', 'trade_lot', 'reasoning']], 
                           use_container_width=True)
    
    # Recent activity
    if not ai_log.empty:
        st.subheader("⚡ Recent AI Activity (24h)")
        recent_ai = log_processor.get_recent_entries(ai_log, 24)
        if not recent_ai.empty:
            st.dataframe(recent_ai[['timestamp', 'symbol', 'ai_decision', 'confidence', 'executed']], 
                       use_container_width=True)
        else:
            st.info("No recent AI activity")

def render_sidebar():
    """Render the sidebar with status and controls"""
    st.sidebar.title("🤖 D.E.V.I Control Panel")
    st.sidebar.markdown("---")
    
    # Bot Status
    st.sidebar.subheader("🔋 Bot Status")
    
    # Check if bot is running (simple file check)
    bot_running = os.path.exists("trade_state.json")
    if bot_running:
        st.sidebar.success("✅ Bot is Running")
    else:
        st.sidebar.warning("⚠️ Bot Status Unknown")
    
    # Quick stats
    st.sidebar.subheader("📊 Quick Stats")
    
    # Load recent data
    ai_log = log_processor.load_ai_decision_log()
    trade_log = log_processor.load_trade_log()
    
    if not ai_log.empty:
        recent_decisions = log_processor.get_recent_entries(ai_log, 24)
        st.sidebar.metric("24h AI Decisions", len(recent_decisions))
    
    if not trade_log.empty:
        recent_trades = log_processor.get_recent_entries(trade_log, 24)
        st.sidebar.metric("24h Trades", len(recent_trades))
    
    # Config backups
    st.sidebar.subheader("💾 Backups")
    backups = config_manager.get_backup_list()
    if backups:
        st.sidebar.write(f"Available: {len(backups)} backups")
        if st.sidebar.button("📂 View Backups"):
            st.session_state.show_backups = True
    else:
        st.sidebar.write("No backups available")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Version:** Internal Beta v1.0")
    st.sidebar.markdown("**Team:** Enoch, Roni, Terry")

def main():
    """Main application function"""
    # Check authentication
    if not check_password():
        return
    
    # Render sidebar
    render_sidebar()
    
    # Main title
    st.title("🤖 D.E.V.I Trading Bot Dashboard")
    st.markdown("### Internal Shared Beta - Live Configuration & Analytics")
    
    # Navigation tabs
    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Configuration", "📊 Trade Logs", "🤖 AI Decisions", "📈 Analytics"])
    
    with tab1:
        render_config_editor()
    
    with tab2:
        render_trade_logs()
    
    with tab3:
        render_ai_decisions()
    
    with tab4:
        render_analytics()
    
    # Handle backup modal
    if st.session_state.get('show_backups', False):
        st.markdown("---")
        st.subheader("📦 Configuration Backups")
        
        backups = config_manager.get_backup_list()
        if backups:
            for backup in backups[:10]:  # Show last 10 backups
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(backup['filename'])
                with col2:
                    st.write(backup['timestamp'].strftime("%Y-%m-%d %H:%M"))
                with col3:
                    if st.button("📁", key=f"backup_{backup['filename']}"):
                        st.info(f"Backup path: {backup['path']}")
        
        if st.button("❌ Close Backups"):
            st.session_state.show_backups = False
            st.rerun()
    
    # Auto-refresh option
    st.sidebar.markdown("---")
    auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh (30s)")
    if auto_refresh:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()