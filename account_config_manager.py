# ------------------------------------------------------------------------------------
# ⚙️ account_config_manager.py – Multi-Account Configuration Management
#
# Purpose: Provides account-specific configuration management that maintains 
# compatibility with existing code while adding multi-account support.
#
# Features:
# ✅ Account-specific config overrides
# ✅ Fallback to global config for unspecified settings
# ✅ Dynamic config switching based on active account
# ✅ Backward compatibility with existing CONFIG usage
# ✅ Account-specific FTMO parameters
# ✅ Real-time config updates per account
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Multi-Account Trading System
# ------------------------------------------------------------------------------------

import os
import json
import copy
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Import original config as base template
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), 'Data Files'))
    from config import CONFIG as BASE_CONFIG, FTMO_PARAMS as BASE_FTMO_PARAMS
except ImportError:
    # Fallback default config
    BASE_CONFIG = {
        "min_score_for_trade": 6,
        "sl_pips": 50,
        "tp_pips": 100,
        "lot_size": 1.25,
        "use_engulfing": True,
        "use_bos": True,
        "use_liquidity_sweep": True
    }
    BASE_FTMO_PARAMS = {
        "initial_balance": 10_000,
        "max_daily_loss_pct": 0.05,
        "max_total_loss_pct": 0.10,
        "profit_target_pct": 0.10,
        "min_trading_days": 4
    }

