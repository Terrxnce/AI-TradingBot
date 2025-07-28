# ------------------------------------------------------------------------------------
# 📊 log_utils.py – Enhanced Log Processing for D.E.V.I GUI
#
# This utility provides comprehensive log processing functions for the GUI:
#
# ✅ load_ai_decision_log() – Load and process AI decision logs
# ✅ load_trade_log() – Load and process trade logs  
# ✅ filter_logs() – Advanced filtering capabilities
# ✅ export_data() – Export functionality for CSV/Excel
# ✅ calculate_metrics() – Performance metrics calculation
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot GUI
# ------------------------------------------------------------------------------------

import pandas as pd
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import os

class LogProcessor:
    def __init__(self, ai_log_file: str = None, trade_log_file: str = None):
        if ai_log_file is None:
            # Try multiple possible paths for ai_decision_log.jsonl
            script_dir = os.path.dirname(os.path.dirname(__file__))
            possible_ai_paths = [
                os.path.join(script_dir, "..", "Bot Core", "ai_decision_log.jsonl"),
                os.path.join(script_dir, "..", "Data Files", "ai_decision_log.jsonl"),
                os.path.join(script_dir, "..", "ai_decision_log.jsonl"),
                "ai_decision_log.jsonl"
            ]
            
            for path in possible_ai_paths:
                if os.path.exists(path):
                    ai_log_file = path
                    break
            else:
                ai_log_file = possible_ai_paths[0]  # Default to first path
                
        if trade_log_file is None:
            # Try multiple possible paths for trade_log.csv
            script_dir = os.path.dirname(os.path.dirname(__file__))
            possible_trade_paths = [
                os.path.join(script_dir, "..", "Bot Core", "logs", "trade_log.csv"),
                os.path.join(script_dir, "..", "logs", "trade_log.csv"),
                os.path.join(script_dir, "..", "Data Files", "trade_log.csv"),
                "logs/trade_log.csv"
            ]
            
            for path in possible_trade_paths:
                if os.path.exists(path):
                    trade_log_file = path
                    break
            else:
                trade_log_file = possible_trade_paths[0]  # Default to first path
                
        self.ai_log_file = ai_log_file
        self.trade_log_file = trade_log_file
    
    def load_ai_decision_log(self) -> pd.DataFrame:
        """Load AI decision log with proper formatting and validation"""
        try:
            if not os.path.exists(self.ai_log_file):
                return pd.DataFrame()
            
            # Read JSONL file
            entries = []
            with open(self.ai_log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        # Standardize entry format
                        standardized = self._standardize_ai_entry(entry)
                        entries.append(standardized)
                    except json.JSONDecodeError:
                        continue
            
            if not entries:
                return pd.DataFrame()
            
            df = pd.DataFrame(entries)
            
            # Convert timestamp to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            
            # Sort by timestamp
            df = df.sort_values('timestamp', ascending=False).reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"Error loading AI decision log: {e}")
            return pd.DataFrame()
    
    def _standardize_ai_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize AI log entry format"""
        standardized = {
            'timestamp': entry.get('timestamp', ''),
            'symbol': entry.get('symbol', 'N/A'),
            'ai_decision': entry.get('ai_decision', entry.get('final_direction', 'HOLD')),
            'confidence': entry.get('ai_confidence', entry.get('confidence', 'N/A')),
            'reasoning': entry.get('ai_reasoning', entry.get('reasoning', '')),
            'risk_note': entry.get('ai_risk_note', entry.get('risk_note', '')),
            'technical_score': entry.get('technical_score', 'N/A'),
            'ema_trend': entry.get('ema_trend', 'N/A'),
            'executed': entry.get('executed', False),
            'ai_override': entry.get('ai_override', False),
            'override_reason': entry.get('override_reason', ''),
            'execution_source': entry.get('execution_source', 'AI')
        }
        return standardized
    
    def load_trade_log(self) -> pd.DataFrame:
        """Load trade log with proper formatting"""
        try:
            if not os.path.exists(self.trade_log_file):
                return pd.DataFrame()
            
            df = pd.read_csv(self.trade_log_file)
            
            # Convert timestamp to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            
            # Sort by timestamp
            df = df.sort_values('timestamp', ascending=False).reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"Error loading trade log: {e}")
            return pd.DataFrame()
    
    def filter_ai_log(self, df: pd.DataFrame, **filters) -> pd.DataFrame:
        """Filter AI decision log based on various criteria"""
        if df.empty:
            return df
        
        filtered_df = df.copy()
        
        # Date range filter
        if 'start_date' in filters and filters['start_date']:
            filtered_df = filtered_df[filtered_df['timestamp'] >= pd.to_datetime(filters['start_date'])]
        
        if 'end_date' in filters and filters['end_date']:
            filtered_df = filtered_df[filtered_df['timestamp'] <= pd.to_datetime(filters['end_date'])]
        
        # Symbol filter
        if 'symbols' in filters and filters['symbols']:
            filtered_df = filtered_df[filtered_df['symbol'].isin(filters['symbols'])]
        
        # Decision filter
        if 'decisions' in filters and filters['decisions']:
            filtered_df = filtered_df[filtered_df['ai_decision'].isin(filters['decisions'])]
        
        # Executed only filter
        if 'executed_only' in filters and filters['executed_only']:
            filtered_df = filtered_df[filtered_df['executed'] == True]
        
        # AI override only filter
        if 'override_only' in filters and filters['override_only']:
            filtered_df = filtered_df[filtered_df['ai_override'] == True]
        
        # Confidence range filter
        if 'min_confidence' in filters and filters['min_confidence'] is not None:
            # Handle both string and numeric confidence values
            numeric_confidence = pd.to_numeric(filtered_df['confidence'], errors='coerce')
            filtered_df = filtered_df[numeric_confidence >= filters['min_confidence']]
        
        return filtered_df
    
    def filter_trade_log(self, df: pd.DataFrame, **filters) -> pd.DataFrame:
        """Filter trade log based on various criteria"""
        if df.empty:
            return df
        
        filtered_df = df.copy()
        
        # Date range filter
        if 'start_date' in filters and filters['start_date']:
            filtered_df = filtered_df[filtered_df['timestamp'] >= pd.to_datetime(filters['start_date'])]
        
        if 'end_date' in filters and filters['end_date']:
            # Include the full end date by adding 1 day
            end_datetime = pd.to_datetime(filters['end_date']) + pd.Timedelta(days=1)
            filtered_df = filtered_df[filtered_df['timestamp'] < end_datetime]
        
        # Symbol filter
        if 'symbols' in filters and filters['symbols']:
            filtered_df = filtered_df[filtered_df['symbol'].isin(filters['symbols'])]
        
        # Action/Direction filter (handle both column names)
        if 'actions' in filters and filters['actions']:
            if 'direction' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['direction'].isin(filters['actions'])]
            elif 'action' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['action'].isin(filters['actions'])]
        
        # Result filter
        if 'results' in filters and filters['results']:
            filtered_df = filtered_df[filtered_df['result'].isin(filters['results'])]
        
        return filtered_df
    
    def calculate_ai_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate AI decision metrics"""
        if df.empty:
            return {}
        
        metrics = {
            'total_decisions': len(df),
            'executed_decisions': len(df[df['executed'] == True]),
            'execution_rate': len(df[df['executed'] == True]) / len(df) * 100 if len(df) > 0 else 0,
            'ai_overrides': len(df[df['ai_override'] == True]),
            'override_rate': len(df[df['ai_override'] == True]) / len(df) * 100 if len(df) > 0 else 0,
        }
        
        # Decision distribution
        decision_counts = df['ai_decision'].value_counts().to_dict()
        metrics['decision_distribution'] = decision_counts
        
        # Average confidence
        numeric_confidence = pd.to_numeric(df['confidence'], errors='coerce')
        if not numeric_confidence.isna().all():
            metrics['average_confidence'] = numeric_confidence.mean()
        
        # Symbol distribution
        symbol_counts = df['symbol'].value_counts().to_dict()
        metrics['symbol_distribution'] = symbol_counts
        
        return metrics
    
    def calculate_trade_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate trade performance metrics"""
        if df.empty:
            return {}
        
        metrics = {
            'total_trades': len(df),
            'executed_trades': len(df[df['result'] == 'EXECUTED']) if 'result' in df.columns else len(df)
        }
        
        # Action distribution (handle both column names)
        if 'direction' in df.columns:
            action_counts = df['direction'].value_counts().to_dict()
            metrics['action_distribution'] = action_counts
        elif 'action' in df.columns:
            action_counts = df['action'].value_counts().to_dict()
            metrics['action_distribution'] = action_counts
        
        # Symbol distribution
        symbol_counts = df['symbol'].value_counts().to_dict()
        metrics['symbol_distribution'] = symbol_counts
        
        return metrics
    
    def export_to_csv(self, df: pd.DataFrame, filename: str) -> bool:
        """Export DataFrame to CSV"""
        try:
            df.to_csv(filename, index=False)
            return True
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False
    
    def export_to_excel(self, df: pd.DataFrame, filename: str, sheet_name: str = 'Data') -> bool:
        """Export DataFrame to Excel"""
        try:
            df.to_excel(filename, sheet_name=sheet_name, index=False)
            return True
        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            return False
    
    def get_recent_entries(self, df: pd.DataFrame, hours: int = 24) -> pd.DataFrame:
        """Get entries from the last N hours"""
        if df.empty or 'timestamp' not in df.columns:
            return df
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return df[df['timestamp'] >= cutoff_time]
    
    def get_unique_symbols(self, df: pd.DataFrame) -> List[str]:
        """Get unique symbols from the DataFrame"""
        if df.empty or 'symbol' not in df.columns:
            return []
        
        return sorted(df['symbol'].unique().tolist())
    
    def match_ai_with_trades(self, ai_df: pd.DataFrame, trade_df: pd.DataFrame, 
                           tolerance_minutes: int = 5) -> pd.DataFrame:
        """Match AI decisions with actual trades"""
        if ai_df.empty or trade_df.empty:
            return ai_df
        
        matched_df = ai_df.copy()
        matched_df['trade_matched'] = False
        matched_df['trade_price'] = None
        matched_df['trade_lot'] = None
        
        for idx, ai_row in ai_df.iterrows():
            if pd.isna(ai_row['timestamp']):
                continue
                
            # Find trades within time window for same symbol
            time_window = timedelta(minutes=tolerance_minutes)
            symbol_trades = trade_df[
                (trade_df['symbol'] == ai_row['symbol']) &
                (abs(trade_df['timestamp'] - ai_row['timestamp']) <= time_window)
            ]
            
            if not symbol_trades.empty:
                # Take the closest trade in time
                closest_trade = symbol_trades.loc[
                    (symbol_trades['timestamp'] - ai_row['timestamp']).abs().idxmin()
                ]
                
                matched_df.at[idx, 'trade_matched'] = True
                matched_df.at[idx, 'trade_price'] = closest_trade.get('price', None)
                matched_df.at[idx, 'trade_lot'] = closest_trade.get('lot', None)
        
        return matched_df

# Global instance
log_processor = LogProcessor()