# ------------------------------------------------------------------------------------
# 📊 account_chart_manager.py – Account-Specific Chart Configuration Management
#
# Purpose: Manages chart configurations, saved views, and custom indicators per account.
# Provides complete isolation of chart settings between different MT5 accounts.
#
# Features:
# ✅ Account-specific chart configurations
# ✅ Saved chart views and layouts
# ✅ Custom indicator settings per account
# ✅ Chart timeframe preferences
# ✅ Symbol watchlists per account
# ✅ Drawing tools and annotations
# ✅ Color schemes and themes
# ✅ Export/import chart configurations
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Multi-Account Trading System
# ------------------------------------------------------------------------------------

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
import copy

@dataclass
class ChartIndicator:
    """Chart indicator configuration"""
    name: str
    type: str  # 'trend', 'oscillator', 'volume', 'volatility'
    parameters: Dict[str, Any]
    color: str = "#0066CC"
    style: str = "solid"  # 'solid', 'dashed', 'dotted'
    enabled: bool = True

@dataclass
class ChartView:
    """Saved chart view configuration"""
    name: str
    symbol: str
    timeframe: str
    indicators: List[ChartIndicator]
    zoom_level: float = 1.0
    price_range: Optional[Dict[str, float]] = None
    annotations: List[Dict] = None
    created_at: str = ""
    last_modified: str = ""
    
    def __post_init__(self):
        if self.annotations is None:
            self.annotations = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.last_modified = datetime.now().isoformat()

