import streamlit as st
import pandas as pd
import json
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

# === NEW: Calculate Top-Level Performance Metrics ===
def calculate_performance_metrics(df, trade_df=None):
    """Calculate key performance metrics for the dashboard header"""
    metrics = {
        'total_decisions': len(df),
        'total_executed': 0,
        'win_rate': 0.0,
        'avg_tech_score': 0.0,
        'avg_ai_confidence': 0.0,
        'skipped_blocked': 0,
        'technical_overrides': 0
    }
    
    if df.empty:
        return metrics
    
    # Basic counts
    metrics['total_executed'] = len(df[df.get('executed', False) == True])
    metrics['skipped_blocked'] = len(df[(df.get('executed', False) == False) & (df.get('final_direction', df.get('direction', 'HOLD')) != 'HOLD')])
    metrics['technical_overrides'] = len(df[df.get('ai_override', False) == True])
    
    # Average scores
    tech_scores = pd.to_numeric(df.get('technical_score', []), errors='coerce').dropna()
    if not tech_scores.empty:
        metrics['avg_tech_score'] = tech_scores.mean()
    
    # AI Confidence (check both new and legacy fields)
    ai_conf = pd.to_numeric(df.get('ai_confidence', []), errors='coerce').dropna()
    if ai_conf.empty:
        ai_conf = pd.to_numeric(df.get('confidence', []), errors='coerce').dropna()
    if not ai_conf.empty:
        metrics['avg_ai_confidence'] = ai_conf.mean()
    
    # Win rate calculation (if trade_df is available)
    if trade_df is not None and not trade_df.empty and metrics['total_executed'] > 0:
        profitable_trades = len(trade_df[trade_df['profit'] > 0])
        metrics['win_rate'] = (profitable_trades / len(trade_df)) * 100 if len(trade_df) > 0 else 0
    
    return metrics

# === NEW: Enhanced AI Decision Display Logic ===
def format_ai_decision_display(ai_decision, final_direction, ai_override=False):
    """Format AI decision display with proper handling of missing/nan values"""
    
    # Handle AI Decision
    if pd.isna(ai_decision) or str(ai_decision).lower() in ['nan', 'none', '']:
        ai_decision_text = "Not Available"
    else:
        ai_decision_text = str(ai_decision).upper()
    
    # Handle Final Decision
    if pd.isna(final_direction) or str(final_direction).lower() in ['nan', 'none', '']:
        final_direction_text = "HOLD"
    else:
        final_direction_text = str(final_direction).upper()
    
    # Format display based on override status
    if ai_override:
        return f"AI Decision: {ai_decision_text} → Final Decision: {final_direction_text} (Technical Override)"
    else:
        if ai_decision_text == "Not Available":
            return f"AI Decision: {ai_decision_text} → Final Decision: {final_direction_text}"
        else:
            return f"Final Decision: {final_direction_text}" if ai_decision_text == final_direction_text else f"AI Decision: {ai_decision_text} → Final Decision: {final_direction_text}"

