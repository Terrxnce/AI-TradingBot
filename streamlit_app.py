import streamlit as st
import pandas as pd
import json
import os
import MetaTrader5 as mt5
from datetime import datetime, timedelta, date

# === File paths ===
AI_LOG_FILE = "ai_decision_log.jsonl"

def load_ai_log():
    try:
        with open(AI_LOG_FILE, "r") as f:
            lines = f.readlines()
        return pd.DataFrame([json.loads(line) for line in lines])
    except Exception as e:
        st.error(f"Failed to load AI log: {e}")
        return pd.DataFrame()

# === Load Live Trade History from MT5 ===
def load_trade_history_from_mt5():
    if not mt5.initialize():
        st.error("❌ MT5 initialization failed. Please make sure MetaTrader 5 is running.")
        return pd.DataFrame()

    utc_from = datetime.now() - timedelta(days=7)
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

# === NEW: Trade Matching Function ===
def match_ai_decision_with_trade(ai_row, trade_df, tolerance_minutes=5):
    """Match AI decision with actual trade execution"""
    if trade_df.empty:
        return None
    
    time_window = pd.Timedelta(minutes=tolerance_minutes)
    symbol_trades = trade_df[trade_df['symbol'] == ai_row['symbol']]
    
    for _, trade in symbol_trades.iterrows():
        # Convert AI timestamp to UTC if it has timezone info
        ai_time = ai_row['timestamp']
        if hasattr(ai_time, 'tz_localize'):
            if ai_time.tz is None:
                ai_time = ai_time.tz_localize('UTC')
        
        # Convert trade time to UTC if needed
        trade_time = trade['time']
        if hasattr(trade_time, 'tz_localize'):
            if trade_time.tz is None:
                trade_time = trade_time.tz_localize('UTC')
        
        time_diff = abs(trade_time - ai_time)
        if time_diff <= time_window:
            return trade
    return None

