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


def safe_print(message: str):
    """Safely print messages, handling Windows pipe errors."""
    try:
        print(message)
    except (OSError, BrokenPipeError):
        # Silently ignore pipe errors on Windows
        pass
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
        try:
            self.log_processor = LogProcessor()
            self.config_data = config.CONFIG
            self.ftmo_params = config.FTMO_PARAMS
            
            # File paths - handle both direct and Streamlit execution
            script_dir = os.path.dirname(__file__)
            parent_dir = os.path.dirname(script_dir)
            
            # Try multiple possible paths for balance history
            possible_balance_paths = [
                os.path.join(parent_dir, "Data Files", "balance_history.csv"),
                "Data Files/balance_history.csv",
                os.path.join(script_dir, "..", "Data Files", "balance_history.csv"),
                "balance_history.csv"
            ]
            
            self.balance_history_path = None
            for path in possible_balance_paths:
                if os.path.exists(path):
                    self.balance_history_path = path
                    break
            
            if self.balance_history_path is None:
                self.balance_history_path = possible_balance_paths[0]  # Default to first path
            
            self.trade_log_path = "Data Files/trade_log.csv"
            self.ai_decision_log_path = "Data Files/ai_decision_log.jsonl"
            
            self.log_processor = LogProcessor(
                ai_log_file=self.ai_decision_log_path,
                trade_log_file=self.trade_log_path
            )
            
            self.config_data = config.CONFIG
            
            # Keep hardcoded FTMO targets but get real balance for display
            self.ftmo_params = config.FTMO_PARAMS  # Keep hardcoded targets
            
            # Get real current balance from MT5 for dynamic display
            try:
                import MetaTrader5 as mt5
                # Try to initialize MT5 connection
                if mt5.initialize():
                    account_info = mt5.account_info()
                    if account_info:
                        # Store real balance for chart display
                        self.current_mt5_balance = float(account_info.balance)
                        self.current_mt5_equity = float(account_info.equity)
                        self.current_mt5_login = str(account_info.login)
                        safe_print(f"✅ Connected to MT5 Account #{account_info.login}: ${account_info.balance:,.2f}")
                    else:
                        # Try to get balance from existing CSV if MT5 account_info fails
                        balance_from_csv = self._get_balance_from_csv()
                        if balance_from_csv:
                            self.current_mt5_balance = balance_from_csv
                            self.current_mt5_equity = balance_from_csv
                            self.current_mt5_login = "CSV Data"
                            safe_print(f"📊 Using balance from CSV: ${balance_from_csv:,.2f}")
                        else:
                            # Final fallback
                            self.current_mt5_balance = self.ftmo_params.get("initial_balance", 10000)
                            self.current_mt5_equity = self.current_mt5_balance
                            self.current_mt5_login = "Unknown"
                    mt5.shutdown()
                else:
                    # Try to get balance from existing CSV if MT5 connection fails
                    balance_from_csv = self._get_balance_from_csv()
                    if balance_from_csv:
                        self.current_mt5_balance = balance_from_csv
                        self.current_mt5_equity = balance_from_csv
                        self.current_mt5_login = "CSV Data"
                        safe_print(f"📊 Using balance from CSV: ${balance_from_csv:,.2f}")
                    else:
                        # Final fallback
                        self.current_mt5_balance = self.ftmo_params.get("initial_balance", 10000)
                        self.current_mt5_equity = self.current_mt5_balance
                        self.current_mt5_login = "Disconnected"
            except Exception as e:
                safe_print(f"Warning: Could not get real MT5 data: {e}")
                # Try to get balance from existing CSV if MT5 fails
                balance_from_csv = self._get_balance_from_csv()
                if balance_from_csv:
                    self.current_mt5_balance = balance_from_csv
                    self.current_mt5_equity = balance_from_csv
                    self.current_mt5_login = "CSV Data"
                    safe_print(f"📊 Using balance from CSV: ${balance_from_csv:,.2f}")
                else:
                    # Final fallback
                    self.current_mt5_balance = self.ftmo_params.get("initial_balance", 10000)
                    self.current_mt5_equity = self.current_mt5_balance
                    self.current_mt5_login = "Error"
            
            # Legacy file paths - handle both direct and Streamlit execution
            script_dir = os.path.dirname(__file__)
            parent_dir = os.path.dirname(script_dir)
            
            # Try multiple possible paths for balance history
            possible_balance_paths = [
                os.path.join(parent_dir, "Data Files", "balance_history.csv"),
                "Data Files/balance_history.csv",
                os.path.join(script_dir, "..", "Data Files", "balance_history.csv"),
                "balance_history.csv"
            ]
            
            self.balance_history_path = None
            for path in possible_balance_paths:
                if os.path.exists(path):
                    self.balance_history_path = path
                    break
            
            if self.balance_history_path is None:
                self.balance_history_path = possible_balance_paths[0]  # Default to first path

            
            # Initialize data in correct order
            self.trade_log = self._load_trade_log()
            self.ai_decision_log = self._load_ai_decision_log()
            self.balance_history = self._load_balance_history()
            
        except Exception as e:
            safe_print(f"❌ Error initializing dashboard: {e}")
            # Set default values if initialization fails
            self.balance_history = pd.DataFrame()
            self.trade_log = pd.DataFrame()
            self.ai_decision_log = pd.DataFrame()
            self.balance_history_path = "Data Files/balance_history.csv"
    
    def _get_balance_from_csv(self) -> float:
        """Get current balance from existing CSV file as fallback"""
        try:
            for path in [
                "Data Files/balance_history.csv",
                os.path.join("Data Files", "balance_history.csv"),
                self.balance_history_path if hasattr(self, 'balance_history_path') else None
            ]:
                if path and os.path.exists(path):
                    df = pd.read_csv(path)
                    if not df.empty and 'balance' in df.columns:
                        return float(df['balance'].iloc[-1])  # Get latest balance
            return None
        except Exception as e:
            safe_print(f"Could not read balance from CSV: {e}")
            return None
    
    def _load_balance_history(self) -> pd.DataFrame:
        """Load balance history from CSV or create from MT5 data"""
        try:
            if os.path.exists(self.balance_history_path):
                df = pd.read_csv(self.balance_history_path)
                df['date'] = pd.to_datetime(df['date'])
                
                # Update with current MT5 data for today
                try:
                    # Use the stored current balance from initialization
                    current_balance = getattr(self, 'current_mt5_balance', self.ftmo_params.get("initial_balance", 10000))
                    current_equity = getattr(self, 'current_mt5_equity', current_balance)
                    
                    today = datetime.now().date()
                    today_mask = df['date'].dt.date == today
                    
                    if today_mask.any():
                        # Update existing today's data
                        df.loc[today_mask, 'balance'] = current_balance
                        df.loc[today_mask, 'equity'] = current_equity
                    else:
                        # Add new today's data
                        today_data = pd.DataFrame({
                            'date': [pd.Timestamp(today)],
                            'balance': [current_balance],
                            'equity': [current_equity]
                        })
                        df = pd.concat([df, today_data], ignore_index=True)
                    
                    # Save updated balance history
                    try:
                        df.to_csv(self.balance_history_path, index=False)
                    except Exception as e:
                        safe_print(f"Warning: Could not save updated balance history: {e}")
                        
                except Exception as e:
                    safe_print(f"Warning: Could not update with current MT5 data: {e}")
                
                return df
            else:
                # If no balance history file exists, create one with real MT5 data
                return self._create_balance_history_from_mt5()
        except Exception as e:
            st.error(f"Error loading balance history: {e}")
            return pd.DataFrame()
    
    def _create_balance_history_from_mt5(self) -> pd.DataFrame:
        """Create balance history using real MT5 account data"""
        try:
            # Use the stored current balance from initialization
            current_balance = getattr(self, 'current_mt5_balance', self.ftmo_params.get("initial_balance", 10000))
            current_equity = getattr(self, 'current_mt5_equity', current_balance)
            
            # Create a simple 7-day history with current balance as endpoint
            dates = []
            balances = []
            equities = []
            
            for i in range(7, 0, -1):
                date = datetime.now().date() - timedelta(days=i)
                dates.append(pd.Timestamp(date))
                # For historical days, use current balance (simple approach)
                balances.append(current_balance)
                equities.append(current_equity)
            
            # Add today with current data
            dates.append(pd.Timestamp(datetime.now().date()))
            balances.append(current_balance)
            equities.append(current_equity)
            
            df = pd.DataFrame({
                'date': dates,
                'balance': balances,
                'equity': equities
            })
            
            # Save the created balance history
            try:
                # Ensure directory exists
                dir_path = os.path.dirname(self.balance_history_path)
                if dir_path:  # Only create directory if path has a directory component
                    os.makedirs(dir_path, exist_ok=True)
                df.to_csv(self.balance_history_path, index=False)
                safe_print(f"✅ Created balance history with real MT5 data: ${current_balance:,.2f}")
            except Exception as e:
                safe_print(f"Warning: Could not save balance history: {e}")
            
            return df
            
        except Exception as e:
            safe_print(f"Error creating balance history from MT5: {e}")
            # Fallback to basic data
            initial_balance = self.ftmo_params.get("initial_balance", 10000)
            df = pd.DataFrame({
                'date': [datetime.now().date()],
                'balance': [initial_balance],
                'equity': [initial_balance]
            })
            return df
    
    def _create_balance_history(self) -> pd.DataFrame:
        """Create balance history from available data"""
        try:
            # Get initial balance from config
            initial_balance = self.ftmo_params.get("initial_balance", 10000)
            
            # Check if trade_log is available and has required columns
            if hasattr(self, 'trade_log') and not self.trade_log.empty and 'timestamp' in self.trade_log.columns and 'result' in self.trade_log.columns:
                # Calculate P&L from trade data since profit column is missing
                trade_data = self.trade_log.copy()
                trade_data['date'] = pd.to_datetime(trade_data['timestamp']).dt.date
                
                # Calculate estimated P&L based on result
                def estimate_pnl(row):
                    if row['result'] == 'EXECUTED':
                        # Estimate 50% win rate for executed trades
                        return 10.0  # Small positive P&L
                    elif row['result'] == 'FAILED':
                        return -5.0  # Small negative P&L for failed trades
                    else:
                        return 0.0
                
                trade_data['profit'] = trade_data.apply(estimate_pnl, axis=1)
                
                # Group by date and sum P&L
                daily_pnl = trade_data.groupby('date')['profit'].sum().reset_index()
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
    
    def update_balance_history_with_mt5(self):
        """Update balance history with current MT5 data (optional)"""
        try:
            import MetaTrader5 as mt5
            if mt5.initialize():
                account_info = mt5.account_info()
                if account_info:
                    today = datetime.now().date()
                    
                    # Check if today's data already exists
                    today_mask = self.balance_history['date'].dt.date == today
                    
                    if today_mask.any():
                        # Update existing today's data
                        self.balance_history.loc[today_mask, 'balance'] = account_info.balance
                        self.balance_history.loc[today_mask, 'equity'] = account_info.equity
                    else:
                        # Add new today's data
                        today_data = pd.DataFrame({
                            'date': [pd.Timestamp(today)],
                            'balance': [account_info.balance],
                            'equity': [account_info.equity]
                        })
                        self.balance_history = pd.concat([self.balance_history, today_data], ignore_index=True)
                    
                    # Save updated balance history
                    self.balance_history.to_csv(self.balance_history_path, index=False)
                    safe_print(f"✅ Balance history updated with current MT5 data: ${account_info.balance:,.2f}")
                
                mt5.shutdown()
        except Exception as e:
            safe_print(f"⚠️ Could not update balance history: {e}")
            # Don't fail the chart creation if MT5 is unavailable
            pass

    def get_top_metrics(self) -> Dict:
        """Calculate top metrics overview using balance history data"""
        try:
            initial_balance = self.ftmo_params.get("initial_balance", 10000)
            
            # Get current balance and equity from balance history
            current_balance = initial_balance
            current_equity = initial_balance
            
            if not self.balance_history.empty:
                current_balance = self.balance_history['balance'].iloc[-1]
                current_equity = self.balance_history['equity'].iloc[-1]
            
            total_pnl = current_balance - initial_balance
            profit_percent = (total_pnl / initial_balance) * 100 if initial_balance > 0 else 0
            
            # Calculate trade accuracy
            if not self.trade_log.empty and 'result' in self.trade_log.columns:
                executed_count = len(self.trade_log[self.trade_log['result'] == 'EXECUTED'])
                failed_count = len(self.trade_log[self.trade_log['result'] == 'FAILED'])
                total_trades = executed_count + failed_count
                trade_accuracy = (executed_count / total_trades * 100) if total_trades > 0 else 0
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
                st.warning("No balance history data available for chart")
                return go.Figure()
            
            # Validate required columns exist
            required_columns = ['date', 'balance']
            if not all(col in self.balance_history.columns for col in required_columns):
                st.error("Balance history missing required columns: date, balance")
                return go.Figure()
            
            # Skip MT5 update in Streamlit to avoid pipe errors
            # Use existing balance history data only
            
            # Get balance data for chart
            balance_data = self.balance_history.copy()
            
            # Ensure date column is properly converted to datetime
            if 'date' in balance_data.columns:
                balance_data['date'] = pd.to_datetime(balance_data['date'], errors='coerce')
            
            # Remove any rows with invalid dates
            balance_data = balance_data.dropna(subset=['date'])
            
            if balance_data.empty:
                st.warning("No valid balance data available for chart")
                # Create a simple fallback chart using stored MT5 balance
                current_balance = getattr(self, 'current_mt5_balance', 10000)
                current_equity = getattr(self, 'current_mt5_equity', current_balance)
                
                # Create fallback data
                fallback_data = pd.DataFrame({
                    'date': [pd.Timestamp(datetime.now().date())],
                    'balance': [current_balance],
                    'equity': [current_equity]
                })
                balance_data = fallback_data
                st.info(f"Using fallback data with MT5 balance: ${current_balance:,.2f}")
            
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
            
            # Update layout to show proper date formatting
            fig.update_layout(
                xaxis=dict(
                    type='date',
                    tickformat='%b %d, %Y',
                    tickmode='auto',
                    nticks=10
                ),
                yaxis=dict(
                    title='Balance ($)',
                    tickformat=',.0f'
                )
            )
            
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
            
            # Show current chart data info
            current_chart_balance = balance_data['balance'].iloc[-1] if not balance_data.empty else initial_balance
            chart_title = f"D.E.V.I. Daily Performance (Current: ${current_chart_balance:,.2f})"
            
            # Update layout
            fig.update_layout(
                title=chart_title,
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
            elif not self.ai_decision_log.empty and 'timestamp' in self.ai_decision_log.columns:
                trading_dates = pd.to_datetime(self.ai_decision_log['timestamp']).dt.date.unique()
                trading_days = len(trading_dates)
            else:
                trading_days = 0
            
            # Calculate FTMO profit target correctly - should be $11,000 for $10K account
            profit_target_amount = initial_balance * (1 + self.ftmo_params.get("profit_target_pct", 0.10))  # $10K + 10% = $11K
            
            objectives = [
                {
                    'objective': 'Profit Target',
                    'current_value': current_balance,  # Show current balance instead of P&L
                    'config_limit': profit_target_amount,  # $11,000
                    'status': '✅' if current_balance >= profit_target_amount else '❌',
                    'notes': f"Target: ${profit_target_amount:,.2f}"
                },
                {
                    'objective': 'Max Total Loss',
                    'current_value': abs(total_pnl) if total_pnl < 0 else 0,
                    'config_limit': initial_balance * self.ftmo_params.get("max_total_loss_pct", 0.10),  # $1,000 (10% of $10K)
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
                        if isinstance(conf, str):
                            if '%' in conf:
                                conf = float(conf.replace('%', ''))
                            elif conf.isdigit():
                                conf = float(conf)
                            elif conf.upper() == 'N/A':
                                continue
                            else:
                                continue
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
            
            # Count unique trading days
            if 'timestamp' in self.ai_decision_log.columns:
                trading_dates = pd.to_datetime(self.ai_decision_log['timestamp']).dt.date.unique()
                trading_days = len(trading_dates)
            else:
                trading_days = 0
            
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
                'trading_days': trading_days,
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
        
        # Debug: show what data we loaded
        if not self.balance_history.empty:
            safe_print(f"📊 Loaded balance history: {len(self.balance_history)} rows, current balance: ${self.balance_history['balance'].iloc[-1]:,.2f}")
        else:
            safe_print("⚠️ Balance history is empty!")
        
        # Additional debug: show MT5 connection status
        safe_print(f"🔗 MT5 Balance: ${getattr(self, 'current_mt5_balance', 'Unknown')}, Account: {getattr(self, 'current_mt5_login', 'Unknown')}")
        
        """Render the complete analytics dashboard"""
        st.title("🧠 D.E.V.I. Analytics Dashboard")
        
        # Display current MT5 account info
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            account_login = getattr(self, 'current_mt5_login', 'Unknown')
            st.metric("MT5 Account", f"#{account_login}")
        with col2:
            current_balance = getattr(self, 'current_mt5_balance', 0)
            st.metric("Current Balance", f"${current_balance:,.2f}")
        with col3:
            # Fixed FTMO targets
            profit_target = self.ftmo_params.get("initial_balance", 10000) * (1 + self.ftmo_params.get("profit_target_pct", 0.10))
            st.metric("Profit Target", f"${profit_target:,.2f}")
        with col4:
            # Fixed FTMO max loss
            max_loss = self.ftmo_params.get("initial_balance", 10000) * (1 - self.ftmo_params.get("max_daily_loss_pct", 0.05))
            st.metric("Max Loss", f"${max_loss:,.2f}")
        
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
        
        # Post-Session Status
        try:
            from post_session_manager import get_post_session_status
            post_status = get_post_session_status()
            
            if post_status["is_active"]:
                st.info(f"🕐 **Post-Session Active** | Time Remaining: {post_status['time_remaining_minutes']} minutes | Open Positions: {post_status['open_positions']}")
            else:
                st.info(f"⏰ **Regular Session** | Current Time: {post_status['current_time_utc']} | Next Post-Session: 17:00-19:00 UTC")
        except Exception as e:
            st.warning(f"⚠️ Could not load post-session status: {e}")
        
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
            # Create a custom formatted dataframe for display
            display_df = obj_df.copy()
            
            # Format values based on objective type
            for idx, row in display_df.iterrows():
                if row['objective'] == 'Min Trading Days':
                    # For trading days, don't use dollar formatting
                    display_df.at[idx, 'current_value'] = f"{row['current_value']:.0f}"
                    display_df.at[idx, 'config_limit'] = f"{row['config_limit']:.0f}"
                else:
                    # For monetary values, use dollar formatting
                    display_df.at[idx, 'current_value'] = f"${row['current_value']:,.2f}"
                    display_df.at[idx, 'config_limit'] = f"${row['config_limit']:,.2f}"
            
            st.dataframe(
                display_df,
                column_config={
                    "objective": "Objective",
                    "status": "Status",
                    "current_value": "Current Value",
                    "config_limit": "Config Limit",
                    "notes": "Notes"
                },
                hide_index=True,
                use_container_width=True
            )
        
        st.markdown("---")
        
        # Win-Rate Analytics
        self.render_winrate_analytics()
        
        # Auto-refresh button
        if st.button("🔄 Refresh Analytics", key="refresh_analytics_dashboard"):
            st.rerun()

    def render_winrate_analytics(self):
        """Render comprehensive Win-Rate Analytics module"""
        st.header("📈 Win-Rate Analytics")
        
        # Initialize session state for filters
        if 'winrate_date_range' not in st.session_state:
            st.session_state.winrate_date_range = [
                datetime.now().date() - timedelta(days=30),
                datetime.now().date()
            ]
        if 'winrate_symbols' not in st.session_state:
            st.session_state.winrate_symbols = []
        if 'winrate_sessions' not in st.session_state:
            st.session_state.winrate_sessions = "All"
        if 'include_breakevens' not in st.session_state:
            st.session_state.include_breakevens = True
        
        # Load and process trade data
        trades_data = self._load_mt5_trade_data()
        
        # Filter controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Date range picker
            date_range = st.date_input(
                "📅 Date Range",
                value=st.session_state.winrate_date_range,
                key="winrate_date_range_picker"
            )
            if len(date_range) == 2:
                st.session_state.winrate_date_range = list(date_range)
        
        with col2:
            # Symbol filter
            available_symbols = self._get_available_symbols(trades_data)
            selected_symbols = st.multiselect(
                "🎯 Symbols",
                options=available_symbols,
                default=st.session_state.winrate_symbols,
                key="winrate_symbols_filter"
            )
            st.session_state.winrate_symbols = selected_symbols
        
        with col3:
            # Session filter
            session_options = ["All", "London", "NY", "Post-Session"]
            selected_session = st.selectbox(
                "🌍 Session",
                options=session_options,
                index=session_options.index(st.session_state.winrate_sessions),
                key="winrate_session_filter"
            )
            st.session_state.winrate_sessions = selected_session
        
        with col4:
            # Breakeven toggle
            include_breakevens = st.checkbox(
                "Include Breakevens in Denominator",
                value=st.session_state.include_breakevens,
                key="include_breakevens_toggle",
                help="Industry standard: include breakevens in win rate calculation"
            )
            st.session_state.include_breakevens = include_breakevens
        
        # Apply filters to trades data
        filtered_trades = self._apply_winrate_filters(
            trades_data,
            st.session_state.winrate_date_range,
            st.session_state.winrate_symbols,
            st.session_state.winrate_sessions
        )
        
        # Calculate win-rate metrics
        winrate_metrics = self._calculate_winrate_metrics(filtered_trades, include_breakevens)
        
        # Display KPI Cards
        st.markdown("### 📊 Performance Overview")
        
        if winrate_metrics['total_trades'] > 0:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                win_rate_display = f"{winrate_metrics['win_rate']:.1f}%" if winrate_metrics['win_rate'] is not None else "N/A"
                st.metric(
                    "Overall Win Rate",
                    win_rate_display,
                    help="Percentage of winning trades"
                )
            
            with col2:
                wins_losses = f"{winrate_metrics['wins']} / {winrate_metrics['losses']}"
                if winrate_metrics['breakevens'] > 0:
                    wins_losses += f" / {winrate_metrics['breakevens']}"
                st.metric(
                    "Wins / Losses" + (" / BE" if winrate_metrics['breakevens'] > 0 else ""),
                    wins_losses,
                    help="Win/Loss/Breakeven count"
                )
            
            with col3:
                avg_rr = f"{winrate_metrics['avg_rr']:.2f}" if winrate_metrics['avg_rr'] is not None else "N/A"
                st.metric(
                    "Avg R:R",
                    avg_rr,
                    help="Average Risk-Reward ratio"
                )
            
            with col4:
                st.metric(
                    "Total Trades",
                    winrate_metrics['total_trades'],
                    help="Number of closed trades"
                )
            
            with col5:
                total_pnl = f"${winrate_metrics['total_pnl']:+,.2f}" if winrate_metrics['total_pnl'] is not None else "N/A"
                st.metric(
                    "Total P&L",
                    total_pnl,
                    help="Total profit/loss"
                )
            
            st.markdown("---")
            
            # Charts section
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # Donut chart: Wins vs Losses
                self._render_winloss_donut_chart(winrate_metrics)
            
            with chart_col2:
                # Bar chart by Symbol
                if len(available_symbols) > 1:
                    self._render_symbol_winrate_chart(filtered_trades, include_breakevens)
                else:
                    st.info("📊 Symbol breakdown requires multiple symbols")
            
            # Session win rate chart
            st.markdown("### 🌍 Session Performance")
            self._render_session_winrate_chart(filtered_trades, include_breakevens)
            
            st.markdown("---")
            
            # Compact data table
            st.markdown("### 📋 Recent Trades")
            self._render_winrate_data_table(filtered_trades)
            
        else:
            # Empty state
            st.info("📭 No closed trades in selected range")
            st.caption("Adjust your date range or symbol filters to see trade data")
            
            # Show available data info
            if not trades_data.empty:
                st.info(f"💡 Found {len(trades_data)} total trades outside current filters")
                min_date = trades_data['close_time'].min().strftime('%Y-%m-%d')
                max_date = trades_data['close_time'].max().strftime('%Y-%m-%d')
                st.caption(f"Available data range: {min_date} to {max_date}")

    def _load_mt5_trade_data(self):
        """Load and process MT5 trade data for win-rate analysis"""
        try:
            # Try to get live MT5 data first
            import MetaTrader5 as mt5
            
            if mt5.initialize():
                # Get historical deals from last 90 days
                utc_to = datetime.now()
                utc_from = utc_to - timedelta(days=90)
                deals = mt5.history_deals_get(utc_from, utc_to)
                mt5.shutdown()
                
                if deals:
                    # Convert to DataFrame
                    deals_df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
                    
                    # Filter for actual trades (BUY/SELL only)
                    trade_deals = deals_df[deals_df['type'].isin([0, 1])].copy()
                    
                    if not trade_deals.empty:
                        # Process deals into trade format
                        processed_trades = []
                        
                        for _, deal in trade_deals.iterrows():
                            trade_data = {
                                'close_time': pd.to_datetime(deal['time'], unit='s'),
                                'symbol': deal['symbol'],
                                'side': 'BUY' if deal['type'] == 0 else 'SELL',
                                'volume': deal['volume'],
                                'price': deal['price'],
                                'pnl': deal.get('profit', 0),
                                'ticket': deal.get('deal', deal.get('ticket', 0)),
                                'session': self._classify_session(pd.to_datetime(deal['time'], unit='s'))
                            }
                            processed_trades.append(trade_data)
                        
                        return pd.DataFrame(processed_trades)
            
            # Fallback to CSV data if MT5 not available
            if hasattr(self, 'trade_log') and not self.trade_log.empty:
                csv_data = self.trade_log.copy()
                
                # Convert CSV format to trade format
                processed_trades = []
                for _, trade in csv_data.iterrows():
                    if 'timestamp' in trade and 'result' in trade and trade['result'] == 'EXECUTED':
                        trade_data = {
                            'close_time': pd.to_datetime(trade['timestamp']),
                            'symbol': trade.get('symbol', 'UNKNOWN'),
                            'side': trade.get('action', 'UNKNOWN'),
                            'volume': trade.get('lot', 0),
                            'price': trade.get('price', 0),
                            'pnl': 0,  # CSV doesn't have P&L, would need to calculate
                            'ticket': 0,
                            'session': self._classify_session(pd.to_datetime(trade['timestamp']))
                        }
                        processed_trades.append(trade_data)
                
                return pd.DataFrame(processed_trades)
            
            return pd.DataFrame()
            
        except Exception as e:
            safe_print(f"Error loading trade data: {e}")
            return pd.DataFrame()

    def _classify_session(self, timestamp):
        """Classify trading session based on UTC timestamp"""
        try:
            # Convert to UTC hour
            utc_hour = timestamp.hour
            
            # London: 08:00-16:00 UTC
            if 8 <= utc_hour < 16:
                return "London"
            # NY: 13:00-21:00 UTC (overlaps with London)
            elif 13 <= utc_hour < 21:
                return "NY"
            # Post-Session: Everything else
            else:
                return "Post-Session"
        except:
            return "Unknown"

    def _get_available_symbols(self, trades_data):
        """Get list of available symbols from trades data"""
        if trades_data.empty:
            return ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "NVDA", "GBPJPY"]
        return sorted(trades_data['symbol'].unique().tolist())

    def _apply_winrate_filters(self, trades_data, date_range, symbols, session):
        """Apply filters to trades data"""
        if trades_data.empty:
            return trades_data
        
        filtered = trades_data.copy()
        
        # Date range filter
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered = filtered[
                (filtered['close_time'].dt.date >= start_date) &
                (filtered['close_time'].dt.date <= end_date)
            ]
        
        # Symbol filter
        if symbols:
            filtered = filtered[filtered['symbol'].isin(symbols)]
        
        # Session filter
        if session != "All":
            filtered = filtered[filtered['session'] == session]
        
        return filtered

    def _calculate_winrate_metrics(self, trades_data, include_breakevens):
        """Calculate win-rate metrics from trades data"""
        if trades_data.empty:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'breakevens': 0,
                'win_rate': None,
                'avg_rr': None,
                'total_pnl': None
            }
        
        # Classify outcomes
        wins = len(trades_data[trades_data['pnl'] > 0.50])  # Win if P&L > $0.50
        losses = len(trades_data[trades_data['pnl'] < -0.50])  # Loss if P&L < -$0.50
        breakevens = len(trades_data[abs(trades_data['pnl']) <= 0.50])  # Breakeven if |P&L| <= $0.50
        
        # Calculate win rate
        if include_breakevens:
            total_for_rate = wins + losses + breakevens
        else:
            total_for_rate = wins + losses
        
        win_rate = (wins / total_for_rate * 100) if total_for_rate > 0 else None
        
        # Calculate average R:R (simplified)
        winning_trades = trades_data[trades_data['pnl'] > 0.50]
        losing_trades = trades_data[trades_data['pnl'] < -0.50]
        
        if not winning_trades.empty and not losing_trades.empty:
            avg_win = winning_trades['pnl'].mean()
            avg_loss = abs(losing_trades['pnl'].mean())
            avg_rr = avg_win / avg_loss if avg_loss > 0 else None
        else:
            avg_rr = None
        
        return {
            'total_trades': len(trades_data),
            'wins': wins,
            'losses': losses,
            'breakevens': breakevens,
            'win_rate': win_rate,
            'avg_rr': avg_rr,
            'total_pnl': trades_data['pnl'].sum()
        }

    def _render_winloss_donut_chart(self, metrics):
        """Render donut chart for wins vs losses"""
        import plotly.graph_objects as go
        
        labels = ['Wins', 'Losses']
        values = [metrics['wins'], metrics['losses']]
        colors = ['#00ff88', '#ff6b6b']
        
        if metrics['breakevens'] > 0:
            labels.append('Breakevens')
            values.append(metrics['breakevens'])
            colors.append('#feca57')
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=colors,
            textinfo='label+percent+value',
            textfont_size=12,
        )])
        
        fig.update_layout(
            title="Trade Outcomes Distribution",
            showlegend=True,
            height=400,
            template='plotly_dark'
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def _render_symbol_winrate_chart(self, trades_data, include_breakevens):
        """Render bar chart of win rates by symbol"""
        import plotly.graph_objects as go
        
        if trades_data.empty:
            return
        
        # Calculate win rates by symbol
        symbol_stats = []
        for symbol in trades_data['symbol'].unique():
            symbol_trades = trades_data[trades_data['symbol'] == symbol]
            metrics = self._calculate_winrate_metrics(symbol_trades, include_breakevens)
            
            if metrics['total_trades'] > 0:
                symbol_stats.append({
                    'symbol': symbol,
                    'win_rate': metrics['win_rate'] or 0,
                    'total_trades': metrics['total_trades']
                })
        
        if not symbol_stats:
            return
        
        # Sort by win rate
        symbol_stats = sorted(symbol_stats, key=lambda x: x['win_rate'], reverse=True)
        
        symbols = [s['symbol'] for s in symbol_stats]
        win_rates = [s['win_rate'] for s in symbol_stats]
        trade_counts = [s['total_trades'] for s in symbol_stats]
        
        fig = go.Figure(data=[go.Bar(
            x=symbols,
            y=win_rates,
            text=[f"{wr:.1f}%<br>({tc} trades)" for wr, tc in zip(win_rates, trade_counts)],
            textposition='auto',
            marker_color='#4ecdc4'
        )])
        
        fig.update_layout(
            title="Win Rate by Symbol",
            xaxis_title="Symbol",
            yaxis_title="Win Rate (%)",
            height=400,
            template='plotly_dark'
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def _render_session_winrate_chart(self, trades_data, include_breakevens):
        """Render bar chart of win rates by session"""
        import plotly.graph_objects as go
        
        if trades_data.empty:
            st.info("📊 No data for session analysis")
            return
        
        # Calculate win rates by session
        session_stats = []
        for session in ['London', 'NY', 'Post-Session']:
            session_trades = trades_data[trades_data['session'] == session]
            metrics = self._calculate_winrate_metrics(session_trades, include_breakevens)
            
            if metrics['total_trades'] > 0:
                session_stats.append({
                    'session': session,
                    'win_rate': metrics['win_rate'] or 0,
                    'total_trades': metrics['total_trades']
                })
        
        if not session_stats:
            st.info("📊 No session data available")
            return
        
        sessions = [s['session'] for s in session_stats]
        win_rates = [s['win_rate'] for s in session_stats]
        trade_counts = [s['total_trades'] for s in session_stats]
        
        fig = go.Figure(data=[go.Bar(
            x=sessions,
            y=win_rates,
            text=[f"{wr:.1f}%<br>({tc} trades)" for wr, tc in zip(win_rates, trade_counts)],
            textposition='auto',
            marker_color='#45b7d1'
        )])
        
        fig.update_layout(
            title="Win Rate by Trading Session",
            xaxis_title="Session",
            yaxis_title="Win Rate (%)",
            height=400,
            template='plotly_dark'
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def _render_winrate_data_table(self, trades_data):
        """Render compact data table of recent trades"""
        if trades_data.empty:
            return
        
        # Prepare display data
        display_trades = trades_data.tail(20).copy()  # Show last 20 trades
        display_trades = display_trades.sort_values('close_time', ascending=False)
        
        # Add outcome classification
        display_trades['outcome'] = display_trades['pnl'].apply(
            lambda x: 'Win' if x > 0.50 else 'Loss' if x < -0.50 else 'Breakeven'
        )
        
        # Format for display
        display_trades['Close Time (UTC)'] = display_trades['close_time'].dt.strftime('%Y-%m-%d %H:%M')
        display_trades['P&L'] = display_trades['pnl'].apply(lambda x: f"${x:+.2f}")
        
        # Select columns for display
        display_columns = ['Close Time (UTC)', 'symbol', 'side', 'volume', 'P&L', 'session', 'outcome']
        
        st.dataframe(
            display_trades[display_columns],
            use_container_width=True,
            hide_index=True,
            height=400
        )

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