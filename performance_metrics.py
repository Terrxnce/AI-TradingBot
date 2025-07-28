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
        """Load trade data from logs"""
        try:
            # Load trade log
            trade_log_path = "logs/trade_log.csv"
            if os.path.exists(trade_log_path):
                trades_df = pd.read_csv(trade_log_path)
                trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
                return trades_df
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"❌ Error loading trade data: {e}")
            return pd.DataFrame()
    
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
                'win_rate': 0,
                'profit_factor': 0,
                'average_trade': 0,
                'total_profit': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'risk_adjusted_return': 0
            }
        
        # Basic metrics
        total_trades = len(trades_df)
        win_rate = self.calculate_win_rate(trades_df)
        profit_factor = self.calculate_profit_factor(trades_df)
        average_trade = self.calculate_average_trade(trades_df)
        total_profit = trades_df['profit'].sum() if 'profit' in trades_df.columns else 0
        
        # Calculate equity curve for drawdown
        if 'profit' in trades_df.columns:
            equity_curve = trades_df['profit'].cumsum() + FTMO_PARAMS['initial_balance']
            max_drawdown = self.calculate_max_drawdown(equity_curve)
            
            # Calculate returns for Sharpe ratio
            returns = trades_df['profit'] / FTMO_PARAMS['initial_balance']
            sharpe_ratio = self.calculate_sharpe_ratio(returns)
            risk_adjusted_return = self.calculate_risk_adjusted_return(trades_df, FTMO_PARAMS['initial_balance'])
        else:
            max_drawdown = 0
            sharpe_ratio = 0
            risk_adjusted_return = 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'average_trade': average_trade,
            'total_profit': total_profit,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'risk_adjusted_return': risk_adjusted_return
        }
    
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

# Global instance
performance_metrics = PerformanceMetrics()

def print_performance_summary():
    """Print performance summary to console"""
    print(performance_metrics.get_performance_summary())

def generate_full_report():
    """Generate and return full performance report"""
    return performance_metrics.generate_performance_report() 