# === UPDATED: Enhanced Table Display Functions ===
def format_table_data(df, trade_df=None):
    """Format the dataframe for clean display with trade matching and override handling"""
    display_df = df.copy()
    
    # Ensure all required columns exist with defaults
    required_columns = {
        'symbol': 'N/A',
        'timestamp': pd.NaT,
        'ai_decision': 'HOLD',  # Original AI decision
        'final_direction': None,  # Final executed direction
        'direction': 'HOLD',  # Fallback for legacy data
        'confidence': 0,
        'ai_confidence': None,  # New field for AI confidence
        'technical_score': None,  # New field for technical score
        'ema_trend': None,  # New field for EMA trend
        'sl': 'N/A',
        'tp': 'N/A',
        'reasoning': 'No reasoning provided',
        'ai_reasoning': None,  # New field for AI reasoning
        'risk_note': 'No risk note provided',
        'ai_risk_note': None,  # New field for AI risk note
        'executed': False,
        'ai_override': False,
        'ai_override_reason': None
    }
    
    for col, default_val in required_columns.items():
        if col not in display_df.columns:
            display_df[col] = default_val
    
    # === NEW: Use final_direction if available, else fallback to ai_decision ===
    display_df['direction'] = display_df.get('final_direction', display_df.get('ai_decision', display_df.get('direction', 'HOLD')))
    
    # === NEW: Ensure execution status is consistent ===
    display_df['executed'] = display_df.get('executed', False)
    
    # === NEW: Display override clearly ===
    display_df['ai_override'] = display_df.get('ai_override', False)
    
    # === NEW: Simplified column to display override source (UI tag) ===
    display_df['override_info'] = display_df.apply(
        lambda row: '🔄 Technical Override' if row.get('ai_override', False) else '✅ AI Decision',
        axis=1
    )
    
    # === Match with actual trades and update execution status ===
    if trade_df is not None and not trade_df.empty:
        for idx, row in display_df.iterrows():
            executed_trade = match_ai_decision_with_trade(row, trade_df)
            
            if executed_trade is not None:
                # Trade was actually executed
                display_df.loc[idx, 'executed'] = True
                display_df.loc[idx, 'actual_direction'] = executed_trade['type']
                
                # Check for AI override scenario
                ai_decision = str(row.get('ai_decision', '')).upper()
                trade_direction = executed_trade['type']
                
                # If AI said HOLD or had missing direction, but trade executed
                if ai_decision in ['HOLD', 'MISSING', 'N/A', ''] or pd.isna(row.get('ai_decision')):
                    display_df.loc[idx, 'ai_override'] = True
                    display_df.loc[idx, 'ai_override_reason'] = f"Technical override: AI suggested {ai_decision}, executed {trade_direction}"
                    display_df.loc[idx, 'direction'] = trade_direction  # Use actual trade direction
                    display_df.loc[idx, 'override_info'] = '🔄 Technical Override'
                    st.success(f"🔄 Override detected for {row['symbol']}: AI={ai_decision} → Executed={trade_direction}")
                
                # Store trade details for potential SL/TP extraction
                display_df.loc[idx, 'trade_price'] = executed_trade.get('price', 'N/A')
                display_df.loc[idx, 'trade_volume'] = executed_trade.get('volume', 'N/A')
                display_df.loc[idx, 'trade_profit'] = executed_trade.get('profit', 'N/A')
    
    # Clean up data formatting
    display_df['executed'] = display_df['executed'].fillna(False).astype(bool)
    
    # **Enhanced SL/TP formatting based on direction and execution**
    def format_sl_tp(row, field):
        """Format SL/TP based on trade direction and execution status"""
        value = row[field]
        direction = str(row['direction']).upper()
        executed = row['executed']
        
        # If value exists and is not N/A
        if pd.notna(value) and str(value).upper() not in ['N/A', 'NAN', '']:
            return str(value)
        
        # If direction is HOLD
        if direction == 'HOLD':
            return "Not Applicable (HOLD decision)"
        
        # If trade was executed but no SL/TP in AI log, could pull from trade system
        if executed and direction in ['BUY', 'SELL']:
            return f"Check trade system ({direction} executed)"
        
        # If direction is missing but executed is False
        if direction in ['N/A', 'MISSING'] and not executed:
            return "Not Applicable (No execution)"
        
        # If direction exists but no SL/TP
        if direction in ['BUY', 'SELL']:
            return f"Not Set ({direction} decision)"
        
        return "N/A"
    
    display_df['sl'] = display_df.apply(lambda row: format_sl_tp(row, 'sl'), axis=1)
    display_df['tp'] = display_df.apply(lambda row: format_sl_tp(row, 'tp'), axis=1)
    
    # **Enhanced Direction formatting**
    display_df['direction'] = display_df['direction'].fillna('HOLD').astype(str)
    display_df['direction'] = display_df['direction'].replace({'N/A': 'HOLD', 'nan': 'HOLD'})
    
    return display_df

