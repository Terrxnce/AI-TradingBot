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
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
import sys
from io import BytesIO
import MetaTrader5 as mt5

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))  # Add root directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Bot Core'))  # Add Bot Core directory

from utils.config_manager import config_manager

# Initialize log processor with explicit paths
script_dir = os.path.dirname(__file__)
ai_log_path = os.path.join(script_dir, "..", "Bot Core", "ai_decision_log.jsonl")
trade_log_path = os.path.join(script_dir, "..", "Bot Core", "logs", "trade_log.csv")

from utils.log_utils import LogProcessor
log_processor = LogProcessor(ai_log_file=ai_log_path, trade_log_file=trade_log_path)

# Try to import performance_metrics with fallback
try:
    from performance_metrics import performance_metrics
except ImportError:
    try:
        # Try alternative import path
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from performance_metrics import performance_metrics
    except ImportError:
        # Create a dummy performance_metrics if import fails
        class DummyPerformanceMetrics:
            def generate_performance_report(self):
                return {'overall_metrics': {}}
            def get_mt5_account_balance(self):
                return 10000 # Default balance for dummy
            def get_mt5_account_equity(self):
                return 10000 # Default equity for dummy
        performance_metrics = DummyPerformanceMetrics()

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
    except Exception as e:
        st.error(f"Error loading MT5 positions: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=10)  # Cache for 10 seconds
def load_bot_heartbeat():
    """Load bot heartbeat data"""
    try:
        # Try multiple possible paths for bot_heartbeat.json
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'bot_heartbeat.json'),
            os.path.join(os.path.dirname(__file__), '..', 'Bot Core', 'bot_heartbeat.json'),
            "bot_heartbeat.json"
        ]
        
        for heartbeat_file in possible_paths:
            if os.path.exists(heartbeat_file):
                with open(heartbeat_file, 'r') as f:
                    return json.load(f)
        return None
    except Exception as e:
        st.error(f"Error loading heartbeat: {e}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_mt5_trade_history(days=30):
    """Load MT5 trade history"""
    try:
        if not mt5.initialize():
            return pd.DataFrame()
        
        # Get more history to ensure we capture all trades
        utc_from = datetime(2025, 7, 21)  # From July 21st
        utc_to = datetime.now()
        deals = mt5.history_deals_get(utc_from, utc_to)
        mt5.shutdown()

        if not deals:
            return pd.DataFrame()

        deals_df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
        deals_df = deals_df[["symbol", "time", "type", "volume", "price", "profit"]]
        deals_df["time"] = pd.to_datetime(deals_df["time"], unit="s")
        deals_df["type"] = deals_df["type"].apply(lambda x: "BUY" if x == 0 else "SELL")
        
        # Sort by time (newest first)
        deals_df = deals_df.sort_values('time', ascending=False)
        
        return deals_df
    except Exception as e:
        st.error(f"Error loading MT5 trade history: {e}")
        return pd.DataFrame()

def sync_trade_log_with_mt5():
    """Sync CSV trade log with MT5 history to show all trades"""
    try:
        if not mt5.initialize():
            return False
        
        # Get all deals from July 21st onwards
        utc_from = datetime(2025, 7, 21)
        utc_to = datetime.now()
        deals = mt5.history_deals_get(utc_from, utc_to)
        mt5.shutdown()

        if not deals:
            return False

        # Convert to DataFrame
        deals_df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
        
        # Filter for USDJPY trades only and exclude non-trade deals
        # Only include deals with type 0 (BUY) or 1 (SELL) - actual trades
        usdjpy_trades = deals_df[
            (deals_df['symbol'] == 'USDJPY') & 
            (deals_df['type'].isin([0, 1]))  # Only BUY/SELL trades
        ].copy()
        
        if usdjpy_trades.empty:
            return False
        
        # Format for CSV trade log
        trade_log_data = []
        for _, deal in usdjpy_trades.iterrows():
            trade_data = {
                "timestamp": pd.to_datetime(deal['time'], unit='s'),
                "symbol": deal['symbol'],
                "direction": "BUY" if deal['type'] == 0 else "SELL",
                "lot": deal['volume'],
                "sl": 0,  # MT5 doesn't provide SL/TP in deals
                "tp": 0,
                "entry_price": deal['price'],
                "result": "EXECUTED"  # All historical deals are executed
            }
            trade_log_data.append(trade_data)
        
        # Create DataFrame and save to CSV
        trade_log_df = pd.DataFrame(trade_log_data)
        trade_log_df = trade_log_df.sort_values('timestamp', ascending=False)
        
        # Save to the correct path
        log_path = os.path.join(os.path.dirname(__file__), "..", "Bot Core", "logs", "trade_log.csv")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        trade_log_df.to_csv(log_path, index=False)
        
        print(f"✅ Synced {len(trade_log_df)} trades from MT5")
        return True
        
    except Exception as e:
        st.error(f"Error syncing trade log: {e}")
        return False

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
        
        # Add sync button
        if st.button("🔄 Sync with MT5", key="sync_trades"):
            if sync_trade_log_with_mt5():
                st.success("✅ Trade log synced with MT5 data!")
                st.rerun()
            else:
                st.error("❌ Failed to sync trade log")
        
        csv_trades = log_processor.load_trade_log()
        
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
                
                # Display additional info for each trade
                for idx, row in filtered_trades.iterrows():
                    with st.expander(f"Trade {idx} - {row.get('symbol', 'N/A')}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.text(f"Action: {row.get('action', 'N/A')}")
                            st.text(f"Price: {row.get('price', 'N/A')}")
                            st.text(f"Volume: {row.get('volume', 'N/A')}")
                        with col2:
                            technical_score = row.get('technical_score', 'N/A')
                            ema_trend = row.get('ema_trend', 'N/A')
                            st.text(f"Technical Score: {technical_score}")
                            st.text(f"EMA Trend: {ema_trend}")
                
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
        st.info("Note: This shows all MT5 deals (including non-trade transactions)")
        
        # Get actual MT5 account balance
        mt5_balance = performance_metrics.get_mt5_account_balance()
        
        if not mt5_trades.empty:
            # Filter for actual trades only (BUY/SELL)
            actual_trades = mt5_trades[mt5_trades['type'].isin(['BUY', 'SELL'])]
            
            # Filter for USDJPY trades only for display
            usdjpy_trades = actual_trades[actual_trades['symbol'] == 'USDJPY']
            
            st.dataframe(usdjpy_trades, use_container_width=True)
            
            # Quick stats
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Trades", len(usdjpy_trades))
            
            with col2:
                # Show actual account balance instead of calculated P&L
                if mt5_balance is not None:
                    st.metric("Account Balance", f"${mt5_balance:.2f}")
                else:
                    st.metric("Account Balance", "N/A")
            
            with col3:
                avg_volume = usdjpy_trades['volume'].mean() if not usdjpy_trades.empty else 0
                st.metric("Avg Volume", f"{avg_volume:.2f}")
            
            with col4:
                # Show most recent trade
                if not usdjpy_trades.empty:
                    latest_trade = usdjpy_trades.iloc[0]  # Already sorted by time
                    st.metric("Latest Trade", f"{latest_trade['symbol']} {latest_trade['type']}")
                else:
                    st.metric("Latest Trade", "N/A")
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
        start_date = st.date_input("Start Date", value=datetime(2025, 7, 27).date(), key="ai_start")
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
    
    # Add sync button for trade data
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("🔄 Refresh Performance Metrics", key="refresh_metrics"):
            st.cache_data.clear()
    with col2:
        if st.button("📊 Sync Trade Data", key="sync_analytics"):
            if sync_trade_log_with_mt5():
                st.success("✅ Trade data synced!")
                st.rerun()
            else:
                st.error("❌ Failed to sync trade data")
    with col3:
        if st.button("🔄 Force MT5 Refresh", key="force_mt5_refresh"):
            st.cache_data.clear()
            st.success("✅ MT5 data refreshed! Reloading...")
            st.rerun()
    
    # Load data at the beginning
    ai_log = log_processor.load_ai_decision_log()
    trade_log = log_processor.load_trade_log()
    
    # Generate performance report
    if st.button("🔄 Refresh Performance Metrics"):
        st.cache_data.clear()
    
    # Load performance metrics
    try:
        report = performance_metrics.generate_performance_report()
        overall_metrics = report.get('overall_metrics', {})
        
        if not overall_metrics:
            st.info("No performance data available. Run some trades first!")
            
            # Fallback to basic analytics
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
            return
        
        # Performance Summary Section
        st.subheader("📊 Performance Summary")
        
        # Overall metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Trades", overall_metrics.get('total_trades', 0))
            st.metric("Executed Trades", overall_metrics.get('executed_trades', 0))
        
        with col2:
            execution_rate = overall_metrics.get('execution_rate', 0)
            st.metric("Execution Rate", f"{execution_rate * 100:.1f}%")
            st.metric("Avg Lot Size", f"{overall_metrics.get('avg_lot_size', 0):.2f}")
        
        with col3:
            st.metric("Most Traded Symbol", overall_metrics.get('most_traded_symbol', 'N/A'))
            st.metric("Most Active Session", overall_metrics.get('most_active_session', 'N/A'))
        
        with col4:
            # Calculate actual P&L from trade data
            if not trade_log.empty and 'profit' in trade_log.columns:
                total_pnl = trade_log['profit'].sum()
                win_rate = len(trade_log[trade_log['profit'] > 0]) / len(trade_log) * 100 if len(trade_log) > 0 else 0
                st.metric("Total P&L", f"${total_pnl:.2f}")
                st.metric("Win Rate", f"{win_rate:.1f}%")
            else:
                st.metric("Total P&L", "$0.00")
                st.metric("Win Rate", "0.0%")
        
        # Additional performance insights
        st.subheader("📈 Performance Insights")
        
        # Recent performance trends
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Last 7 days performance
            if not trade_log.empty and 'profit' in trade_log.columns:
                seven_days_ago = datetime.now() - timedelta(days=7)
                recent_trades = trade_log[trade_log['timestamp'] >= seven_days_ago]
                recent_pnl = recent_trades['profit'].sum()
                st.metric("7-Day P&L", f"${recent_pnl:.2f}")
            else:
                st.metric("7-Day P&L", "$0.00")
        
        with col2:
            # Total volume traded
            if not trade_log.empty:
                if 'volume' in trade_log.columns:
                    total_volume = trade_log['volume'].sum()
                elif 'lot' in trade_log.columns:
                    total_volume = trade_log['lot'].sum()
                else:
                    total_volume = 0
                st.metric("Total Volume", f"{total_volume:.2f}")
            else:
                st.metric("Total Volume", "0.00")
        
        with col3:
            # Best performing symbol
            if not trade_log.empty and 'profit' in trade_log.columns and 'symbol' in trade_log.columns:
                symbol_performance = trade_log.groupby('symbol')['profit'].sum()
                if not symbol_performance.empty:
                    best_symbol = symbol_performance.idxmax()
                    best_pnl = symbol_performance.max()
                    st.metric("Best Symbol", f"{best_symbol} (${best_pnl:.2f})")
                else:
                    st.metric("Best Symbol", "N/A")
            else:
                st.metric("Best Symbol", "N/A")
        
        # Symbol performance
        st.subheader("📈 Symbol Performance")
        symbol_metrics = report.get('symbol_metrics', {})
        
        if symbol_metrics:
            symbol_df = pd.DataFrame.from_dict(symbol_metrics, orient='index')
            symbol_df = symbol_df.reset_index()
            symbol_df.columns = ['Symbol', 'Trades', 'Profit', 'Win Rate', 'Avg Trade']
            st.dataframe(symbol_df, use_container_width=True)
        else:
            st.info("No symbol performance data available")
        
        # Session performance
        st.subheader("🕐 Session Performance")
        session_metrics = report.get('session_metrics', {})
        if session_metrics:
            session_df = pd.DataFrame.from_dict(session_metrics, orient='index')
            st.dataframe(session_df, use_container_width=True)
        
        # Daily performance chart
        st.subheader("📅 Daily Performance")
        
        # Get actual MT5 account balance and equity
        mt5_balance = performance_metrics.get_mt5_account_balance()
        mt5_equity = performance_metrics.get_mt5_account_equity()
        
        if mt5_balance is not None:
            print(f"✅ MT5 Account Balance: ${mt5_balance:.2f}")
            print(f"✅ MT5 Account Equity: ${mt5_equity:.2f}")
            
            # Create a simple daily performance chart using actual MT5 data
            # Since we can't get historical balance data easily, we'll show current vs initial
            initial_balance = 10000  # Starting balance
            current_balance = mt5_balance
            current_equity = mt5_equity if mt5_equity is not None else mt5_balance
            
            # Create the chart similar to the screenshot
            fig = go.Figure()
            
            # Add current balance point (green)
            fig.add_trace(go.Scatter(
                x=[datetime.now().date()],
                y=[current_balance],
                mode='markers+text',
                name='Current Balance',
                line=dict(color='lightgreen', width=2),
                marker=dict(color='lightgreen', size=12),
                text=[f"${current_balance:.2f}"],
                textposition="top center"
            ))
            
            # Add current equity point (blue)
            fig.add_trace(go.Scatter(
                x=[datetime.now().date()],
                y=[current_equity],
                mode='markers+text',
                name='Current Equity',
                line=dict(color='lightblue', width=2),
                marker=dict(color='lightblue', size=12),
                text=[f"${current_equity:.2f}"],
                textposition="bottom center"
            ))
            
            # Add initial balance line (dashed)
            fig.add_hline(
                y=initial_balance,
                line_dash="dash",
                line_color="gray",
                annotation_text=f"Initial Balance: ${initial_balance:.2f}",
                annotation_position="left"
            )
            
            # Add profit target line (horizontal green line)
            profit_target = 11000  # You can adjust this
            fig.add_hline(
                y=profit_target,
                line_dash="solid",
                line_color="green",
                annotation_text="Profit Target",
                annotation_position="top right"
            )
            
            # Add max loss limit line (horizontal red line)
            max_loss_limit = 9000  # You can adjust this
            fig.add_hline(
                y=max_loss_limit,
                line_dash="solid",
                line_color="red",
                annotation_text="Max Loss Limit",
                annotation_position="bottom right"
            )
            
            # Update layout
            fig.update_layout(
                title="Account Performance (Live MT5 Data)",
                xaxis_title="Date",
                yaxis_title="Amount (USD)",
                hovermode='x unified',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            # Update y-axis to show proper range
            min_balance = min(current_balance, current_equity, max_loss_limit)
            max_balance = max(current_balance, current_equity, profit_target)
            fig.update_yaxes(range=[min_balance - 100, max_balance + 100])
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_pnl = current_balance - initial_balance
                st.metric("Total P&L", f"${total_pnl:.2f}")
            with col2:
                st.metric("Current Balance", f"${current_balance:.2f}")
            with col3:
                if mt5_equity is not None:
                    equity_diff = current_equity - current_balance
                    st.metric("Equity Difference", f"${equity_diff:.2f}")
                else:
                    st.metric("Current Equity", "N/A")
            with col4:
                profit_percentage = (total_pnl / initial_balance) * 100
                st.metric("Profit %", f"{profit_percentage:.2f}%")
            
            # Show account summary
            st.subheader("📊 Account Summary")
            summary_data = {
                "Metric": ["Initial Balance", "Current Balance", "Total P&L", "Profit %", "Current Equity"],
                "Value": [
                    f"${initial_balance:.2f}",
                    f"${current_balance:.2f}",
                    f"${total_pnl:.2f}",
                    f"{profit_percentage:.2f}%",
                    f"${current_equity:.2f}" if mt5_equity is not None else "N/A"
                ]
            }
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
            
        else:
            st.error("❌ Could not fetch MT5 account data")
            
        # Also show trade-based P&L for comparison
        if not trade_log.empty and 'profit' in trade_log.columns:
            st.subheader("📈 Trade-Based P&L (For Reference)")
            trade_pnl = trade_log['profit'].sum()
            st.info(f"Trade-based P&L: ${trade_pnl:.2f} (excludes commissions/swaps)")
            st.info(f"MT5 Account P&L: ${mt5_balance - 10000:.2f} (includes all fees)")
            st.info(f"Difference: ${(mt5_balance - 10000) - trade_pnl:.2f} (commissions/swaps)")
        
    except Exception as e:
        st.error(f"Error loading performance metrics: {e}")
        st.info("Make sure the bot has been running and has trade data available.")

def render_sidebar():
    """Render the sidebar with status and controls"""
    st.sidebar.title("🤖 D.E.V.I Control Panel")
    st.sidebar.markdown("---")
    
    # Bot Status with Heartbeat
    st.sidebar.subheader("🔋 Live Bot Status")
    
    # Add refresh button
    if st.sidebar.button("🔄 Refresh Status", key="refresh_status"):
        st.cache_data.clear()
        st.rerun()
    
    # Debug: Show heartbeat file info
    try:
        import os
        heartbeat_file = "bot_heartbeat.json"
        if os.path.exists(heartbeat_file):
            file_time = os.path.getmtime(heartbeat_file)
            file_time_str = datetime.fromtimestamp(file_time).strftime("%H:%M:%S")
            st.sidebar.caption(f"File modified: {file_time_str}")
    except:
        pass
    
    # Load heartbeat data
    heartbeat_data = load_bot_heartbeat()
    
    if heartbeat_data:
        # Bot Status
        status = heartbeat_data.get("bot_status", "unknown")
        last_heartbeat = heartbeat_data.get("last_heartbeat", "")
        symbols = heartbeat_data.get("current_symbols", [])
        loop_count = heartbeat_data.get("loop_count", 0)
        mt5_connected = heartbeat_data.get("mt5_connected", False)
        news_protection = heartbeat_data.get("news_protection_active", False)
        
        # Status indicator
        if status == "running":
            st.sidebar.success("✅ Bot is Running")
        elif status == "starting":
            st.sidebar.info("🔄 Bot is Starting")
        else:
            st.sidebar.warning("⚠️ Bot Status Unknown")
        
        # Bot details
        st.sidebar.write(f"**Symbols:** {', '.join(symbols)}")
        st.sidebar.write(f"**Loops:** {loop_count}")
        st.sidebar.write(f"**MT5:** {'✅ Connected' if mt5_connected else '❌ Disconnected'}")
        st.sidebar.write(f"**News Protection:** {'🛡️ Active' if news_protection else '✅ Inactive'}")
        
        # Last heartbeat
        if last_heartbeat:
            try:
                last_time = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                time_diff = datetime.now() - last_time.replace(tzinfo=None)
                minutes_ago = int(time_diff.total_seconds() // 60)
                
                # Show more detailed time information
                if minutes_ago < 1:
                    st.sidebar.success(f"🟢 Last update: Just now")
                elif minutes_ago < 5:
                    st.sidebar.success(f"🟢 Last update: {minutes_ago}m ago")
                elif minutes_ago < 15:
                    st.sidebar.info(f"🟡 Last update: {minutes_ago}m ago")
                elif minutes_ago < 30:
                    st.sidebar.warning(f"🟠 Last update: {minutes_ago}m ago")
                else:
                    st.sidebar.error(f"🔴 Last update: {minutes_ago}m ago")
                    
                # Show current time for reference
                current_time = datetime.now().strftime("%H:%M:%S")
                st.sidebar.caption(f"Current time: {current_time}")
                
            except Exception as e:
                st.sidebar.write(f"Last update: {last_heartbeat}")
                st.sidebar.caption(f"Error parsing time: {e}")
    else:
        st.sidebar.warning("⚠️ Bot Status Unknown")
        st.sidebar.write("No heartbeat data available")
    
    # Quick Performance Stats
    st.sidebar.subheader("📊 Quick Performance")
    
    # Load recent data with proper filtering
    ai_log = log_processor.load_ai_decision_log()
    trade_log = log_processor.load_trade_log()
    
    # Calculate 24h AI decisions properly
    if not ai_log.empty and 'timestamp' in ai_log.columns:
        now = datetime.now()
        yesterday = now - timedelta(hours=24)
        
        # Convert timestamp to datetime if it's string
        if ai_log['timestamp'].dtype == 'object':
            ai_log['timestamp'] = pd.to_datetime(ai_log['timestamp'])
        
        # Filter for last 24 hours
        recent_decisions = ai_log[ai_log['timestamp'] >= yesterday]
        st.sidebar.metric("24h AI Decisions", len(recent_decisions))
    else:
        st.sidebar.metric("24h AI Decisions", 0)
    
    # Use MT5 trade history for accurate 24h trade count
    mt5_trades = load_mt5_trade_history(days=1)  # Get last 24 hours
    if not mt5_trades.empty:
        # Filter for actual trades (BUY/SELL) in last 24 hours
        now = datetime.now()
        yesterday = now - timedelta(hours=24)
        recent_mt5_trades = mt5_trades[
            (mt5_trades['time'] >= yesterday) & 
            (mt5_trades['type'].isin(['BUY', 'SELL']))  # Filter for BUY/SELL trades
        ]
        
        # Count unique trades (not deals) - count only BUY entries
        unique_trades = recent_mt5_trades[recent_mt5_trades['type'] == 'BUY']
        trade_count = len(unique_trades)
        
        st.sidebar.metric("24h Trades", trade_count)
    elif not trade_log.empty:
        # Fallback to CSV trade log if MT5 data unavailable
        recent_trades = log_processor.get_recent_entries(trade_log, 24)
        st.sidebar.metric("24h Trades", len(recent_trades))
    else:
        st.sidebar.metric("24h Trades", 0)
        
    # Get MT5 balance
    try:
        if mt5.initialize():
            account_info = mt5.account_info()
            if account_info:
                current_balance = account_info.balance
                st.sidebar.metric("Current Balance", f"${current_balance:.2f}")
            mt5.shutdown()
    except:
        st.sidebar.metric("Current Balance", "N/A")
    
    # Calculate quick performance metrics
    if not trade_log.empty and 'profit' in trade_log.columns:
        win_rate = len(trade_log[trade_log['profit'] > 0]) / len(trade_log) * 100
        avg_trade = trade_log['profit'].mean()
        
        st.sidebar.metric("Win Rate", f"{win_rate:.1f}%")
        st.sidebar.metric("Avg Trade", f"${avg_trade:.2f}")
        
        # Recent performance (last 7 days)
        recent_trades_7d = log_processor.get_recent_entries(trade_log, 168)  # 7 days
        if not recent_trades_7d.empty and 'profit' in recent_trades_7d.columns:
            recent_profit = recent_trades_7d['profit'].sum()
            st.sidebar.metric("7d P&L", f"${recent_profit:.2f}")
    
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
    
    # Bot Status Monitoring Section
    st.subheader("🔋 Live Bot Status")
    
    heartbeat_data = load_bot_heartbeat()
    if heartbeat_data:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status = heartbeat_data.get("bot_status", "unknown")
            if status == "running":
                st.success("✅ Bot Running")
            elif status == "starting":
                st.info("🔄 Bot Starting")
            else:
                st.warning("⚠️ Bot Unknown")
        
        with col2:
            symbols = heartbeat_data.get("current_symbols", [])
            st.write(f"**Trading:** {', '.join(symbols)}")
        
        with col3:
            loop_count = heartbeat_data.get("loop_count", 0)
            st.write(f"**Loops:** {loop_count}")
        
        with col4:
            mt5_connected = heartbeat_data.get("mt5_connected", False)
            if mt5_connected:
                st.success("✅ MT5 Connected")
            else:
                st.error("❌ MT5 Disconnected")
        
        # News protection status
        news_protection = heartbeat_data.get("news_protection_active", False)
        if news_protection:
            st.warning("🛡️ News Protection Active - No Trading")
        else:
            st.success("✅ News Protection Inactive - Trading Allowed")
    
    st.markdown("---")
    
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