# ------------------------------------------------------------------------------------
# 📊 analytics_dashboard.py – D.E.V.I. Analytics Dashboard
#
# Purpose: Visualize D.E.V.I.'s full trading performance since launch (July 21/22), 
# using live data and config-defined risk parameters, with auto-updating logic 
# and clear visual feedback.
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import os
import sys
import numpy as np
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
import config

# Add current directory for utils
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from log_utils import LogProcessor

class AnalyticsDashboard:
    """Comprehensive analytics dashboard for D.E.V.I. trading bot"""
    
    def __init__(self):
        self.log_processor = LogProcessor()
        self.config_data = config.CONFIG
        self.ftmo_params = config.FTMO_PARAMS
        
        # File paths
        self.balance_history_path = "Data Files/balance_history.csv"
        self.trade_log_path = "Data Files/trade_log.csv"
        self.ai_decision_log_path = "Data Files/ai_decision_log.jsonl"
        
        # Initialize data
        self.balance_history = self._load_balance_history()
        self.trade_log = self._load_trade_log()
        self.ai_decision_log = self._load_ai_decision_log()
    
    def _load_balance_history(self) -> pd.DataFrame:
        """Load balance history from CSV or create from MT5 data"""
        try:
            if os.path.exists(self.balance_history_path):
                df = pd.read_csv(self.balance_history_path)
                df['date'] = pd.to_datetime(df['date'])
                
                # Add today's real-time data if not already present
                today = datetime.now().date()
                if df.empty or df['date'].dt.date.iloc[-1] != today:
                    try:
                        import MetaTrader5 as mt5
                        if mt5.initialize():
                            account_info = mt5.account_info()
                            if account_info:
                                today_data = pd.DataFrame({
                                    'date': [today],
                                    'balance': [account_info.balance],
                                    'equity': [account_info.equity]
                                })
                                df = pd.concat([df, today_data], ignore_index=True)
                            mt5.shutdown()
                    except Exception as e:
                        st.warning(f"Could not get real-time balance: {e}")
                
                return df
            else:
                # Create balance history from trade log and MT5 data
                return self._create_balance_history()
        except Exception as e:
            st.error(f"Error loading balance history: {e}")
            return pd.DataFrame()
    
    def _create_balance_history(self) -> pd.DataFrame:
        """Create balance history from available data"""
        try:
            # Get initial balance from config
            initial_balance = self.ftmo_params.get("initial_balance", 10000)
            
            # Create daily balance tracking from trade log
            if not self.trade_log.empty and 'timestamp' in self.trade_log.columns:
                self.trade_log['date'] = pd.to_datetime(self.trade_log['timestamp']).dt.date
                daily_pnl = self.trade_log.groupby('date')['profit'].sum().reset_index()
                daily_pnl['date'] = pd.to_datetime(daily_pnl['date'])
                
                # Calculate cumulative balance
                daily_pnl['balance'] = initial_balance + daily_pnl['profit'].cumsum()
                daily_pnl['equity'] = daily_pnl['balance']  # Simplified for now
                
                return daily_pnl[['date', 'balance', 'equity']]
            else:
                # Fallback: create single entry with initial balance
                return pd.DataFrame({
                    'date': [datetime.now().date()],
                    'balance': [initial_balance],
                    'equity': [initial_balance]
                })
        except Exception as e:
            st.error(f"Error creating balance history: {e}")
            return pd.DataFrame()
    
    def _load_trade_log(self) -> pd.DataFrame:
        """Load trade log data"""
        try:
            return self.log_processor.load_trade_log()
        except Exception as e:
            st.error(f"Error loading trade log: {e}")
            return pd.DataFrame()
    
    def _load_ai_decision_log(self) -> pd.DataFrame:
        """Load AI decision log data"""
        try:
            return self.log_processor.load_ai_decision_log()
        except Exception as e:
            st.error(f"Error loading AI decision log: {e}")
            return pd.DataFrame()
    
    def get_top_metrics(self) -> Dict:
        """Calculate top metrics overview using real-time MT5 data"""
        try:
            import MetaTrader5 as mt5
            initial_balance = self.ftmo_params.get("initial_balance", 10000)
            
            # Get real-time MT5 balance and equity
            current_balance = initial_balance
            current_equity = initial_balance
            
            try:
                if mt5.initialize():
                    account_info = mt5.account_info()
                    if account_info:
                        current_balance = account_info.balance
                        current_equity = account_info.equity
                    mt5.shutdown()
            except Exception as e:
                st.warning(f"Could not get real-time MT5 data: {e}")
                # Fallback to balance history
                if not self.balance_history.empty:
                    current_balance = self.balance_history['balance'].iloc[-1]
                    current_equity = self.balance_history['equity'].iloc[-1]
            
            total_pnl = current_balance - initial_balance
            profit_percent = (total_pnl / initial_balance) * 100 if initial_balance > 0 else 0
            
            # Calculate trade accuracy
            if not self.trade_log.empty and 'result' in self.trade_log.columns:
                tp_count = len(self.trade_log[self.trade_log['result'] == 'TP'])
                sl_count = len(self.trade_log[self.trade_log['result'] == 'SL'])
                partial_count = len(self.trade_log[self.trade_log['result'] == 'Partial'])
                total_trades = tp_count + sl_count + partial_count
                trade_accuracy = (tp_count / total_trades * 100) if total_trades > 0 else 0
            else:
                trade_accuracy = 0
            
            return {
                'initial_balance': initial_balance,
                'current_balance': current_balance,
                'current_equity': current_equity,
                'total_pnl': total_pnl,
                'profit_percent': profit_percent,
                'trade_accuracy': trade_accuracy
            }
        except Exception as e:
            st.error(f"Error calculating top metrics: {e}")
            return {}
    
    def create_daily_performance_chart(self) -> go.Figure:
        """Create daily performance chart with markers using real-time data"""
        try:
            if self.balance_history.empty:
                return go.Figure()
            
            # Get real-time MT5 data for today
            balance_data = self.balance_history.copy()
            today = datetime.now().date()
            
            try:
                import MetaTrader5 as mt5
                if mt5.initialize():
                    account_info = mt5.account_info()
                    if account_info:
                        # Update today's data with real-time values
                        today_mask = balance_data['date'].dt.date == today
                        if today_mask.any():
                            balance_data.loc[today_mask, 'balance'] = account_info.balance
                            balance_data.loc[today_mask, 'equity'] = account_info.equity
                        else:
                            # Add today's data if not present
                            today_data = pd.DataFrame({
                                'date': [today],
                                'balance': [account_info.balance],
                                'equity': [account_info.equity]
                            })
                            balance_data = pd.concat([balance_data, today_data], ignore_index=True)
                    mt5.shutdown()
            except Exception as e:
                st.warning(f"Could not get real-time chart data: {e}")
            
            # Calculate daily changes for markers
            balance_data['change'] = balance_data['balance'].diff()
            
            # Create markers based on daily P&L
            markers = []
            colors = []
            for change in balance_data['change']:
                if pd.isna(change):
                    markers.append('circle')
                    colors.append('grey')
                elif change > 0:
                    markers.append('triangle-up')
                    colors.append('green')
                elif change < 0:
                    markers.append('triangle-down')
                    colors.append('red')
                else:
                    markers.append('circle')
                    colors.append('grey')
            
            # Create the chart
            fig = go.Figure()
            
            # Balance line
            fig.add_trace(go.Scatter(
                x=balance_data['date'],
                y=balance_data['balance'],
                mode='lines+markers',
                name='Balance',
                line=dict(color='#00ff88', width=3),
                marker=dict(
                    symbol=markers,
                    size=8,
                    color=colors
                ),
                hovertemplate='<b>Date:</b> %{x}<br>' +
                            '<b>Balance:</b> $%{y:,.2f}<br>' +
                            '<b>Change:</b> %{text}<br>' +
                            '<extra></extra>',
                text=[f"${change:+,.2f}" if not pd.isna(change) else "N/A" 
                      for change in balance_data['change']]
            ))
            
            # Equity line (optional)
            if 'equity' in balance_data.columns:
                fig.add_trace(go.Scatter(
                    x=balance_data['date'],
                    y=balance_data['equity'],
                    mode='lines',
                    name='Equity',
                    line=dict(color='rgba(0, 150, 255, 0.6)', width=2),
                    hovertemplate='<b>Date:</b> %{x}<br>' +
                                '<b>Equity:</b> $%{y:,.2f}<br>' +
                                '<extra></extra>'
                ))
            
            # Add reference lines
            initial_balance = self.ftmo_params.get("initial_balance", 10000)
            profit_target = initial_balance * (1 + self.ftmo_params.get("profit_target_pct", 0.10))
            max_loss = initial_balance * (1 - self.ftmo_params.get("max_total_loss_pct", 0.10))
            
            # Start balance line
            fig.add_hline(
                y=initial_balance,
                line_dash="dot",
                line_color="grey",
                annotation_text=f"Initial Balance: ${initial_balance:,.2f}"
            )
            
            # Profit target line
            fig.add_hline(
                y=profit_target,
                line_dash="solid",
                line_color="green",
                annotation_text=f"Profit Target: ${profit_target:,.2f}"
            )
            
            # Max loss line
            fig.add_hline(
                y=max_loss,
                line_dash="solid",
                line_color="red",
                annotation_text=f"Max Loss: ${max_loss:,.2f}"
            )
            
            # Update layout
            fig.update_layout(
                title="D.E.V.I. Daily Performance",
                xaxis_title="Date",
                yaxis_title="Balance ($)",
                hovermode='x unified',
                template='plotly_dark',
                height=500
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating performance chart: {e}")
            return go.Figure()
    
    def get_risk_objectives_status(self) -> List[Dict]:
        """Get risk objective tracking status"""
        try:
            initial_balance = self.ftmo_params.get("initial_balance", 10000)
            current_balance = self.balance_history['balance'].iloc[-1] if not self.balance_history.empty else initial_balance
            
            total_pnl = current_balance - initial_balance
            
            # Calculate daily loss
            if len(self.balance_history) >= 2:
                today_balance = self.balance_history['balance'].iloc[-1]
                yesterday_balance = self.balance_history['balance'].iloc[-2]
                daily_loss = yesterday_balance - today_balance
            else:
                daily_loss = 0
            
            # Count unique trading days
            if not self.trade_log.empty and 'timestamp' in self.trade_log.columns:
                trading_dates = pd.to_datetime(self.trade_log['timestamp']).dt.date.unique()
                trading_days = len(trading_dates)
            else:
                trading_days = 0
            
            objectives = [
                {
                    'objective': 'Profit Target',
                    'current_value': total_pnl,
                    'config_limit': initial_balance * self.ftmo_params.get("profit_target_pct", 0.10),
                    'status': '✅' if total_pnl >= initial_balance * self.ftmo_params.get("profit_target_pct", 0.10) else '❌',
                    'notes': f"Target: ${initial_balance * self.ftmo_params.get('profit_target_pct', 0.10):,.2f}"
                },
                {
                    'objective': 'Max Total Loss',
                    'current_value': abs(total_pnl) if total_pnl < 0 else 0,
                    'config_limit': initial_balance * self.ftmo_params.get("max_total_loss_pct", 0.10),
                    'status': '✅' if abs(total_pnl) <= initial_balance * self.ftmo_params.get("max_total_loss_pct", 0.10) else '❌',
                    'notes': f"Limit: ${initial_balance * self.ftmo_params.get('max_total_loss_pct', 0.10):,.2f}"
                },
                {
                    'objective': 'Max Daily Loss',
                    'current_value': daily_loss if daily_loss > 0 else 0,
                    'config_limit': initial_balance * self.ftmo_params.get("max_daily_loss_pct", 0.05),
                    'status': '✅' if daily_loss <= initial_balance * self.ftmo_params.get("max_daily_loss_pct", 0.05) else '❌',
                    'notes': f"Limit: ${initial_balance * self.ftmo_params.get('max_daily_loss_pct', 0.05):,.2f}"
                },
                {
                    'objective': 'Min Trading Days',
                    'current_value': trading_days,
                    'config_limit': self.ftmo_params.get("min_trading_days", 4),
                    'status': '✅' if trading_days >= self.ftmo_params.get("min_trading_days", 4) else '❌',
                    'notes': f"Required: {self.ftmo_params.get('min_trading_days', 4)} days"
                }
            ]
            
            return objectives
            
        except Exception as e:
            st.error(f"Error calculating risk objectives: {e}")
            return []
    
    def get_ai_insights(self) -> Dict:
        """Get AI insights breakdown"""
        try:
            if self.ai_decision_log.empty:
                return {}
            
            # Average confidence (last 5 + all-time)
            if 'ai_confidence' in self.ai_decision_log.columns:
                # Convert confidence to numeric, handling non-numeric values
                confidence_values = []
                for conf in self.ai_decision_log['ai_confidence']:
                    try:
                        if isinstance(conf, str) and '%' in conf:
                            conf = float(conf.replace('%', ''))
                        elif isinstance(conf, str) and conf.isdigit():
                            conf = float(conf)
                        elif isinstance(conf, (int, float)):
                            conf = float(conf)
                        else:
                            continue
                        confidence_values.append(conf)
                    except:
                        continue
                
                if confidence_values:
                    avg_confidence_all = np.mean(confidence_values)
                    avg_confidence_recent = np.mean(confidence_values[-5:]) if len(confidence_values) >= 5 else avg_confidence_all
                else:
                    avg_confidence_all = 0
                    avg_confidence_recent = 0
            else:
                avg_confidence_all = 0
                avg_confidence_recent = 0
            
            # Count trade types
            ai_confirmed = len(self.ai_decision_log[self.ai_decision_log['ai_override'] == False])
            technical_overrides = len(self.ai_decision_log[self.ai_decision_log['ai_override'] == True])
            missed_trades = len(self.ai_decision_log[self.ai_decision_log['executed'] == False])
            
            # Top reasoning strings
            if 'ai_reasoning' in self.ai_decision_log.columns:
                reasoning_counts = self.ai_decision_log['ai_reasoning'].value_counts().head(3)
                top_reasoning = reasoning_counts.to_dict()
            else:
                top_reasoning = {}
            
            return {
                'avg_confidence_all': avg_confidence_all,
                'avg_confidence_recent': avg_confidence_recent,
                'ai_confirmed_trades': ai_confirmed,
                'technical_overrides': technical_overrides,
                'missed_trades': missed_trades,
                'top_reasoning': top_reasoning
            }
            
        except Exception as e:
            st.error(f"Error calculating AI insights: {e}")
            return {}
    
    def render_dashboard(self):
        """Render the analytics dashboard with real-time updates"""
        # Add cache control for real-time updates
        st.cache_data.clear()
        
        # Refresh balance history with real-time data
        self.balance_history = self._load_balance_history()
        
        """Render the complete analytics dashboard"""
        st.title("🧠 D.E.V.I. Analytics Dashboard")
        
        # Add refresh button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Refresh Data", key="refresh_analytics"):
                st.cache_data.clear()
                st.rerun()
        with col2:
            st.caption("Last updated: " + datetime.now().strftime("%H:%M:%S"))
            st.caption("Data source: Real-time MT5")
        
        st.markdown("---")
        
        # Top Metrics Overview
        st.header("📊 Top Metrics Overview")
        metrics = self.get_top_metrics()
        
        if metrics:
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                st.metric("Initial Balance", f"${metrics['initial_balance']:,.2f}")
            
            with col2:
                st.metric("Current Balance", f"${metrics['current_balance']:,.2f}")
            
            with col3:
                st.metric("Current Equity", f"${metrics['current_equity']:,.2f}")
            
            with col4:
                st.metric("Total P&L", f"${metrics['total_pnl']:+,.2f}")
            
            with col5:
                st.metric("Profit %", f"{metrics['profit_percent']:+.2f}%")
            
            with col6:
                st.metric("Trade Accuracy", f"{metrics['trade_accuracy']:.1f}%")
        
        st.markdown("---")
        
        # Daily Performance Chart
        st.header("📈 Daily Performance Chart")
        st.caption("Chart includes real-time MT5 balance data for today")
        chart = self.create_daily_performance_chart()
        if chart.data:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("No balance history data available for chart")
        
        st.markdown("---")
        
        # Risk Objectives Tracker
        st.header("🎯 Risk Objective Tracker")
        objectives = self.get_risk_objectives_status()
        
        if objectives:
            obj_df = pd.DataFrame(objectives)
            st.dataframe(
                obj_df,
                column_config={
                    "objective": "Objective",
                    "status": "Status",
                    "current_value": st.column_config.NumberColumn("Current Value", format="$%.2f"),
                    "config_limit": st.column_config.NumberColumn("Config Limit", format="$%.2f"),
                    "notes": "Notes"
                },
                hide_index=True,
                use_container_width=True
            )
        
        st.markdown("---")
        
        # Trade Log Table
        st.header("📋 Trade Log Table (All-Time)")
        if not self.trade_log.empty:
            # Prepare trade log for display
            display_log = self.trade_log.copy()
            if 'timestamp' in display_log.columns:
                display_log['Date'] = pd.to_datetime(display_log['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Select columns to display
            columns_to_show = ['Date', 'symbol', 'direction', 'lot', 'entry_price', 'profit', 'result']
            available_columns = [col for col in columns_to_show if col in display_log.columns]
            
            st.dataframe(
                display_log[available_columns],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No trade log data available")
        
        st.markdown("---")
        
        # AI Insights Breakdown
        st.header("🤖 AI Insight Breakdown")
        ai_insights = self.get_ai_insights()
        
        if ai_insights:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Confidence Metrics")
                st.metric("All-Time Avg Confidence", f"{ai_insights['avg_confidence_all']:.1f}%")
                st.metric("Recent Avg Confidence", f"{ai_insights['avg_confidence_recent']:.1f}%")
            
            with col2:
                st.subheader("Trade Execution")
                st.metric("AI Confirmed Trades", ai_insights['ai_confirmed_trades'])
                st.metric("Technical Overrides", ai_insights['technical_overrides'])
                st.metric("Missed Trades", ai_insights['missed_trades'])
            
            if ai_insights['top_reasoning']:
                st.subheader("Top AI Reasoning")
                for reason, count in ai_insights['top_reasoning'].items():
                    st.write(f"• **{reason}**: {count} times")
        else:
            st.info("No AI decision log data available")
        
        # Auto-refresh button
        if st.button("🔄 Refresh Analytics", key="refresh_analytics_dashboard"):
            st.rerun()

def main():
    """Main function to run the analytics dashboard"""
    st.set_page_config(
        page_title="D.E.V.I. Analytics Dashboard",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize dashboard
    dashboard = AnalyticsDashboard()
    
    # Render dashboard
    dashboard.render_dashboard()

if __name__ == "__main__":
    main() 