"""
log_utils.py - AI Decision Log Processing Utilities

This module provides utility functions for processing and analyzing AI decision logs.
It centralizes common operations like data validation, metric calculations, and formatting.

Author: Enhanced by Claude Sonnet 4
Project: D.E.V.I. Trading Dashboard Enhancement
"""

import pandas as pd
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

def validate_log_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and standardize a single AI decision log entry.
    
    Args:
        entry: Raw log entry dictionary
        
    Returns:
        Validated and standardized entry with proper defaults
    """
    # Define the expected schema with defaults
    schema = {
        'timestamp': None,
        'symbol': 'N/A',
        'ai_decision': 'HOLD',
        'final_direction': None,
        'technical_score': None,
        'ema_trend': None,
        'ai_confidence': None,
        'confidence': None,  # Legacy field
        'ai_reasoning': None,
        'reasoning': None,  # Legacy field
        'ai_risk_note': None,
        'risk_note': None,  # Legacy field
        'executed': False,
        'ai_override': False,
        'override_reason': None,
        'execution_source': 'AI',
        'sl': None,
        'tp': None,
        'execution_block_reason': None
    }
    
    # Start with schema defaults
    validated_entry = schema.copy()
    
    # Update with actual entry data
    for key, value in entry.items():
        if key in validated_entry:
            validated_entry[key] = value
    
    # Apply data type conversions and validations
    
    # Ensure boolean fields are properly typed
    boolean_fields = ['executed', 'ai_override']
    for field in boolean_fields:
        if validated_entry[field] is not None:
            validated_entry[field] = bool(validated_entry[field])
    
    # Ensure numeric fields are properly typed
    numeric_fields = ['technical_score', 'ai_confidence', 'confidence']
    for field in numeric_fields:
        if validated_entry[field] is not None:
            try:
                validated_entry[field] = float(validated_entry[field])
            except (ValueError, TypeError):
                validated_entry[field] = None
    
    # Standardize string fields (remove empty strings, convert to N/A)
    string_fields = ['symbol', 'ai_decision', 'final_direction', 'ema_trend', 
                    'ai_reasoning', 'reasoning', 'ai_risk_note', 'risk_note', 
                    'override_reason', 'execution_source', 'execution_block_reason']
    for field in string_fields:
        if validated_entry[field] is not None:
            val = str(validated_entry[field]).strip()
            if val == '' or val.lower() in ['none', 'nan']:
                validated_entry[field] = None
    
    # Set final_direction from ai_decision if not provided
    if validated_entry['final_direction'] is None:
        validated_entry['final_direction'] = validated_entry['ai_decision']
    
    return validated_entry

def calculate_decision_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate comprehensive metrics from AI decision log DataFrame.
    
    Args:
        df: DataFrame containing AI decision log entries
        
    Returns:
        Dictionary containing calculated metrics
    """
    if df.empty:
        return {
            'total_decisions': 0,
            'total_executed': 0,
            'execution_rate': 0.0,
            'hold_rate': 0.0,
            'buy_rate': 0.0,
            'sell_rate': 0.0,
            'override_rate': 0.0,
            'avg_technical_score': 0.0,
            'avg_ai_confidence': 0.0,
            'confidence_variance': 0.0,
            'symbols_traded': 0
        }
    
    total_decisions = len(df)
    
    # Execution metrics
    executed_count = len(df[df.get('executed', False) == True])
    execution_rate = (executed_count / total_decisions) * 100 if total_decisions > 0 else 0
    
    # Decision type metrics
    final_directions = df.get('final_direction', df.get('ai_decision', pd.Series(['HOLD'] * len(df))))
    hold_count = len(final_directions[final_directions == 'HOLD'])
    buy_count = len(final_directions[final_directions == 'BUY'])
    sell_count = len(final_directions[final_directions == 'SELL'])
    
    hold_rate = (hold_count / total_decisions) * 100
    buy_rate = (buy_count / total_decisions) * 100
    sell_rate = (sell_count / total_decisions) * 100
    
    # Override metrics
    override_count = len(df[df.get('ai_override', False) == True])
    override_rate = (override_count / total_decisions) * 100
    
    # Technical score metrics
    tech_scores = pd.to_numeric(df.get('technical_score', []), errors='coerce').dropna()
    avg_technical_score = tech_scores.mean() if not tech_scores.empty else 0.0
    
    # AI confidence metrics
    ai_conf = pd.to_numeric(df.get('ai_confidence', []), errors='coerce').dropna()
    if ai_conf.empty:
        ai_conf = pd.to_numeric(df.get('confidence', []), errors='coerce').dropna()
    
    avg_ai_confidence = ai_conf.mean() if not ai_conf.empty else 0.0
    confidence_variance = ai_conf.var() if not ai_conf.empty else 0.0
    
    # Symbol diversity
    symbols_traded = len(df['symbol'].unique()) if 'symbol' in df.columns else 0
    
    return {
        'total_decisions': total_decisions,
        'total_executed': executed_count,
        'execution_rate': execution_rate,
        'hold_rate': hold_rate,
        'buy_rate': buy_rate,
        'sell_rate': sell_rate,
        'override_rate': override_rate,
        'avg_technical_score': avg_technical_score,
        'avg_ai_confidence': avg_ai_confidence,
        'confidence_variance': confidence_variance,
        'symbols_traded': symbols_traded
    }