# === UPDATED: Enhanced Table Display Functions ===
def format_table_data(df, trade_df=None):
    """Format the dataframe for clean display with trade matching and override handling"""
    display_df = df.copy()
    
    # Ensure all required columns exist with defaults and N/A values
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

        # === NEW: Apply N/A fallbacks for all None/NaN values ===
    string_columns = ['symbol', 'ema_trend', 'sl', 'tp', 'reasoning', 'ai_reasoning', 'risk_note', 'ai_risk_note', 'ai_override_reason']
    for col in string_columns:
        if col in display_df.columns:
            display_df[col] = display_df[col].fillna('N/A')
            display_df[col] = display_df[col].replace(['', 'nan', 'None'], 'N/A')
    
    
    # === NEW: Use final_direction if available, else fallback to ai_decision ===
    display_df['direction'] = display_df.get('final_direction', display_df.get('ai_decision', display_df.get('direction', 'HOLD')))
    
    # === NEW: Ensure execution status is consistent ===
    display_df['executed'] = display_df.get('executed', False)
    
    # === NEW: Display override clearly ===
    display_df['ai_override'] = display_df.get('ai_override', False)
    
        # === NEW: Enhanced AI Decision Display ===
    display_df['decision_display'] = display_df.apply(
        lambda row: format_ai_decision_display(
            row.get('ai_decision'),
            row.get('final_direction', row.get('direction')),
            row.get('ai_override', False)
        ),
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
                    display_df.loc[idx, 'direction'] = trade_direction
                    # Update decision display for override
                    display_df.loc[idx, 'decision_display'] = format_ai_decision_display(
                        ai_decision, trade_direction, True
                    )
                   
                # Store trade details
                display_df.loc[idx, 'trade_price'] = executed_trade.get('price', 'N/A')
                display_df.loc[idx, 'trade_volume'] = executed_trade.get('volume', 'N/A')
                display_df.loc[idx, 'trade_profit'] = executed_trade.get('profit', 'N/A')
    
    # Clean up data formatting
    display_df['executed'] = display_df['executed'].fillna(False).astype(bool)
    
    # **Enhanced SL/TP formatting with N/a fallbacks for None values**
    def format_sl_tp(row, field):
        """Format SL/TP based on trade direction and execution status"""
        value = row[field]
        direction = str(row['direction']).upper()
        executed = row['executed']
        
        # If value exists and is not N/A
        if pd.notna(value) and str(value).upper() not in ['N/A', 'NAN', 'NONE']:
            return str(value)
        
        # If direction is HOLD
        if direction == 'HOLD':
            return "N/A"
        
        # If trade was executed but no SL/TP in AI log
        if executed and direction in ['BUY', 'SELL']:
            return "N/A"

        
        return "N/A"
    
    display_df['sl'] = display_df.apply(lambda row: format_sl_tp(row, 'sl'), axis=1)
    display_df['tp'] = display_df.apply(lambda row: format_sl_tp(row, 'tp'), axis=1)
    
    # **Enhanced Direction formatting**
    display_df['direction'] = display_df['direction'].fillna('HOLD').astype(str)
    display_df['direction'] = display_df['direction'].replace({'N/A': 'HOLD', 'nan': 'HOLD', 'None': 'HOLD'})
    
    return display_df
# === NEW: Trade Performance Metrics Header Component ===
def display_performance_header(df, trade_df=None):
    """Display comprehensive performance metrics at the top of dashboard"""
    st.header("📊 Trade Performance Overview")
    
    metrics = calculate_performance_metrics(df, trade_df)
    
    # Main metrics row
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric(
            "Total Executed Trades", 
            metrics['total_executed'],
            help="Number of trades that were actually executed in the market"
        )
    
    with col2:
        if metrics['win_rate'] > 0:
            st.metric(
                "Win Rate", 
                f"{metrics['win_rate']:.1f}%",
                help="Percentage of profitable trades (requires MT5 data)"
            )
        else:
            st.metric(
                "Win Rate", 
                "N/A",
                help="Win rate calculation requires MT5 trade data"
            )
    
    with col3:
        st.metric(
            "Avg Tech Score", 
            f"{metrics['avg_tech_score']:.1f}" if metrics['avg_tech_score'] > 0 else "N/A",
            help="Average technical analysis score across all decisions"
        )
    
    with col4:
        st.metric(
            "Avg AI Confidence", 
            f"{metrics['avg_ai_confidence']:.1f}/10" if metrics['avg_ai_confidence'] > 0 else "N/A",
            help="Average AI confidence level across all decisions"
        )
    
    with col5:
        st.metric(
            "Skipped/Blocked Trades", 
            metrics['skipped_blocked'],
            help="Trades that had BUY/SELL signals but were not executed"
        )
    
    with col6:
        st.metric(
            "Technical Overrides", 
            metrics['technical_overrides'],
            help="Cases where technical analysis overrode AI decisions"
        )
    
    # Additional insights row
    if metrics['total_decisions'] > 0:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            execution_rate = (metrics['total_executed'] / metrics['total_decisions']) * 100
            st.metric(
                "Execution Rate",
                f"{execution_rate:.1f}%",
                help="Percentage of decisions that resulted in executed trades"
            )
        
        with col2:
            hold_decisions = metrics['total_decisions'] - metrics['total_executed'] - metrics['skipped_blocked']
            st.metric(
                "HOLD Decisions",
                hold_decisions,
                help="Number of times the system decided to hold and not trade"
            )
        
        with col3:
            if metrics['technical_overrides'] > 0:
                override_rate = (metrics['technical_overrides'] / metrics['total_decisions']) * 100
                st.metric(
                    "Override Rate",
                    f"{override_rate:.1f}%",
                    help="Percentage of decisions where technical analysis overrode AI"
                )
            else:
                st.metric(
                    "AI Agreement",
                    "100%",
                    help="AI and technical analysis are in full agreement"
                )




def display_enhanced_ai_table(filtered_df, trade_df=None):
    """Enhanced table display for AI decisions with trade matching and override display"""
    
    if filtered_df.empty:
        st.info("No decisions match the current filters.")
        return
    
    # Format the data with trade matching
    display_df = format_table_data(filtered_df, trade_df)
    
      # === NEW: Collapsible Enhanced Filters ===
    with st.sidebar.expander("📊 Enhanced Filters", expanded=False):
        # Execution Status Filter
        execution_options = ['All', 'Executed', 'Not Executed']
        selected_execution = st.selectbox(
            "Execution Status",
            execution_options,
            help="Filter by whether the trade was executed (checks actual trades)"
        )
        
        # AI Override Filter
        override_options = ['All', 'Override Cases', 'AI Decisions']
        selected_override = st.selectbox(
            "Decision Type",
            override_options,
            help="Show cases where AI decisions were overridden by technical signals"
        )
        
        # Direction Filter
        directions = ['All'] + sorted([d for d in display_df['direction'].unique() if pd.notna(d)])
        selected_direction = st.selectbox(
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
        st.metric("Filtered Decisions", len(display_df))
    
    with col2:
        executed_count = len(display_df[display_df['executed'] == True])
        st.metric("Executed", executed_count)
    
    with col3:
        hold_count = len(display_df[display_df['direction'] == 'HOLD'])
        st.metric("HOLD", hold_count)
    
    with col4:
        override_count = len(display_df[display_df['ai_override'] == True])
        st.metric("Overrides", override_count)
    
    with col5:
        if len(display_df) > 0:
            confidence_col = 'ai_confidence' if 'ai_confidence' in display_df.columns and display_df['ai_confidence'].notna().any() else 'confidence'
            avg_confidence = pd.to_numeric(display_df[confidence_col], errors='coerce').mean()
            st.metric("Avg Confidence", f"{avg_confidence:.1f}" if not pd.isna(avg_confidence) else "N/A")
        else:
            st.metric("Avg Confidence", "N/A")
    
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
            timestamp_str = pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['timestamp']) else 'Unknown Time'
            st.markdown(f"### {row['symbol']} – {timestamp_str}")
            
            # === NEW: Enhanced Decision Display ===
            decision_display = row.get('decision_display', 'N/A')
            if row.get('ai_override', False):
                st.markdown(f"🔄 **{decision_display}**")
            else:
                direction = row['direction']
                emoji = "🟢" if direction == "BUY" else "🔴" if direction == "SELL" else "🟡"
                st.markdown(f"{emoji} **{decision_display}**")
            
            # === NEW: Display key metrics with N/A handling ===
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sl_val = row.get('sl', 'N/A')
                tp_val = row.get('tp', 'N/A')
                st.text(f"SL: {sl_val}")
                st.text(f"TP: {tp_val}")
                st.text(f"Executed: {'✅ Yes' if row['executed'] else '❌ No'}")
            
            with col2:
                technical_score = row.get('technical_score', 'N/A')
                ema_trend = row.get('ema_trend', 'N/A')
                st.text(f"Technical Score: {technical_score}")
                st.text(f"EMA Trend: {ema_trend}")
            
            with col3:
                ai_confidence = row.get('ai_confidence', row.get('confidence', 'N/A'))
                if ai_confidence != 'N/A' and pd.notna(ai_confidence):
                    st.text(f"AI Confidence: {ai_confidence}/10")
                else:
                    st.text(f"AI Confidence: N/A")
                
                if 'trade_profit' in row and pd.notna(row['trade_profit']) and row['trade_profit'] != 'N/A':
                    profit_color = "🟢" if float(row['trade_profit']) > 0 else "🔴"
                    st.text(f"P&L: {profit_color} {row['trade_profit']}")
            
            # === NEW: Expandable sections with N/A handling ===
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("📖 AI Reasoning"):
                    reasoning = row.get('ai_reasoning', row.get('reasoning', 'N/A'))
                    if reasoning == 'N/A' or pd.isna(reasoning) or str(reasoning).strip() == '':
                        st.write("No reasoning provided")
                    else:
                        st.write(str(reasoning))
            
            
            with col2:
                with st.expander("⚠️ Risk Assessment"):
                    risk_note = row.get('ai_risk_note', row.get('risk_note', 'N/A'))
                    if risk_note == 'N/A' or pd.isna(risk_note) or str(risk_note).strip() == '':
                        st.write("No risk assessment provided")
                    else:
                        st.write(str(risk_note))
            
            # Show override details if applicable
            if row.get('ai_override', False):
                with st.expander("🔄 Override Details"):
                    override_reason = row.get('ai_override_reason', 'N/A')
                    if override_reason != 'N/A' and pd.notna(override_reason):
                        st.warning(str(override_reason))
                    
                    if 'trade_price' in row and pd.notna(row['trade_price']) and row['trade_price'] != 'N/A':
                        st.write("**Executed Trade Details:**")
                        st.write(f"• Price: {row['trade_price']}")
                        st.write(f"• Volume: {row['trade_volume']}")
                        st.write(f"• Profit/Loss: {row['trade_profit']}")
            
            st.markdown("---")
    
    # === Export Options ===
    st.subheader("📥 Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = display_df.to_csv(index=False)
        st.download_button(
            label="📊 Download as CSV",
            data=csv_data,
            file_name=f"ai_trading_decisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Download filtered data with all columns as CSV file"
        )
    
    with col2:
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

# === NEW: Display Performance Metrics Header ===
display_performance_header(log_df, trade_df)
st.markdown("---")

# === NEW: Collapsible Sidebar Filters ===
with st.sidebar.expander("🔍 Basic Filters", expanded=True):
    # **Debug timestamp information**
    st.markdown("### 📅 Date Info")
    st.write(f"**Total entries:** {len(log_df)}")
    st.write(f"**Date range in data:**")
    st.write(f"From: {log_df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S')}")
    st.write(f"To: {log_df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show entries per date for debugging
    date_counts = log_df['timestamp'].dt.date.value_counts().sort_index()
    st.write("**Entries per date:**")
    for date, count in date_counts.items():
        st.write(f"  {date}: {count} entries")
    
    st.markdown("---")
    
    # Symbol filter
    symbols = sorted(log_df["symbol"].dropna().unique())
    selected_symbols = st.multiselect("Symbol", options=symbols, default=symbols)
    
    # **Improved date range handling**
    # Convert to local timezone for date picker (removes timezone info for date comparison)
    log_df_local = log_df.copy()
    log_df_local["timestamp_local"] = log_df_local["timestamp"].dt.tz_convert(None)
    
    min_date = log_df_local["timestamp_local"].min().date()
    max_date = log_df_local["timestamp_local"].max().date()
    
    # **More flexible date range picker**
    st.write(f"Available date range: {min_date} to {max_date}")
    
    # Force max_date to be at least today if data exists for today
    today = date.today()
    if max_date < today and len(log_df_local[log_df_local["timestamp_local"].dt.date == today]) > 0:
        max_date = today
    
    date_range = st.date_input(
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
        
        st.write(f"**Confidence range:** {min_conf} to {max_conf}")
        
        if min_conf < max_conf:
            conf_filter = st.slider("Confidence (min)", min_conf, max_conf, min_conf)
        else:
            st.markdown(f"Only one confidence level found: **{min_conf}**")
            conf_filter = min_conf
    else:
        st.warning("No valid confidence values found")
        conf_filter = 0
    
    # Search box
    search_term = st.text_input("Search (reasoning or risk note)").lower()

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
st.caption("Built by Divine Earnings | Phase 2.0 – Enhanced Dashboard with Performance Metrics | Complete Trade Analytics 📊")