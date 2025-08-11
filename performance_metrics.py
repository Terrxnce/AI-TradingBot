#!/usr/bin/env python3
"""
Performance Metrics System for AI Trading Bot
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
from config import CONFIG, FTMO_PARAMS

class PerformanceMetrics:
    def __init__(self):
        self.metrics_file = "performance_metrics.json"
        self.trade_history = []
        self.daily_metrics = {}
        
    def calculate_sharpe_ratio(self, returns, risk_free_rate=0.02):
        """Calculate Sharpe ratio"""
        if len(returns) == 0:
            return 0
        
        excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
        if np.std(excess_returns) == 0:
            return 0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    
    def calculate_max_drawdown(self, equity_curve):
        """Calculate maximum drawdown"""
        if len(equity_curve) == 0:
            return 0
        
        peak = equity_curve.expanding(min_periods=1).max()
        drawdown = (equity_curve - peak) / peak
        return drawdown.min()
    
    def calculate_win_rate(self, trades_df):
        """Calculate win rate"""
        if len(trades_df) == 0:
            return 0
        
        # Check if 'profit' column exists
        if 'profit' not in trades_df.columns:
            return 0
        
        winning_trades = trades_df[trades_df['profit'] > 0]
        return len(winning_trades) / len(trades_df)
    
    def calculate_profit_factor(self, trades_df):
        """Calculate profit factor"""
        if len(trades_df) == 0:
            return 0
        
        # Check if 'profit' column exists
        if 'profit' not in trades_df.columns:
            return 0
        
        winning_trades = trades_df[trades_df['profit'] > 0]
        losing_trades = trades_df[trades_df['profit'] < 0]
        
        total_profit = winning_trades['profit'].sum() if len(winning_trades) > 0 else 0
        total_loss = abs(losing_trades['profit'].sum()) if len(losing_trades) > 0 else 0
        
        return total_profit / total_loss if total_loss > 0 else float('inf')
    
    def calculate_average_trade(self, trades_df):
        """Calculate average trade profit/loss"""
        if len(trades_df) == 0:
            return 0
        
        # Check if 'profit' column exists
        if 'profit' not in trades_df.columns:
            return 0
        
        return trades_df['profit'].mean()
    
    def calculate_risk_adjusted_return(self, trades_df, initial_balance):
        """Calculate risk-adjusted return"""
        if len(trades_df) == 0:
            return 0
        
        # Check if 'profit' column exists
        if 'profit' not in trades_df.columns:
            return 0
        
        total_return = trades_df['profit'].sum()
        volatility = trades_df['profit'].std()
        
        if volatility == 0:
            return 0
        
        return total_return / volatility
    
    def load_trade_data(self):
        """Load trade data from logs and MT5 history"""
        try:
            # First try to load from CSV trade log
            from shared.settings import get_current_user_paths
            user_paths = get_current_user_paths()
            possible_paths = []
            if user_paths:
                possible_paths.append(os.fspath(user_paths["logs"] / "trade_log.csv"))
            possible_paths += [
                "logs/trade_log.csv",
                "Bot Core/logs/trade_log.csv", 
                "Data Files/trade_log.csv"
            ]
            
            csv_trades = None
            for trade_log_path in possible_paths:
                if os.path.exists(trade_log_path):
                    csv_trades = pd.read_csv(trade_log_path)
                    csv_trades['timestamp'] = pd.to_datetime(csv_trades['timestamp'])
                    print(f"✅ Loaded trade data from: {trade_log_path}")
                    break
            
            if csv_trades is None:
                print("⚠️ No trade log found in expected locations")
                return pd.DataFrame()
            
            # Always get MT5 data to ensure we have profit information
            print("🔄 Fetching MT5 trade history for profit data...")
            mt5_trades = self._get_mt5_trade_history()
            
            if not mt5_trades.empty:
                # Instead of trying to match, let's use MT5 data directly
                # Filter for actual trades (BUY/SELL) with profit
                actual_mt5_trades = mt5_trades[mt5_trades['profit'] != 0].copy()
                
                if not actual_mt5_trades.empty:
                    print(f"✅ Found {len(actual_mt5_trades)} MT5 trades with profit data")
                    
                    # Create a clean trade log from MT5 data
                    trade_data = []
                    for _, trade in actual_mt5_trades.iterrows():
                        trade_entry = {
                            "timestamp": trade['timestamp'],
                            "symbol": trade['symbol'],
                            "direction": trade['direction'],
                            "lot": trade['volume'],
                            "sl": 0,  # MT5 doesn't provide SL/TP in deals
                            "tp": 0,
                            "entry_price": trade['price'],
                            "profit": trade['profit'],
                            "result": "EXECUTED"
                        }
                        trade_data.append(trade_entry)
                    
                    result_df = pd.DataFrame(trade_data)
                    total_profit = result_df['profit'].sum()
                    print(f"✅ Total P&L from MT5: ${total_profit:.2f}")
                    
                    return result_df
                else:
                    print("⚠️ No MT5 trades with profit data found")
                    return csv_trades
            else:
                print("⚠️ No MT5 trade history available")
                return csv_trades
                
        except Exception as e:
            print(f"❌ Error loading trade data: {e}")
            return pd.DataFrame()
    
    def _get_mt5_trade_history(self):
        """Get trade history from MT5"""
        try:
            import MetaTrader5 as mt5
            if not mt5.initialize():
                return pd.DataFrame()
            
            # Get deals for a reasonable historical window
            utc_from = datetime.now() - timedelta(days=90)
            utc_to = datetime.now()
            deals = mt5.history_deals_get(utc_from, utc_to)
            mt5.shutdown()

            if not deals:
                return pd.DataFrame()

            # Convert to DataFrame and normalize columns
            deals_df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
            if deals_df.empty:
                return pd.DataFrame()
            deals_df['timestamp'] = pd.to_datetime(deals_df['time'], unit='s')
            deals_df['direction'] = deals_df['type'].apply(lambda x: "BUY" if x == 0 else "SELL")
            deals_df = deals_df.sort_values('timestamp', ascending=False)
            return deals_df
            
        except Exception as e:
            print(f"❌ Error getting MT5 trade history: {e}")
            return pd.DataFrame()
    
    def _merge_with_mt5_data(self, csv_trades, mt5_trades):
        """Merge CSV trade data with MT5 profit data"""
        try:
            if mt5_trades.empty:
                print("⚠️ No MT5 trades to merge")
                return csv_trades
            
            print(f"🔄 Merging {len(csv_trades)} CSV trades with {len(mt5_trades)} MT5 trades")
            
            # Create a merged dataframe with profit data
            merged_trades = []
            
            for _, csv_trade in csv_trades.iterrows():
                # Find matching MT5 trade by timestamp and direction
                # Use a time tolerance of 5 minutes for matching
                csv_time = csv_trade['timestamp']
                time_tolerance = pd.Timedelta(minutes=5)
                
                matching_mt5 = mt5_trades[
                    (abs(mt5_trades['timestamp'] - csv_time) <= time_tolerance) &
                    (mt5_trades['direction'] == csv_trade['direction'])
                ]
                
                if not matching_mt5.empty:
                    mt5_trade = matching_mt5.iloc[0]
                    trade_data = csv_trade.to_dict()
                    trade_data['profit'] = mt5_trade['profit']
                    trade_data['volume'] = mt5_trade['volume']
                    merged_trades.append(trade_data)
                    print(f"✅ Matched trade: {csv_trade['direction']} at {csv_time}, Profit: ${mt5_trade['profit']:.2f}")
                else:
                    # Keep original trade without profit data
                    trade_data = csv_trade.to_dict()
                    trade_data['profit'] = 0
                    merged_trades.append(trade_data)
                    print(f"⚠️ No MT5 match for: {csv_trade['direction']} at {csv_time}")
            
            result_df = pd.DataFrame(merged_trades)
            total_profit = result_df['profit'].sum()
            print(f"✅ Total P&L after merge: ${total_profit:.2f}")
            
            return result_df
            
        except Exception as e:
            print(f"❌ Error merging trade data: {e}")
            return csv_trades
    
    def calculate_daily_metrics(self, trades_df):
        """Calculate daily performance metrics"""
        if trades_df.empty:
            return {}
        
        # Group by date
        trades_df['date'] = trades_df['timestamp'].dt.date
        daily_groups = trades_df.groupby('date')
        
        daily_metrics = {}
        for date, group in daily_groups:
            daily_metrics[str(date)] = {
                'trades': len(group),
                'profit': group['profit'].sum() if 'profit' in group.columns else 0,
                'wins': len(group[group['profit'] > 0]) if 'profit' in group.columns else 0,
                'losses': len(group[group['profit'] < 0]) if 'profit' in group.columns else 0,
                'win_rate': len(group[group['profit'] > 0]) / len(group) if 'profit' in group.columns else 0
            }
        
        return daily_metrics
    
    def calculate_overall_metrics(self, trades_df):
        """Calculate overall performance metrics"""
        if trades_df.empty:
            return {
                'total_trades': 0,
                'executed_trades': 0,
                'execution_rate': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'average_trade': 0,
                'total_profit': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'risk_adjusted_return': 0,
                'avg_lot_size': 0,
                'most_traded_symbol': 'N/A',
                'most_active_session': 'N/A'
            }
        
        total_trades = len(trades_df)
        
        # Execution metrics
        executed_trades = trades_df[trades_df['result'] == 'EXECUTED'] if 'result' in trades_df.columns else trades_df
        execution_rate = len(executed_trades) / total_trades if total_trades > 0 else 0
        
        # Symbol analysis
        most_traded_symbol = trades_df['symbol'].mode().iloc[0] if 'symbol' in trades_df.columns and not trades_df['symbol'].empty else 'N/A'
        
        # Session analysis
        if 'timestamp' in trades_df.columns:
            trades_df['hour'] = trades_df['timestamp'].dt.hour
            trades_df['session'] = trades_df['hour'].apply(self._get_session)
            most_active_session = trades_df['session'].mode().iloc[0] if not trades_df['session'].empty else 'N/A'
        else:
            most_active_session = 'N/A'
        
        # Lot size analysis - use volume from MT5 if available
        if 'volume' in trades_df.columns:
            avg_lot_size = trades_df['volume'].mean()
        elif 'lot' in trades_df.columns:
            avg_lot_size = trades_df['lot'].mean()
        else:
            avg_lot_size = 0
        
        # Since we don't have profit data, set these to 0
        win_rate = 0
        profit_factor = 0
        average_trade = 0
        total_profit = 0
        max_drawdown = 0
        sharpe_ratio = 0
        risk_adjusted_return = 0
        
        return {
            'total_trades': total_trades,
            'executed_trades': len(executed_trades),
            'execution_rate': execution_rate,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'average_trade': average_trade,
            'total_profit': total_profit,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'risk_adjusted_return': risk_adjusted_return,
            'avg_lot_size': avg_lot_size,
            'most_traded_symbol': most_traded_symbol,
            'most_active_session': most_active_session
        }
    
    def _get_session(self, hour):
        """Helper function to get session from hour"""
        if 1 <= hour < 7:
            return 'Asia'
        elif 8 <= hour < 12:
            return 'London'
        elif 13 <= hour < 14:
            return 'NY_PreMarket'
        elif 14 <= hour < 20:
            return 'New_York'
        else:
            return 'Post_Market'
    
    def calculate_symbol_performance(self, trades_df):
        """Calculate performance by symbol"""
        if trades_df.empty or 'symbol' not in trades_df.columns:
            return {}
        
        symbol_metrics = {}
        for symbol in trades_df['symbol'].unique():
            symbol_trades = trades_df[trades_df['symbol'] == symbol]
            
            symbol_metrics[symbol] = {
                'trades': len(symbol_trades),
                'profit': symbol_trades['profit'].sum() if 'profit' in symbol_trades.columns else 0,
                'win_rate': self.calculate_win_rate(symbol_trades),
                'average_trade': self.calculate_average_trade(symbol_trades)
            }
        
        return symbol_metrics
    
    def calculate_session_performance(self, trades_df):
        """Calculate performance by trading session"""
        if trades_df.empty:
            return {}
        
        # Add session information
        trades_df['hour'] = trades_df['timestamp'].dt.hour
        
        def get_session(hour):
            if 1 <= hour < 7:
                return 'Asia'
            elif 8 <= hour < 12:
                return 'London'
            elif 13 <= hour < 14:
                return 'NY_PreMarket'
            elif 14 <= hour < 20:
                return 'New_York'
            else:
                return 'Post_Market'
        
        trades_df['session'] = trades_df['hour'].apply(get_session)
        
        session_metrics = {}
        for session in trades_df['session'].unique():
            session_trades = trades_df[trades_df['session'] == session]
            
            session_metrics[session] = {
                'trades': len(session_trades),
                'profit': session_trades['profit'].sum() if 'profit' in session_trades.columns else 0,
                'win_rate': self.calculate_win_rate(session_trades),
                'average_trade': self.calculate_average_trade(session_trades)
            }
        
        return session_metrics
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        trades_df = self.load_trade_data()
        
        if trades_df.empty:
            return {
                'status': 'No trade data available',
                'overall_metrics': {},
                'daily_metrics': {},
                'symbol_metrics': {},
                'session_metrics': {},
                'generated_at': datetime.now().isoformat()
            }
        
        report = {
            'overall_metrics': self.calculate_overall_metrics(trades_df),
            'daily_metrics': self.calculate_daily_metrics(trades_df),
            'symbol_metrics': self.calculate_symbol_performance(trades_df),
            'session_metrics': self.calculate_session_performance(trades_df),
            'generated_at': datetime.now().isoformat()
        }
        
        # Save report
        with open(self.metrics_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report
    
    def get_performance_summary(self):
        """Get quick performance summary"""
        trades_df = self.load_trade_data()
        
        if trades_df.empty:
            return "No trade data available"
        
        metrics = self.calculate_overall_metrics(trades_df)
        
        summary = f"""
