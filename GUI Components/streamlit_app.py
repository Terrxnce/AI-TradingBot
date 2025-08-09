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

# Try to import MetaTrader5, create fallback if not available
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    print("⚠️ MetaTrader5 not available. Creating mock for testing.")
    MT5_AVAILABLE = False
    
    # Create a mock MT5 class for testing
    class mt5:
        @staticmethod
        def initialize():
            return True
        
        @staticmethod
        def shutdown():
            pass
        
        @staticmethod
        def positions_get():
            return []

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))  # Add root directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Bot Core'))  # Add Bot Core directory

# Import multi-account system
try:
    from account_manager import initialize_account_system, get_account_manager, get_data_source
    from account_config_manager import get_config_manager
    
    # Initialize the multi-account system
    account_manager, data_source = initialize_account_system()
    config_manager = get_config_manager()
    MULTI_ACCOUNT_ENABLED = True
except Exception as e:
    print("⚠️ Multi-account system not available:", str(e))
    MULTI_ACCOUNT_ENABLED = False
    account_manager = None
    data_source = None
    config_manager = None

from utils.config_manager import config_manager as legacy_config_manager
from utils.log_utils import LogProcessor

# Initialize session state for account management
if 'account_system_initialized' not in st.session_state:
    st.session_state.account_system_initialized = True
    st.session_state.current_account = None
    st.session_state.log_processor = None

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

# === Timeout Prevention Configuration ===
# Set session timeout to prevent disconnections
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = time.time()

# Update activity timestamp on each interaction
st.session_state.last_activity = time.time()

# Auto-refresh every 30 seconds to keep connection alive
if 'auto_refresh_counter' not in st.session_state:
    st.session_state.auto_refresh_counter = 0

st.session_state.auto_refresh_counter += 1

# Add a hidden auto-refresh mechanism
if st.session_state.auto_refresh_counter % 30 == 0:  # Every 30 seconds
    st.rerun()

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
            # Secure team password for Cloudflare Tunnel access
            if password == "devipass2025":  # Secure password for team access
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

# === Account Selection ===
def handle_account_selection():
    """Handle account selection and switching"""
    if not MULTI_ACCOUNT_ENABLED:
        st.sidebar.warning("⚠️ Multi-account system not available. Using legacy mode.")
        return True
        
    if 'current_account' not in st.session_state:
        st.session_state.current_account = None
    
    # Get available accounts
    available_accounts = account_manager.get_available_accounts()
    
    if not available_accounts:
        st.error("❌ No accounts configured. Please set up accounts in accounts_config.json")
        return False
    
    # Account selection in sidebar
    with st.sidebar:
        st.markdown("### 🏦 Account Selection")
        
        # Show current account info
        current_account = account_manager.get_current_account_id()
        if current_account:
            current_config = account_manager.get_current_account_config()
            st.success(f"**Active:** {current_config.account_name} ({current_account})")
            
            # Show MT5 connection status
            account_info = data_source.get_mt5_account_info()
            if account_info:
                st.metric("Balance", f"${account_info['balance']:,.2f}")
                st.metric("Equity", f"${account_info['equity']:,.2f}")
            else:
                st.warning("⚠️ MT5 not connected")
        
        # Account switcher
        account_options = {}
        for acc_id in available_accounts:
            config = account_manager.accounts.get(acc_id)
            if config:
                account_options[f"{config.account_name} ({acc_id})"] = acc_id
        
        selected_display = st.selectbox(
            "Select Account:",
            options=list(account_options.keys()),
            index=list(account_options.values()).index(current_account) if current_account in account_options.values() else 0
        )
        
        selected_account_id = account_options[selected_display]
        
        # Switch account if different
        if selected_account_id != current_account:
            with st.spinner(f"Switching to account {selected_account_id}..."):
                if account_manager.switch_account(selected_account_id):
                    # Update config manager
                    config_manager.set_active_account(selected_account_id)
                    
                    # Update log processor with new account paths
                    ai_log_path = data_source.get_ai_decision_log_path()
                    trade_log_path = data_source.get_trade_log_path()
                    st.session_state.log_processor = LogProcessor(
                        ai_log_file=ai_log_path, 
                        trade_log_file=trade_log_path
                    )
                    
                    st.session_state.current_account = selected_account_id
                    st.success(f"✅ Switched to {selected_account_id}")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to switch to account {selected_account_id}")
        
        # Account management buttons
        if st.button("🔄 Refresh Connection"):
            if current_account:
                account_manager.switch_account(current_account)
                st.rerun()
        
        # Configuration section
        with st.expander("⚙️ Account Settings"):
            if current_account:
                current_config = config_manager.get_config()
                st.json(current_config)
    
    return True