class AccountConfigManager:
    """Manages account-specific configurations with fallback to global defaults"""
    
    def __init__(self, accounts_config_dir: str = "Data"):
        self.accounts_config_dir = Path(accounts_config_dir)
        self.accounts_config_dir.mkdir(exist_ok=True)
        
        # Cache for loaded configs
        self.account_configs: Dict[str, Dict[str, Any]] = {}
        self.account_ftmo_params: Dict[str, Dict[str, Any]] = {}
        
        # Current active account
        self.current_account_id: Optional[str] = None
        
        # Global defaults
        self.base_config = copy.deepcopy(BASE_CONFIG)
        self.base_ftmo_params = copy.deepcopy(BASE_FTMO_PARAMS)
    
    def set_active_account(self, account_id: str):
        """Set the currently active account for config access"""
        self.current_account_id = account_id
        self._ensure_account_config_files(account_id)
    
    def _ensure_account_config_files(self, account_id: str):
        """Ensure account-specific config files exist"""
        account_config_dir = self.accounts_config_dir / f"Account_{account_id}"
        account_config_dir.mkdir(exist_ok=True)
        
        # Create account-specific config file if it doesn't exist
        config_file = account_config_dir / "account_config.json"
        if not config_file.exists():
            default_account_config = {
                "config_overrides": {},
                "ftmo_overrides": {},
                "last_updated": None
            }
            with open(config_file, 'w') as f:
                json.dump(default_account_config, f, indent=2)
    
    def load_account_config(self, account_id: str) -> Dict[str, Any]:
        """Load configuration for specific account"""
        if account_id in self.account_configs:
            return self.account_configs[account_id]
        
        self._ensure_account_config_files(account_id)
        
        config_file = self.accounts_config_dir / f"Account_{account_id}" / "account_config.json"
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    account_data = json.load(f)
                
                # Merge with base config
                merged_config = copy.deepcopy(self.base_config)
                if "config_overrides" in account_data:
                    merged_config.update(account_data["config_overrides"])
                
                self.account_configs[account_id] = merged_config
                
                # Load FTMO params
                merged_ftmo = copy.deepcopy(self.base_ftmo_params)
                if "ftmo_overrides" in account_data:
                    merged_ftmo.update(account_data["ftmo_overrides"])
                
                self.account_ftmo_params[account_id] = merged_ftmo
                
                return merged_config
            else:
                # Use base config as fallback
                self.account_configs[account_id] = copy.deepcopy(self.base_config)
                self.account_ftmo_params[account_id] = copy.deepcopy(self.base_ftmo_params)
                return self.account_configs[account_id]
                
        except Exception as e:
            print("❌ Error loading config for account " + str(account_id) + ": " + str(e))
            # Fallback to base config
            self.account_configs[account_id] = copy.deepcopy(self.base_config)
            self.account_ftmo_params[account_id] = copy.deepcopy(self.base_ftmo_params)
            return self.account_configs[account_id]
    
    def get_config(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for account (current account if not specified)"""
        account_id = account_id or self.current_account_id
        if not account_id:
            return self.base_config
        
        if account_id not in self.account_configs:
            self.load_account_config(account_id)
        
        return self.account_configs[account_id]
    
    def get_ftmo_params(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Get FTMO parameters for account (current account if not specified)"""
        account_id = account_id or self.current_account_id
        if not account_id:
            return self.base_ftmo_params
        
        if account_id not in self.account_ftmo_params:
            self.load_account_config(account_id)
        
        return self.account_ftmo_params[account_id]
    
    def update_account_config(self, account_id: str, config_updates: Dict[str, Any], 
                            ftmo_updates: Optional[Dict[str, Any]] = None):
        """Update configuration for specific account"""
        self._ensure_account_config_files(account_id)
        
        config_file = self.accounts_config_dir / f"Account_{account_id}" / "account_config.json"
        
        try:
            # Load existing config
            if config_file.exists():
                with open(config_file, 'r') as f:
                    account_data = json.load(f)
            else:
                account_data = {"config_overrides": {}, "ftmo_overrides": {}}
            
            # Update overrides
            account_data["config_overrides"].update(config_updates)
            if ftmo_updates:
                account_data["ftmo_overrides"].update(ftmo_updates)
            
            account_data["last_updated"] = datetime.now().isoformat()
            
            # Save updated config
            with open(config_file, 'w') as f:
                json.dump(account_data, f, indent=2)
            
            # Update cached config
            if account_id in self.account_configs:
                self.account_configs[account_id].update(config_updates)
            
            if account_id in self.account_ftmo_params and ftmo_updates:
                self.account_ftmo_params[account_id].update(ftmo_updates)
            
            print("✅ Updated config for account " + str(account_id))
            
        except Exception as e:
            print("❌ Error updating config for account " + str(account_id) + ": " + str(e))
    
    def get_config_value(self, key: str, account_id: Optional[str] = None, default: Any = None) -> Any:
        """Get specific config value for account"""
        config = self.get_config(account_id)
        return config.get(key, default)
    
    def get_ftmo_value(self, key: str, account_id: Optional[str] = None, default: Any = None) -> Any:
        """Get specific FTMO parameter value for account"""
        ftmo_params = self.get_ftmo_params(account_id)
        return ftmo_params.get(key, default)
    
    def reset_account_config(self, account_id: str):
        """Reset account configuration to global defaults"""
        self._ensure_account_config_files(account_id)
        
        config_file = self.accounts_config_dir / f"Account_{account_id}" / "account_config.json"
        
        reset_config = {
            "config_overrides": {},
            "ftmo_overrides": {},
            "last_updated": datetime.now().isoformat()
        }
        
        with open(config_file, 'w') as f:
            json.dump(reset_config, f, indent=2)
        
        # Clear cache
        if account_id in self.account_configs:
            del self.account_configs[account_id]
        if account_id in self.account_ftmo_params:
            del self.account_ftmo_params[account_id]
        
        print("🔄 Reset config for account " + str(account_id) + " to defaults")
    
    def copy_config_to_account(self, source_account_id: str, target_account_id: str):
        """Copy configuration from one account to another"""
        source_config = self.get_config(source_account_id)
        source_ftmo = self.get_ftmo_params(source_account_id)
        
        # Get only the overrides (differences from base)
        config_overrides = {}
        for key, value in source_config.items():
            if key not in self.base_config or self.base_config[key] != value:
                config_overrides[key] = value
        
        ftmo_overrides = {}
        for key, value in source_ftmo.items():
            if key not in self.base_ftmo_params or self.base_ftmo_params[key] != value:
                ftmo_overrides[key] = value
        
        self.update_account_config(target_account_id, config_overrides, ftmo_overrides)
        print("📋 Copied config from account " + str(source_account_id) + " to " + str(target_account_id))

# Global instance for backward compatibility
config_manager: Optional[AccountConfigManager] = None

def initialize_config_manager() -> AccountConfigManager:
    """Initialize the global config manager"""
    global config_manager
    config_manager = AccountConfigManager()
    return config_manager

def get_config_manager() -> AccountConfigManager:
    """Get the global config manager"""
    if config_manager is None:
        return initialize_config_manager()
    return config_manager

# Backward compatibility functions that work with current account
def get_current_config() -> Dict[str, Any]:
    """Get config for currently active account"""
    return get_config_manager().get_config()

def get_current_ftmo_params() -> Dict[str, Any]:
    """Get FTMO params for currently active account"""
    return get_config_manager().get_ftmo_params()

# Dynamic CONFIG and FTMO_PARAMS that update based on active account
class DynamicConfig:
    """Dynamic configuration that updates based on active account"""
    
    def __init__(self, config_manager: AccountConfigManager):
        self.config_manager = config_manager
    
    def __getitem__(self, key):
        return self.config_manager.get_config_value(key)
    
    def __setitem__(self, key, value):
        if self.config_manager.current_account_id:
            self.config_manager.update_account_config(
                self.config_manager.current_account_id, 
                {key: value}
            )
    
    def get(self, key, default=None):
        return self.config_manager.get_config_value(key, default=default)
    
    def update(self, other_dict):
        if self.config_manager.current_account_id:
            self.config_manager.update_account_config(
                self.config_manager.current_account_id,
                other_dict
            )
    
    def keys(self):
        return self.config_manager.get_config().keys()
    
    def values(self):
        return self.config_manager.get_config().values()
    
    def items(self):
        return self.config_manager.get_config().items()

class DynamicFTMOParams:
    """Dynamic FTMO parameters that update based on active account"""
    
    def __init__(self, config_manager: AccountConfigManager):
        self.config_manager = config_manager
    
    def __getitem__(self, key):
        return self.config_manager.get_ftmo_value(key)
    
    def __setitem__(self, key, value):
        if self.config_manager.current_account_id:
            self.config_manager.update_account_config(
                self.config_manager.current_account_id,
                {},
                {key: value}
            )
    
    def get(self, key, default=None):
        return self.config_manager.get_ftmo_value(key, default=default)
    
    def update(self, other_dict):
        if self.config_manager.current_account_id:
            self.config_manager.update_account_config(
                self.config_manager.current_account_id,
                {},
                other_dict
            )
    
    def keys(self):
        return self.config_manager.get_ftmo_params().keys()
    
    def values(self):
        return self.config_manager.get_ftmo_params().values()
    
    def items(self):
        return self.config_manager.get_ftmo_params().items()

# Create dynamic instances for backward compatibility
def get_dynamic_config():
    """Get dynamic CONFIG that updates with account switching"""
    manager = get_config_manager()
    return DynamicConfig(manager)

def get_dynamic_ftmo_params():
    """Get dynamic FTMO_PARAMS that updates with account switching"""
    manager = get_config_manager()
    return DynamicFTMOParams(manager)

# For backward compatibility - these will be updated when account switches
CONFIG = get_dynamic_config()
FTMO_PARAMS = get_dynamic_ftmo_params()