📊 Performance Summary:
├── Total Trades: {metrics['total_trades']}
├── Win Rate: {metrics['win_rate']:.1%}
├── Profit Factor: {metrics['profit_factor']:.2f}
├── Average Trade: ${metrics['average_trade']:.2f}
├── Total Profit: ${metrics['total_profit']:.2f}
├── Max Drawdown: {metrics['max_drawdown']:.1%}
├── Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
└── Risk-Adjusted Return: {metrics['risk_adjusted_return']:.2f}
"""
        return summary

    def get_mt5_account_balance(self, account_id: str = None):
        """Get current account balance directly from MT5 for specific account"""
        try:
            # Try to use account-aware system if available
            try:
                from account_manager import get_data_source
                data_source = get_data_source()
                account_info = data_source.get_mt5_account_info(account_id)
                if account_info:
                    return account_info.get('balance')
            except ImportError:
                pass
            
            # Fallback to direct MT5 access
            import MetaTrader5 as mt5
            if not mt5.initialize():
                return None
            
            account_info = mt5.account_info()
            mt5.shutdown()
            
            if account_info is None:
                return None
            
            return account_info.balance
            
        except Exception as e:
            print(f"❌ Error getting MT5 account balance: {e}")
            return None
    
    def get_mt5_account_equity(self, account_id: str = None):
        """Get current account equity directly from MT5 for specific account"""
        try:
            # Try to use account-aware system if available
            try:
                from account_manager import get_data_source
                data_source = get_data_source()
                account_info = data_source.get_mt5_account_info(account_id)
                if account_info:
                    return account_info.get('equity')
            except ImportError:
                pass
            
            # Fallback to direct MT5 access
            import MetaTrader5 as mt5
            if not mt5.initialize():
                return None
            
            account_info = mt5.account_info()
            mt5.shutdown()
            
            if account_info is None:
                return None
            
            return account_info.equity
            
        except Exception as e:
            print(f"❌ Error getting MT5 account equity: {e}")
            return None

# Global instance
performance_metrics = PerformanceMetrics()

def print_performance_summary():
    """Print performance summary to console"""
    print(performance_metrics.get_performance_summary())

def generate_full_report():
    """Generate and return full performance report"""
    return performance_metrics.generate_performance_report() 