# === Utility Functions ===
@st.cache_data(ttl=10)  # Cache for 10 seconds to reduce stale data
def load_mt5_positions():
    """Load current MT5 positions for active account"""
    try:
        if MULTI_ACCOUNT_ENABLED:
            # Check if we have an active account session
            current_account = account_manager.get_current_account_id()
            if not current_account:
                st.warning("⚠️ No active account session")
                return pd.DataFrame()
            
            # Use account-aware MT5 connection
            account_info = data_source.get_mt5_account_info()
            if not account_info:
                st.warning("⚠️ Failed to get account info - MT5 not connected")
                return pd.DataFrame()
        else:
            # Legacy MT5 connection
            if not mt5.initialize():
                st.warning("⚠️ Failed to initialize MT5 connection")
                return pd.DataFrame()
        
        # Get positions through MT5
        positions = mt5.positions_get()
        
        # Shutdown MT5 if in legacy mode
        if not MULTI_ACCOUNT_ENABLED:
            mt5.shutdown()
        
        if positions is None:
            st.warning("⚠️ MT5 returned None for positions")
            return pd.DataFrame()
        
        if not positions:
            return pd.DataFrame()
        
        positions_df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
        return positions_df[["symbol", "type", "volume", "price_open", "profit", "time"]]
    except Exception as e:
        st.error(f"❌ Error loading MT5 positions: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=5)  # Cache for 5 seconds to get more frequent updates
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
        
        # Disable RSI and Fibonacci toggles with tooltips
        use_rsi = st.checkbox(
            "Use RSI Indicator",
            value=False,
            disabled=True,
            help="🧪 Coming Soon – Currently in Testing"
        )
        
        use_fib = st.checkbox(
            "Use Fibonacci",
            value=False,
            disabled=True,
            help="🧪 Coming Soon – Currently in Testing"
        )
        
        # Add visual indicator
        st.caption("🧪 RSI & Fibonacci: Testing Phase")
        
        # Post-Session Trading Control
        st.subheader("🕐 Post-Session Trading Control")
        post_session_enabled = st.checkbox(
            "Enable Post-Session Trading",
            value=config.get("post_session_enabled", True),
            help="Enable enhanced post-session trading (17:00-19:00 UTC) with 0.75x lot sizing"
        )
        
        if post_session_enabled:
            st.info("🕐 Post-Session Active: Enhanced trading with 0.75x lot sizing, 8.0 score threshold, and 0.75%/1.5% profit targets")
        else:
            st.warning("⏸️ Post-Session Disabled: Only regular session trading (14:00-16:00 UTC) will be active")
        
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
                "post_session_enabled": post_session_enabled,
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
        
        # Add refresh button for positions
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh Positions", key="refresh_positions"):
                st.cache_data.clear()
                st.rerun()
        
        positions = load_mt5_positions()
        
        # Show last update time
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        
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
    """Render AI decisions section"""
    st.header("🤖 AI Decision Log")
    
    # Load AI decision log
    ai_log = log_processor.load_ai_decision_log()
    
    if ai_log.empty:
        st.info("No AI decisions found. Start the bot to see AI analysis.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Symbol filter
        symbols = ['All'] + sorted(ai_log['symbol'].unique().tolist())
        selected_symbol = st.selectbox("Symbol", symbols, key="ai_symbol_filter")
    
    with col2:
        # Decision filter
        decisions = ['All'] + sorted(ai_log['ai_decision'].unique().tolist())
        selected_decision = st.selectbox("Decision", decisions, key="ai_decision_filter")
    
    with col3:
        # Date range filter
        if 'timestamp' in ai_log.columns:
            ai_log['timestamp'] = pd.to_datetime(ai_log['timestamp'])
            min_date = ai_log['timestamp'].min().date()
            max_date = ai_log['timestamp'].max().date()
            date_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="ai_date_filter"
            )
    
    # Apply filters
    filtered_log = ai_log.copy()
    
    if selected_symbol != 'All':
        filtered_log = filtered_log[filtered_log['symbol'] == selected_symbol]
    
    if selected_decision != 'All':
        filtered_log = filtered_log[filtered_log['ai_decision'] == selected_decision]
    
    if len(date_range) == 2 and 'timestamp' in filtered_log.columns:
        start_date, end_date = date_range
        if start_date and end_date:
            filtered_log = filtered_log[
                (filtered_log['timestamp'].dt.date >= start_date) &
                (filtered_log['timestamp'].dt.date <= end_date)
            ]
    
    # Display filtered data
    if filtered_log.empty:
        st.warning("No AI decisions found with current filters")
        return
    
    # Show summary stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_decisions = len(filtered_log)
        st.metric("Total Decisions", total_decisions)
    
    with col2:
        executed_trades = len(filtered_log[filtered_log['executed'] == True])
        execution_rate = (executed_trades / total_decisions * 100) if total_decisions > 0 else 0
        st.metric("Execution Rate", f"{execution_rate:.1f}%")
    
    with col3:
        if 'ai_confidence' in filtered_log.columns:
            avg_confidence = filtered_log['ai_confidence'].apply(
                lambda x: float(x) if str(x).replace('.', '').isdigit() else 0
            ).mean()
            st.metric("Avg Confidence", f"{avg_confidence:.1f}")
        else:
            st.metric("Avg Confidence", "N/A")
    
    with col4:
        if 'technical_score' in filtered_log.columns:
            avg_score = filtered_log['technical_score'].apply(
                lambda x: float(x) if str(x).replace('.', '').isdigit() else 0
            ).mean()
            st.metric("Avg Tech Score", f"{avg_score:.1f}")
        else:
            st.metric("Avg Tech Score", "N/A")
    
    # Decision distribution pie chart
    st.subheader("📊 Decision Distribution")
    
    if 'ai_decision' in filtered_log.columns:
        decision_counts = filtered_log['ai_decision'].value_counts()
        
        if not decision_counts.empty:
            # Create pie chart
            fig = go.Figure(data=[go.Pie(
                labels=decision_counts.index,
                values=decision_counts.values,
                hole=0.3,
                marker_colors=['#00ff88', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57']
            )])
            
            fig.update_layout(
                title="AI Decision Distribution",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                ),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show decision breakdown
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📈 Decision Breakdown")
                for decision, count in decision_counts.items():
                    percentage = (count / len(filtered_log)) * 100
                    st.metric(f"{decision}", f"{count} ({percentage:.1f}%)")
            
            with col2:
                st.subheader("🎯 Execution Stats")
                if 'executed' in filtered_log.columns:
                    executed_count = filtered_log['executed'].sum()
                    total_decisions = len(filtered_log)
                    execution_rate = (executed_count / total_decisions) * 100 if total_decisions > 0 else 0
                    st.metric("Executed Trades", f"{executed_count} ({execution_rate:.1f}%)")
                    
                    # Show override stats if available
                    if 'ai_override' in filtered_log.columns:
                        override_count = filtered_log['ai_override'].sum()
                        override_rate = (override_count / total_decisions) * 100 if total_decisions > 0 else 0
                        st.metric("AI Overrides", f"{override_count} ({override_rate:.1f}%)")
        else:
            st.info("No decision data available for chart")
    else:
        st.info("No 'ai_decision' column found in data")
    
    # Display detailed log
    st.subheader("📋 AI Decision Details")
    
    # Select columns to display (only include columns that exist)
    base_columns = ['timestamp', 'symbol', 'ai_decision', 'ai_confidence', 'technical_score', 'ema_trend', 'final_direction', 'executed']
    optional_columns = ['ai_reasoning', 'ai_risk_note', 'ai_override', 'override_reason', 'execution_source']
    
    # Only include columns that actually exist in the data
    display_columns = []
    for col in base_columns + optional_columns:
        if col in filtered_log.columns:
            display_columns.append(col)
    
    # Ensure we have at least some columns to display
    if not display_columns:
        display_columns = list(filtered_log.columns)
    
    # Format timestamp for display
    display_log = filtered_log[display_columns].copy()
    if 'timestamp' in display_log.columns:
        try:
            display_log['timestamp'] = pd.to_datetime(display_log['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            # Sort by timestamp (newest first)
            display_log = display_log.sort_values('timestamp', ascending=False)
        except Exception as e:
            st.warning(f"Could not format timestamp column: {e}")
            # If timestamp formatting fails, just sort by index
            display_log = display_log.sort_index(ascending=False)
    else:
        # If no timestamp column, sort by index
        display_log = display_log.sort_index(ascending=False)
    
    st.dataframe(display_log, use_container_width=True)
    
    # Download button
    csv = filtered_log.to_csv(index=False)
    st.download_button(
        label="📥 Download AI Decisions (CSV)",
        data=csv,
        file_name=f"ai_decisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

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
    try:
        heartbeat_data = load_bot_heartbeat()
    except Exception as e:
        st.sidebar.error("❌ Failed to load heartbeat")
        st.sidebar.caption(f"Heartbeat Error: {str(e)[:50]}...")
        heartbeat_data = None
    
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
    try:
        ai_log = log_processor.load_ai_decision_log()
    except Exception as e:
        st.sidebar.error("❌ Failed to load AI log")
        ai_log = pd.DataFrame()
        
    try:
        trade_log = log_processor.load_trade_log()
    except Exception as e:
        st.sidebar.error("❌ Failed to load trade log")
        trade_log = pd.DataFrame()
    
    # Calculate 24h AI decisions properly
    try:
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
    except Exception as e:
        st.sidebar.metric("24h AI Decisions", "Error")
        st.sidebar.caption(f"AI Log Error: {str(e)[:50]}...")
    
    # Calculate 24h trades from AI decision log (more accurate than MT5 history)
    try:
        if not ai_log.empty and 'timestamp' in ai_log.columns:
            now = datetime.now()
            yesterday = now - timedelta(hours=24)
            
            # Convert timestamp to datetime if it's string
            if ai_log['timestamp'].dtype == 'object':
                ai_log['timestamp'] = pd.to_datetime(ai_log['timestamp'])
            
            # Filter for last 24 hours and executed trades
            recent_trades = ai_log[
                (ai_log['timestamp'] >= yesterday) & 
                (ai_log['executed'] == True)
            ]
            st.sidebar.metric("24h Trades", len(recent_trades))
        else:
            st.sidebar.metric("24h Trades", 0)
    except Exception as e:
        st.sidebar.metric("24h Trades", "Error")
        st.sidebar.caption(f"Trade Log Error: {str(e)[:50]}...")
        
    # Get MT5 balance
    try:
        if mt5.initialize():
            account_info = mt5.account_info()
            if account_info:
                current_balance = account_info.balance
                st.sidebar.metric("Current Balance", f"${current_balance:.2f}")
            else:
                st.sidebar.metric("Current Balance", "N/A")
            mt5.shutdown()
        else:
            st.sidebar.metric("Current Balance", "MT5 Not Connected")
    except Exception as e:
        st.sidebar.metric("Current Balance", "Error")
        st.sidebar.caption(f"MT5 Error: {str(e)[:50]}...")
    
    # Calculate quick performance metrics
    try:
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
    except Exception as e:
        st.sidebar.metric("Performance", "Error")
        st.sidebar.caption(f"Metrics Error: {str(e)[:50]}...")
    
    # Config backups
    st.sidebar.subheader("💾 Backups")
    try:
        backups = config_manager.get_backup_list()
        if backups:
            st.sidebar.write(f"Available: {len(backups)} backups")
            if st.sidebar.button("📂 View Backups"):
                st.session_state.show_backups = True
        else:
            st.sidebar.write("No backups available")
    except Exception as e:
        st.sidebar.write("Backups: Error")
        st.sidebar.caption(f"Backup Error: {str(e)[:50]}...")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Version:** Internal Beta v1.0")
    st.sidebar.markdown("**Team:** Enoch, Roni, Terry")

def main():
    """Main application function"""
    # Check authentication
    if not check_password():
        return
    
    # Handle account selection
    if not handle_account_selection():
        return
    
    # Initialize log processor if not already done
    if st.session_state.log_processor is None:
        if MULTI_ACCOUNT_ENABLED:
            current_account = account_manager.get_current_account_id()
            if current_account:
                ai_log_path = data_source.get_ai_decision_log_path()
                trade_log_path = data_source.get_trade_log_path()
                st.session_state.log_processor = LogProcessor(
                    ai_log_file=ai_log_path, 
                    trade_log_file=trade_log_path
                )
        else:
            # Fallback to legacy paths
            script_dir = os.path.dirname(__file__)
            ai_log_path = os.path.join(script_dir, "..", "Bot Core", "ai_decision_log.jsonl")
            trade_log_path = os.path.join(script_dir, "..", "Bot Core", "logs", "trade_log.csv")
            st.session_state.log_processor = LogProcessor(
                ai_log_file=ai_log_path, 
                trade_log_file=trade_log_path
            )
    
    # Render sidebar
    render_sidebar()
    
    # Main title with account info
    if MULTI_ACCOUNT_ENABLED:
        current_account = account_manager.get_current_account_id()
        current_config = account_manager.get_current_account_config()
        account_display = " - " + str(current_config.account_name) + " (" + str(current_account) + ")" if current_config else ""
    else:
        account_display = " - Legacy Mode"
    
    st.title("🤖 D.E.V.I Trading Bot Dashboard" + account_display)
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
    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Configuration", "📊 Trade Logs", "🤖 AI Decisions", "🧠 D.E.V.I Analytics"])
    
    with tab1:
        render_config_editor()
    
    with tab2:
        render_trade_logs()
    
    with tab3:
        render_ai_decisions()
    
    with tab4:
        # Import and render the comprehensive analytics dashboard
        try:
            from analytics_dashboard import AnalyticsDashboard
            # Clear cache for real-time updates
            st.cache_data.clear()
            dashboard = AnalyticsDashboard()
            dashboard.render_dashboard()
        except ImportError as e:
            st.error(f"Could not load analytics dashboard: {e}")
            st.info("Please ensure analytics_dashboard.py is in the GUI Components directory")
        except Exception as e:
            st.error(f"Analytics dashboard error: {e}")
            st.info("The analytics dashboard encountered an error. Check the logs for details.")
    
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