def format_ai_decision_text(ai_decision: Any, final_direction: Any, is_override: bool = False) -> str:
    """
    Format AI decision display text with proper handling of missing values.
    
    Args:
        ai_decision: Original AI decision
        final_direction: Final executed direction
        is_override: Whether this was a technical override
        
    Returns:
        Formatted decision display string
    """
    # Handle AI Decision
    if pd.isna(ai_decision) or str(ai_decision).lower() in ['nan', 'none', '']:
        ai_text = "Not Available"
    else:
        ai_text = str(ai_decision).upper()
    
    # Handle Final Direction
    if pd.isna(final_direction) or str(final_direction).lower() in ['nan', 'none', '']:
        final_text = "HOLD"
    else:
        final_text = str(final_direction).upper()
    
    # Format based on override status
    if is_override:
        return f"AI Decision: {ai_text} → Final Decision: {final_text} (Technical Override)"
    else:
        if ai_text == "Not Available":
            return f"AI Decision: {ai_text} → Final Decision: {final_text}"
        elif ai_text == final_text:
            return f"Final Decision: {final_text}"
        else:
            return f"AI Decision: {ai_text} → Final Decision: {final_text}"

def detect_execution_inconsistencies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect inconsistencies between AI decisions and actual execution status.
    
    Args:
        df: DataFrame containing AI decision log entries
        
    Returns:
        DataFrame containing only entries with potential inconsistencies
    """
    if df.empty:
        return df
    
    inconsistencies = []
    
    for idx, row in df.iterrows():
        issues = []
        
        # Check for missing AI decision but execution occurred
        ai_decision = row.get('ai_decision')
        executed = row.get('executed', False)
        final_direction = row.get('final_direction')
        
        if executed and (pd.isna(ai_decision) or str(ai_decision).upper() == 'HOLD'):
            if final_direction and str(final_direction).upper() in ['BUY', 'SELL']:
                issues.append("Executed trade without AI buy/sell signal")
        
        # Check for AI signal but no execution
        if str(ai_decision).upper() in ['BUY', 'SELL'] and not executed:
            issues.append(f"AI suggested {ai_decision} but trade not executed")
        
        # Check for missing confidence scores
        ai_conf = row.get('ai_confidence')
        conf = row.get('confidence')
        if pd.isna(ai_conf) and pd.isna(conf):
            issues.append("Missing confidence score")
        
        # Check for missing technical score
        tech_score = row.get('technical_score')
        if pd.isna(tech_score):
            issues.append("Missing technical score")
        
        if issues:
            row_copy = row.copy()
            row_copy['detected_issues'] = '; '.join(issues)
            inconsistencies.append(row_copy)
    
    return pd.DataFrame(inconsistencies)

def export_log_summary(df: pd.DataFrame, filename: Optional[str] = None) -> str:
    """
    Export a comprehensive summary of the AI decision log.
    
    Args:
        df: DataFrame containing AI decision log entries
        filename: Optional filename for export
        
    Returns:
        Summary text that can be saved or displayed
    """
    if filename is None:
        filename = f"ai_decision_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    metrics = calculate_decision_metrics(df)
    inconsistencies = detect_execution_inconsistencies(df)
    
    summary = []
    summary.append("=" * 60)
    summary.append("AI DECISION LOG SUMMARY")
    summary.append("=" * 60)
    summary.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary.append(f"Total Entries: {len(df)}")
    summary.append("")
    
    # Basic Metrics
    summary.append("DECISION METRICS:")
    summary.append(f"  Total Decisions: {metrics['total_decisions']}")
    summary.append(f"  Executed Trades: {metrics['total_executed']}")
    summary.append(f"  Execution Rate: {metrics['execution_rate']:.1f}%")
    summary.append(f"  Hold Rate: {metrics['hold_rate']:.1f}%")
    summary.append(f"  Buy Rate: {metrics['buy_rate']:.1f}%")
    summary.append(f"  Sell Rate: {metrics['sell_rate']:.1f}%")
    summary.append(f"  Override Rate: {metrics['override_rate']:.1f}%")
    summary.append("")
    
    # Quality Metrics
    summary.append("QUALITY METRICS:")
    summary.append(f"  Avg Technical Score: {metrics['avg_technical_score']:.1f}")
    summary.append(f"  Avg AI Confidence: {metrics['avg_ai_confidence']:.1f}")
    summary.append(f"  Confidence Variance: {metrics['confidence_variance']:.2f}")
    summary.append(f"  Symbols Traded: {metrics['symbols_traded']}")
    summary.append("")
    
    # Symbol Breakdown
    if 'symbol' in df.columns:
        symbol_counts = df['symbol'].value_counts()
        summary.append("SYMBOL BREAKDOWN:")
        for symbol, count in symbol_counts.head(10).items():
            summary.append(f"  {symbol}: {count} decisions")
        summary.append("")
    
    # Data Quality Issues
    if not inconsistencies.empty:
        summary.append("DATA QUALITY ISSUES:")
        summary.append(f"  Total Issues Found: {len(inconsistencies)}")
        issue_types = {}
        for _, row in inconsistencies.iterrows():
            issues = row.get('detected_issues', '').split('; ')
            for issue in issues:
                if issue:
                    issue_types[issue] = issue_types.get(issue, 0) + 1
        
        for issue, count in issue_types.items():
            summary.append(f"  {issue}: {count} occurrences")
        summary.append("")
    
    # Date Range
    if 'timestamp' in df.columns and not df['timestamp'].empty:
        min_date = df['timestamp'].min()
        max_date = df['timestamp'].max()
        summary.append("DATE RANGE:")
        summary.append(f"  From: {min_date}")
        summary.append(f"  To: {max_date}")
        summary.append(f"  Duration: {(max_date - min_date).days} days")
        summary.append("")
    
    summary.append("=" * 60)
    
    summary_text = '\n'.join(summary)
    
    # Save to file if filename provided
    if filename:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(summary_text)
    
    return summary_text

def load_and_validate_log(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load and validate AI decision log from JSONL file.
    
    Args:
        file_path: Path to the JSONL file
        
    Returns:
        Tuple of (validated DataFrame, validation report)
    """
    validation_report = {
        'total_lines': 0,
        'valid_entries': 0,
        'invalid_entries': 0,
        'errors': []
    }
    
    valid_entries = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        validation_report['total_lines'] = len(lines)
        
        for i, line in enumerate(lines):
            try:
                entry = json.loads(line.strip())
                validated_entry = validate_log_entry(entry)
                valid_entries.append(validated_entry)
                validation_report['valid_entries'] += 1
            except json.JSONDecodeError as e:
                validation_report['invalid_entries'] += 1
                validation_report['errors'].append(f"Line {i+1}: JSON decode error - {str(e)}")
            except Exception as e:
                validation_report['invalid_entries'] += 1
                validation_report['errors'].append(f"Line {i+1}: Validation error - {str(e)}")
        
        df = pd.DataFrame(valid_entries) if valid_entries else pd.DataFrame()
        
        # Convert timestamp column if present
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        return df, validation_report
        
    except FileNotFoundError:
        validation_report['errors'].append(f"File not found: {file_path}")
        return pd.DataFrame(), validation_report
    except Exception as e:
        validation_report['errors'].append(f"Unexpected error: {str(e)}")
        return pd.DataFrame(), validation_report