def display_enhanced_ai_table(filtered_df, trade_df=None):
    """Enhanced table display for AI decisions with trade matching and override display"""
    
    if filtered_df.empty:
        st.info("No decisions match the current filters.")
        return
    
    # Format the data with trade matching
    display_df = format_table_data(filtered_df, trade_df)
    
    # === Additional Filters for Enhanced Table ===
    st.sidebar.markdown("### 📊 Enhanced Filters")
    
    # Execution Status Filter
    execution_options = ['All', 'Executed', 'Not Executed']
    selected_execution = st.sidebar.selectbox(
        "Execution Status",
        execution_options,
        help="Filter by whether the trade was executed (now checks actual trades)"
    )
    
    # AI Override Filter
    override_options = ['All', 'Override Cases', 'AI Decisions']
    selected_override = st.sidebar.selectbox(
        "Decision Type",
        override_options,
        help="Show cases where AI decisions were overridden by technical signals"
    )
    
    # Direction Filter
    directions = ['All'] + sorted([d for d in display_df['direction'].unique() if pd.notna(d)])
    selected_direction = st.sidebar.selectbox(
        "Trade Direction",
        directions,
        help="Filter by trade direction. Shows actual executed direction when available."
    )
    
    # Apply Additional Filters
    if selected_execution == 'Executed':
        display_df = display_df[display_df['executed'] == True]
    elif selected_execution == 'Not Executed':
        display_df = display_df[display_df['executed'] == False]
    
    if selected_override == 'Override Cases':
        display_df = display_df[display_df['ai_override'] == True]
    elif selected_override == 'AI Decisions':
        display_df = display_df[display_df['ai_override'] == False]
    
    if selected_direction != 'All':
        display_df = display_df[display_df['direction'] == selected_direction]
    
    # === Display Summary Stats with Enhanced Context ===
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Decisions", len(display_df))
    
    with col2:
        executed_count = len(display_df[display_df['executed'] == True])
        st.metric("Executed Trades", executed_count)
    
    with col3:
        hold_count = len(display_df[display_df['direction'] == 'HOLD'])
        st.metric("HOLD Decisions", hold_count)
    
    with col4:
        override_count = len(display_df[display_df['ai_override'] == True])
        if override_count > 0:
            st.metric("🔄 Technical Overrides", override_count)
        else:
            st.metric("Data Quality", "✅ Good")
    
    with col5:
        if len(display_df) > 0:
            # Use ai_confidence if available, else fall back to confidence
            confidence_col = 'ai_confidence' if 'ai_confidence' in display_df.columns and display_df['ai_confidence'].notna().any() else 'confidence'
            avg_confidence = pd.to_numeric(display_df[confidence_col], errors='coerce').mean()
            st.metric("Avg AI Confidence", f"{avg_confidence:.1f}" if not pd.isna(avg_confidence) else "N/A")
        else:
            st.metric("Avg AI Confidence", "N/A")
    
    st.markdown("---")
    
    # === Display Enhanced Table ===
    st.subheader(f"🤖 AI Trading Decisions ({len(display_df)} entries)")
    
    if display_df.empty:
        st.info("No decisions match the current filters.")
        return
    
    # Sort by timestamp (newest first)
    if 'timestamp' in display_df.columns:
        display_df = display_df.sort_values('timestamp', ascending=False)
    
    # === NEW: Updated Main Table Display Logic ===
    for idx, row in display_df.iterrows():
        with st.container():
            # Create header for each entry
            st.markdown(f"### {row['symbol']} – {pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['timestamp']) else 'Unknown Time'}")
            
            # === NEW: Display override information clearly ===
            if row.get('ai_override', False):
                # Show AI decision vs final decision for overrides
                ai_decision = row.get('ai_decision', 'HOLD')
                final_direction = row['direction']
                st.markdown(
                    f"🧠 **AI Decision:** {ai_decision} → **Final Decision:** {final_direction} {row['override_info']}"
                )
            else:
                # Show normal AI decision
                direction = row['direction']
                emoji = "🟢" if direction == "BUY" else "🔴" if direction == "SELL" else "🟡"
                st.markdown(f"{emoji} **{direction}** – {row['override_info']}")
            
            # === NEW: Display key metrics in organized format ===
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.text(f"SL: {row.get('sl', 'N/A')}")
                st.text(f"TP: {row.get('tp', 'N/A')}")
                st.text(f"Executed: {'✅ Yes' if row['executed'] else '❌ No'}")
            
            with col2:
                technical_score = row.get('technical_score', 'N/A')
                ema_trend = row.get('ema_trend', 'N/A')
                st.text(f"Technical Score: {technical_score}")
                st.text(f"EMA Trend: {ema_trend}")
            
            with col3:
                ai_confidence = row.get('ai_confidence', row.get('confidence', 'N/A'))
                st.text(f"AI Confidence: {ai_confidence}/10")
                if 'trade_profit' in row and pd.notna(row['trade_profit']):
                    profit_color = "🟢" if float(row['trade_profit']) > 0 else "🔴"
                    st.text(f"P&L: {profit_color} {row['trade_profit']}")
            
            # === NEW: Expandable sections for detailed information ===
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("📖 AI Reasoning"):
                    reasoning = row.get('ai_reasoning', row.get('reasoning', 'No reasoning provided'))
                    st.write(str(reasoning))
            
            with col2:
                with st.expander("⚠️ Risk Assessment"):
                    risk_note = row.get('ai_risk_note', row.get('risk_note', 'No risk assessment provided'))
                    st.write(str(risk_note))
            
            # Show override details if applicable
            if row.get('ai_override', False) and pd.notna(row.get('ai_override_reason')):
                with st.expander("🔄 Override Details"):
                    st.warning(str(row['ai_override_reason']))
                    if 'trade_price' in row and pd.notna(row['trade_price']):
                        st.write("**Executed Trade Details:**")
                        st.write(f"• Price: {row['trade_price']}")
                        st.write(f"• Volume: {row['trade_volume']}")
                        st.write(f"• Profit/Loss: {row['trade_profit']}")
            
            st.markdown("---")
    
    # === Export Options ===
    st.subheader("📥 Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # CSV Export
        csv_data = display_df.to_csv(index=False)
        st.download_button(
            label="📊 Download as CSV",
            data=csv_data,
            file_name=f"ai_trading_decisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Download filtered data with all columns as CSV file"
        )
    
    with col2:
        # JSON Export
        json_data = display_df.to_json(orient='records', date_format='iso', indent=2)
        st.download_button(
            label="📋 Download as JSON",
            data=json_data,
            file_name=f"ai_trading_decisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            help="Download filtered data with all columns as JSON file"
        )

# === Pagination (keeping your original function) ===
def paginate(df, page_size):
    total_pages = max((len(df) - 1) // page_size + 1, 1)
    page = st.number_input("Page", 1, total_pages, step=1)
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total_pages

# === Streamlit Setup ===
st.set_page_config(page_title="D.E.V.I. Dashboard", layout="wide")
st.title("🧠 D.E.V.I. Trading Log Dashboard")

# === MT5 Trade History ===
st.header("📊 MT5 Trade History")
trade_df = load_trade_history_from_mt5()

if not trade_df.empty:
    st.dataframe(trade_df)
    st.download_button(
        label="📥 Download Trade History",
        data=trade_df.to_csv(index=False).encode("utf-8"),
        file_name="devi_trade_history.csv",
        mime="text/csv"
    )
    st.success(f"✅ Loaded {len(trade_df)} trades for cross-referencing with AI decisions")
else:
    st.warning("No recent trade history found in the past 7 days.")

# === AI Reasoning Log ===
st.markdown("---")
st.header("🧠 AI Reasoning Log")

# Load and process AI log data
log_df = load_ai_log()

if log_df.empty:
    st.warning("AI decision log not found yet.")
    st.stop()

# **Proper timestamp handling with mixed formats**
if "timestamp" in log_df.columns:
    
    # Handle mixed timestamp formats more robustly
    def parse_timestamp(ts):
        try:
            # First try with microseconds
            return pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
        except:
            try:
                # Then try without microseconds
                return pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S")
            except:
                # Finally, let pandas infer the format
                return pd.to_datetime(ts, errors="coerce")
    
    # Apply the parsing function
    log_df["timestamp"] = log_df["timestamp"].apply(parse_timestamp)
    
    # Remove rows with invalid timestamps
    invalid_timestamps = log_df["timestamp"].isna().sum()
    if invalid_timestamps > 0:
        st.warning(f"⚠️ Found {invalid_timestamps} invalid timestamps, removing them.")
    
    log_df = log_df.dropna(subset=["timestamp"])
    
    if log_df.empty:
        st.error("❌ No valid timestamps found in AI log.")
        st.stop()
        
    # Convert to UTC for consistency
    log_df["timestamp"] = log_df["timestamp"].dt.tz_localize("UTC", nonexistent="shift_forward", ambiguous="infer")
    
else:
    st.error("❌ 'timestamp' column missing in AI log.")
    st.stop()

# **Debug timestamp information**
st.sidebar.markdown("### 📅 Date Info")
st.sidebar.write(f"**Total entries:** {len(log_df)}")
st.sidebar.write(f"**Date range in data:**")
st.sidebar.write(f"From: {log_df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.write(f"To: {log_df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')}")

# Show entries per date for debugging
date_counts = log_df['timestamp'].dt.date.value_counts().sort_index()
st.sidebar.write("**Entries per date:**")
for date, count in date_counts.items():
    st.sidebar.write(f"  {date}: {count} entries")

# === Sidebar Filters ===
st.sidebar.header("🔍 Basic Filters")

# Symbol filter
symbols = sorted(log_df["symbol"].dropna().unique())
selected_symbols = st.sidebar.multiselect("Symbol", options=symbols, default=symbols)

# **Improved date range handling**
# Convert to local timezone for date picker (removes timezone info for date comparison)
log_df_local = log_df.copy()
log_df_local["timestamp_local"] = log_df_local["timestamp"].dt.tz_convert(None)

min_date = log_df_local["timestamp_local"].min().date()
max_date = log_df_local["timestamp_local"].max().date()

# **More flexible date range picker**
st.sidebar.write(f"Available date range: {min_date} to {max_date}")

# Force max_date to be at least today if data exists for today
today = date.today()
if max_date < today and len(log_df_local[log_df_local["timestamp_local"].dt.date == today]) > 0:
    max_date = today

date_range = st.sidebar.date_input(
    "Date Range", 
    value=(min_date, max_date), 
    min_value=min_date, 
    max_value=max_date,
    help=f"Select dates between {min_date} and {max_date}"
)

# **Handle both single date and date range**
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
elif isinstance(date_range, tuple) and len(date_range) == 1:
    start_date = end_date = date_range[0]
else:
    start_date = end_date = date_range

# **Convert confidence to numeric once**
log_df["confidence"] = pd.to_numeric(log_df["confidence"], errors="coerce")
conf_values = log_df["confidence"].dropna()

if not conf_values.empty:
    min_conf = int(conf_values.min())
    max_conf = int(conf_values.max())
    
    st.sidebar.write(f"**Confidence range:** {min_conf} to {max_conf}")
    
    if min_conf < max_conf:
        conf_filter = st.sidebar.slider("Confidence (min)", min_conf, max_conf, min_conf)
    else:
        st.sidebar.markdown(f"Only one confidence level found: **{min_conf}**")
        conf_filter = min_conf
else:
    st.sidebar.warning("No valid confidence values found")
    conf_filter = 0

# Search box
search_term = st.sidebar.text_input("Search (reasoning or risk note)").lower()

# === Apply Basic Filters ===
# **Use local timezone for date filtering**
filtered_df = log_df[
    (log_df["symbol"].isin(selected_symbols)) &
    (log_df["timestamp"].dt.tz_convert(None).dt.date >= start_date) &
    (log_df["timestamp"].dt.tz_convert(None).dt.date <= end_date)
]

# **Use confidence column directly for filtering**
if conf_filter and not conf_values.empty:
    filtered_df = filtered_df[filtered_df["confidence"] >= conf_filter]

if search_term:
    filtered_df = filtered_df[
        filtered_df["reasoning"].str.lower().str.contains(search_term, na=False) |
        filtered_df["risk_note"].str.lower().str.contains(search_term, na=False)
    ]

# === Display Mode Selection ===
st.subheader("📋 Display Mode")
display_mode = st.radio(
    "Choose display mode:",
    ["Enhanced Table View", "Classic Table View"],
    help="Enhanced view shows detailed, investor-ready format with trade matching. Classic view shows simple paginated table."
)

if display_mode == "Enhanced Table View":
    # === Enhanced Table Display with Trade Matching ===
    display_enhanced_ai_table(filtered_df, trade_df)
    
else:
    # === Classic Display (Your Original) ===
    st.subheader(f"Filtered AI Log: {len(filtered_df)} entries")
    
    # **Show current filter status**
    if len(filtered_df) < len(log_df):
        st.info(f"Showing {len(filtered_df)} out of {len(log_df)} total entries")

    paged_df, total_pages = paginate(filtered_df, page_size=10)
    st.dataframe(paged_df)

    if total_pages > 1:
        st.caption(f"Page size: 10 rows | Total pages: {total_pages}")

    st.download_button(
        label="📥 Download AI Log as CSV",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="ai_reasoning_log.csv",
        mime="text/csv"
    )

st.markdown("---")
st.caption("Built by Divine Earnings | Phase 1.7 – Enhanced Override Display | Now with Clear Technical Overrides 🔄")