@dataclass
class AccountChartConfig:
    """Complete chart configuration for an account"""
    account_id: str
    default_timeframe: str = "H1"
    default_indicators: List[ChartIndicator] = None
    symbol_watchlist: List[str] = None
    saved_views: Dict[str, ChartView] = None
    color_scheme: Dict[str, str] = None
    chart_preferences: Dict[str, Any] = None
    custom_drawings: Dict[str, List[Dict]] = None
    
    def __post_init__(self):
        if self.default_indicators is None:
            self.default_indicators = []
        if self.symbol_watchlist is None:
            self.symbol_watchlist = ["EURUSD", "GBPUSD", "USDJPY"]
        if self.saved_views is None:
            self.saved_views = {}
        if self.color_scheme is None:
            self.color_scheme = self._get_default_colors()
        if self.chart_preferences is None:
            self.chart_preferences = self._get_default_preferences()
        if self.custom_drawings is None:
            self.custom_drawings = {}
    
    def _get_default_colors(self) -> Dict[str, str]:
        """Get default color scheme"""
        return {
            "background": "#1E1E1E",
            "grid": "#333333",
            "candle_up": "#00FF88",
            "candle_down": "#FF4444",
            "volume": "#666666",
            "ma_fast": "#FFD700",
            "ma_slow": "#FF6B6B",
            "rsi": "#4ECDC4",
            "macd": "#45B7D1"
        }
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default chart preferences"""
        return {
            "show_volume": True,
            "show_grid": True,
            "show_crosshair": True,
            "candlestick_style": "candles",  # 'candles', 'bars', 'line'
            "timezone": "UTC",
            "auto_scale": True,
            "show_last_value": True,
            "chart_type": "financial"
        }

class AccountChartManager:
    """Manages chart configurations for multiple accounts"""
    
    def __init__(self, base_config_dir: str = "Data"):
        self.base_config_dir = Path(base_config_dir)
        self.base_config_dir.mkdir(exist_ok=True)
        
        # Cache for loaded configurations
        self.account_configs: Dict[str, AccountChartConfig] = {}
        
        # Default indicators available
        self.default_indicators = self._get_default_indicators()
    
    def _get_default_indicators(self) -> List[ChartIndicator]:
        """Get list of default indicators"""
        return [
            ChartIndicator(
                name="MA_20",
                type="trend",
                parameters={"period": 20, "method": "simple"},
                color="#FFD700"
            ),
            ChartIndicator(
                name="MA_50",
                type="trend", 
                parameters={"period": 50, "method": "simple"},
                color="#FF6B6B"
            ),
            ChartIndicator(
                name="RSI",
                type="oscillator",
                parameters={"period": 14, "overbought": 70, "oversold": 30},
                color="#4ECDC4"
            ),
            ChartIndicator(
                name="MACD",
                type="oscillator",
                parameters={"fast": 12, "slow": 26, "signal": 9},
                color="#45B7D1"
            ),
            ChartIndicator(
                name="Bollinger_Bands",
                type="volatility",
                parameters={"period": 20, "deviation": 2},
                color="#9B59B6"
            )
        ]
    
    def get_account_config_dir(self, account_id: str) -> Path:
        """Get configuration directory for specific account"""
        config_dir = self.base_config_dir / f"Account_{account_id}" / "charts"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def load_account_config(self, account_id: str) -> AccountChartConfig:
        """Load chart configuration for specific account"""
        if account_id in self.account_configs:
            return self.account_configs[account_id]
        
        config_dir = self.get_account_config_dir(account_id)
        config_file = config_dir / "chart_config.json"
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Convert indicator data back to ChartIndicator objects
                if 'default_indicators' in config_data:
                    indicators = []
                    for ind_data in config_data['default_indicators']:
                        indicators.append(ChartIndicator(**ind_data))
                    config_data['default_indicators'] = indicators
                
                # Convert saved views
                if 'saved_views' in config_data:
                    views = {}
                    for view_name, view_data in config_data['saved_views'].items():
                        if 'indicators' in view_data:
                            view_indicators = []
                            for ind_data in view_data['indicators']:
                                view_indicators.append(ChartIndicator(**ind_data))
                            view_data['indicators'] = view_indicators
                        views[view_name] = ChartView(**view_data)
                    config_data['saved_views'] = views
                
                config = AccountChartConfig(**config_data)
            else:
                # Create default configuration
                config = AccountChartConfig(
                    account_id=account_id,
                    default_indicators=copy.deepcopy(self.default_indicators)
                )
                self.save_account_config(config)
            
            self.account_configs[account_id] = config
            return config
            
        except Exception as e:
            print(f"❌ Error loading chart config for account {account_id}: {e}")
            # Return default config
            config = AccountChartConfig(
                account_id=account_id,
                default_indicators=copy.deepcopy(self.default_indicators)
            )
            self.account_configs[account_id] = config
            return config
    
    def save_account_config(self, config: AccountChartConfig):
        """Save chart configuration for account"""
        config_dir = self.get_account_config_dir(config.account_id)
        config_file = config_dir / "chart_config.json"
        
        try:
            # Convert to serializable format
            config_dict = asdict(config)
            
            # Convert ChartIndicator objects to dicts
            if 'default_indicators' in config_dict:
                config_dict['default_indicators'] = [
                    asdict(ind) for ind in config.default_indicators
                ]
            
            # Convert saved views
            if 'saved_views' in config_dict:
                views_dict = {}
                for view_name, view in config.saved_views.items():
                    view_dict = asdict(view)
                    view_dict['indicators'] = [asdict(ind) for ind in view.indicators]
                    views_dict[view_name] = view_dict
                config_dict['saved_views'] = views_dict
            
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            print(f"✅ Saved chart config for account {config.account_id}")
            
        except Exception as e:
            print(f"❌ Error saving chart config for account {config.account_id}: {e}")
    
    def add_indicator(self, account_id: str, indicator: ChartIndicator):
        """Add indicator to account's default indicators"""
        config = self.load_account_config(account_id)
        
        # Check if indicator already exists
        existing_names = [ind.name for ind in config.default_indicators]
        if indicator.name in existing_names:
            # Update existing indicator
            for i, ind in enumerate(config.default_indicators):
                if ind.name == indicator.name:
                    config.default_indicators[i] = indicator
                    break
        else:
            # Add new indicator
            config.default_indicators.append(indicator)
        
        self.save_account_config(config)
    
    def remove_indicator(self, account_id: str, indicator_name: str):
        """Remove indicator from account's default indicators"""
        config = self.load_account_config(account_id)
        config.default_indicators = [
            ind for ind in config.default_indicators 
            if ind.name != indicator_name
        ]
        self.save_account_config(config)
    
    def save_chart_view(self, account_id: str, view: ChartView):
        """Save a chart view for account"""
        config = self.load_account_config(account_id)
        config.saved_views[view.name] = view
        self.save_account_config(config)
    
    def load_chart_view(self, account_id: str, view_name: str) -> Optional[ChartView]:
        """Load a saved chart view"""
        config = self.load_account_config(account_id)
        return config.saved_views.get(view_name)
    
    def delete_chart_view(self, account_id: str, view_name: str):
        """Delete a saved chart view"""
        config = self.load_account_config(account_id)
        if view_name in config.saved_views:
            del config.saved_views[view_name]
            self.save_account_config(config)
    
    def get_symbol_watchlist(self, account_id: str) -> List[str]:
        """Get symbol watchlist for account"""
        config = self.load_account_config(account_id)
        return config.symbol_watchlist
    
    def update_symbol_watchlist(self, account_id: str, symbols: List[str]):
        """Update symbol watchlist for account"""
        config = self.load_account_config(account_id)
        config.symbol_watchlist = symbols
        self.save_account_config(config)
    
    def add_symbol_to_watchlist(self, account_id: str, symbol: str):
        """Add symbol to watchlist"""
        config = self.load_account_config(account_id)
        if symbol not in config.symbol_watchlist:
            config.symbol_watchlist.append(symbol)
            self.save_account_config(config)
    
    def remove_symbol_from_watchlist(self, account_id: str, symbol: str):
        """Remove symbol from watchlist"""
        config = self.load_account_config(account_id)
        if symbol in config.symbol_watchlist:
            config.symbol_watchlist.remove(symbol)
            self.save_account_config(config)
    
    def update_color_scheme(self, account_id: str, color_scheme: Dict[str, str]):
        """Update color scheme for account"""
        config = self.load_account_config(account_id)
        config.color_scheme.update(color_scheme)
        self.save_account_config(config)
    
    def get_chart_preferences(self, account_id: str) -> Dict[str, Any]:
        """Get chart preferences for account"""
        config = self.load_account_config(account_id)
        return config.chart_preferences
    
    def update_chart_preferences(self, account_id: str, preferences: Dict[str, Any]):
        """Update chart preferences for account"""
        config = self.load_account_config(account_id)
        config.chart_preferences.update(preferences)
        self.save_account_config(config)
    
    def save_custom_drawing(self, account_id: str, symbol: str, drawing_data: Dict):
        """Save custom drawing/annotation for symbol"""
        config = self.load_account_config(account_id)
        if symbol not in config.custom_drawings:
            config.custom_drawings[symbol] = []
        
        drawing_data['id'] = len(config.custom_drawings[symbol])
        drawing_data['timestamp'] = datetime.now().isoformat()
        config.custom_drawings[symbol].append(drawing_data)
        self.save_account_config(config)
    
    def get_custom_drawings(self, account_id: str, symbol: str) -> List[Dict]:
        """Get custom drawings for symbol"""
        config = self.load_account_config(account_id)
        return config.custom_drawings.get(symbol, [])
    
    def delete_custom_drawing(self, account_id: str, symbol: str, drawing_id: int):
        """Delete custom drawing"""
        config = self.load_account_config(account_id)
        if symbol in config.custom_drawings:
            config.custom_drawings[symbol] = [
                drawing for drawing in config.custom_drawings[symbol]
                if drawing.get('id') != drawing_id
            ]
            self.save_account_config(config)
    
    def export_account_config(self, account_id: str, export_path: str):
        """Export account chart configuration to file"""
        config = self.load_account_config(account_id)
        
        # Convert to serializable format
        export_data = {
            'account_id': account_id,
            'export_timestamp': datetime.now().isoformat(),
            'config': asdict(config)
        }
        
        # Convert indicators
        if 'default_indicators' in export_data['config']:
            export_data['config']['default_indicators'] = [
                asdict(ind) for ind in config.default_indicators
            ]
        
        # Convert saved views
        if 'saved_views' in export_data['config']:
            views_dict = {}
            for view_name, view in config.saved_views.items():
                view_dict = asdict(view)
                view_dict['indicators'] = [asdict(ind) for ind in view.indicators]
                views_dict[view_name] = view_dict
            export_data['config']['saved_views'] = views_dict
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✅ Exported chart config for account {account_id} to {export_path}")
    
    def import_account_config(self, account_id: str, import_path: str):
        """Import account chart configuration from file"""
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            config_data = import_data['config']
            config_data['account_id'] = account_id  # Override account ID
            
            # Convert indicators
            if 'default_indicators' in config_data:
                indicators = []
                for ind_data in config_data['default_indicators']:
                    indicators.append(ChartIndicator(**ind_data))
                config_data['default_indicators'] = indicators
            
            # Convert saved views
            if 'saved_views' in config_data:
                views = {}
                for view_name, view_data in config_data['saved_views'].items():
                    if 'indicators' in view_data:
                        view_indicators = []
                        for ind_data in view_data['indicators']:
                            view_indicators.append(ChartIndicator(**ind_data))
                        view_data['indicators'] = view_indicators
                    views[view_name] = ChartView(**view_data)
                config_data['saved_views'] = views
            
            config = AccountChartConfig(**config_data)
            self.account_configs[account_id] = config
            self.save_account_config(config)
            
            print(f"✅ Imported chart config for account {account_id} from {import_path}")
            
        except Exception as e:
            print(f"❌ Error importing chart config: {e}")
    
    def copy_config_between_accounts(self, source_account_id: str, target_account_id: str):
        """Copy chart configuration from one account to another"""
        source_config = self.load_account_config(source_account_id)
        
        # Create deep copy and update account ID
        target_config_data = asdict(source_config)
        target_config_data['account_id'] = target_account_id
        
        # Recreate objects
        if 'default_indicators' in target_config_data:
            target_config_data['default_indicators'] = copy.deepcopy(source_config.default_indicators)
        
        if 'saved_views' in target_config_data:
            target_config_data['saved_views'] = copy.deepcopy(source_config.saved_views)
        
        target_config = AccountChartConfig(**target_config_data)
        self.account_configs[target_account_id] = target_config
        self.save_account_config(target_config)
        
        print(f"📋 Copied chart config from account {source_account_id} to {target_account_id}")

# Global instance
chart_manager: Optional[AccountChartManager] = None

def get_chart_manager() -> AccountChartManager:
    """Get the global chart manager"""
    global chart_manager
    if chart_manager is None:
        chart_manager = AccountChartManager()
    return chart_manager

def initialize_chart_manager() -> AccountChartManager:
    """Initialize the global chart manager"""
    global chart_manager
    chart_manager = AccountChartManager()
    return chart_manager