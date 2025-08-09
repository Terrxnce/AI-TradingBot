# ------------------------------------------------------------------------------------
# 🏦 account_manager.py – Multi-Account Data Architecture Core
#
# Purpose: Manage account sessions, data isolation, and dynamic data source configuration
# for MT5 multi-account trading system. Provides complete account-based data separation.
#
# Features:
# ✅ Account session management with context isolation
# ✅ Dynamic data source configuration per account
# ✅ Account-specific data storage and caching
# ✅ MT5 account switching with data refresh
# ✅ Configuration management per account
# ✅ Data abstraction layer for all components
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Multi-Account Trading System
# ------------------------------------------------------------------------------------

import os
import json
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from pathlib import Path
import shutil
from contextlib import contextmanager
import threading
from dataclasses import dataclass, asdict

@dataclass
class AccountConfig:
    """Account-specific configuration"""
    account_id: str
    account_name: str
    broker: str
    server: str
    login: int
    password: str
    enabled: bool = True
    config_overrides: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config_overrides is None:
            self.config_overrides = {}

class AccountDataManager:
    """Handles account-specific data storage and retrieval"""
    
    def __init__(self, base_data_dir: str = "Data"):
        self.base_data_dir = Path(base_data_dir)
        self.base_data_dir.mkdir(exist_ok=True)
    
    def get_account_data_dir(self, account_id: str) -> Path:
        """Get data directory for specific account"""
        account_dir = self.base_data_dir / f"Account_{account_id}"
        account_dir.mkdir(exist_ok=True)
        return account_dir
    
    def get_account_file_path(self, account_id: str, filename: str) -> Path:
        """Get full path for account-specific file"""
        return self.get_account_data_dir(account_id) / filename
    
    def copy_default_data(self, account_id: str):
        """Copy default data files to new account directory"""
        account_dir = self.get_account_data_dir(account_id)
        default_files = [
            "trade_log.csv",
            "balance_history.csv", 
            "ai_decision_log.jsonl",
            "config.py"
        ]
        
        for filename in default_files:
            source_path = self.base_data_dir.parent / "Data Files" / filename
            if source_path.exists():
                dest_path = account_dir / filename
                if not dest_path.exists():
                    shutil.copy2(source_path, dest_path)
    
    def ensure_account_files(self, account_id: str):
        """Ensure all required files exist for account"""
        account_dir = self.get_account_data_dir(account_id)
        
        # Create empty files if they don't exist
        required_files = {
            "trade_log.csv": "timestamp,symbol,action,lot_size,price,sl,tp,profit,balance,equity,tech_score,ai_confidence,reasoning\n",
            "balance_history.csv": "date,balance,equity\n",
            "ai_decision_log.jsonl": "",
            "trade_state.json": "{}",
            "bot_heartbeat.json": '{"last_heartbeat": null, "status": "offline"}',
            "performance_metrics.json": '{"total_trades": 0, "win_rate": 0, "total_profit": 0}'
        }
        
        for filename, default_content in required_files.items():
            file_path = account_dir / filename
            if not file_path.exists():
                file_path.write_text(default_content)

class MT5AccountConnector:
    """Handles MT5 connections and account switching"""
    
    def __init__(self):
        self.current_account: Optional[AccountConfig] = None
        self._connection_lock = threading.Lock()
    
    def connect_account(self, account_config: AccountConfig) -> bool:
        """Connect to specific MT5 account"""
        with self._connection_lock:
            try:
                # Shutdown any existing connection
                mt5.shutdown()
                
                # Initialize MT5
                if not mt5.initialize():
                    raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
                
                # Login to specific account
                login_result = mt5.login(
                    login=account_config.login,
                    password=account_config.password,
                    server=account_config.server
                )
                
                if not login_result:
                    raise RuntimeError(f"MT5 login failed for account {account_config.account_id}: {mt5.last_error()}")
                
                # Verify connection
                account_info = mt5.account_info()
                if account_info is None:
                    raise RuntimeError("Failed to retrieve account info after login")
                
                self.current_account = account_config
                print(f"✅ Connected to MT5 account {account_config.account_id} ({account_info.login})")
                return True
                
            except Exception as e:
                print(f"❌ Failed to connect to account {account_config.account_id}: {e}")
                self.current_account = None
                return False
    
    def disconnect(self):
        """Disconnect from current MT5 account"""
        with self._connection_lock:
            mt5.shutdown()
            self.current_account = None
            print("📴 MT5 disconnected")
    
    def get_account_info(self) -> Optional[Dict]:
        """Get current account info with safety checks"""
        if self.current_account is None:
            return None
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return None
            
            return {
                'login': account_info.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'currency': account_info.currency
            }
        except Exception as e:
            print(f"❌ Error getting account info: {e}")
            return None

class AccountSessionManager:
    """Manages account sessions and context isolation"""
    
    def __init__(self, accounts_config_file: str = "accounts_config.json"):
        self.accounts_config_file = accounts_config_file
        self.data_manager = AccountDataManager()
        self.mt5_connector = MT5AccountConnector()
        self.current_session: Optional[str] = None
        self.accounts: Dict[str, AccountConfig] = {}
        self.session_data_cache: Dict[str, Dict] = {}
        
        self.load_accounts_config()
    
    def load_accounts_config(self):
        """Load accounts configuration from file"""
        if os.path.exists(self.accounts_config_file):
            try:
                with open(self.accounts_config_file, 'r') as f:
                    config_data = json.load(f)
                
                for account_id, account_data in config_data.items():
                    self.accounts[account_id] = AccountConfig(**account_data)
                
                print(f"✅ Loaded {len(self.accounts)} account configurations")
            except Exception as e:
                print(f"❌ Error loading accounts config: {e}")
        else:
            # Create default config file
            self.create_default_accounts_config()
    
    def create_default_accounts_config(self):
        """Create default accounts configuration"""
        default_accounts = {
            "0001": {
                "account_id": "0001",
                "account_name": "Demo Account 1",
                "broker": "MetaQuotes Software Corp.",
                "server": "MetaQuotes-Demo",
                "login": 0,  # To be configured
                "password": "",  # To be configured
                "enabled": True,
                "config_overrides": {}
            },
            "0002": {
                "account_id": "0002", 
                "account_name": "Demo Account 2",
                "broker": "MetaQuotes Software Corp.",
                "server": "MetaQuotes-Demo",
                "login": 0,  # To be configured
                "password": "",  # To be configured
                "enabled": True,
                "config_overrides": {}
            }
        }
        
        with open(self.accounts_config_file, 'w') as f:
            json.dump(default_accounts, f, indent=2)
        
        print(f"📝 Created default accounts config: {self.accounts_config_file}")
    
    def switch_account(self, account_id: str) -> bool:
        """Switch to different account with complete context isolation"""
        if account_id not in self.accounts:
            print(f"❌ Account {account_id} not found in configuration")
            return False
        
        if not self.accounts[account_id].enabled:
            print(f"❌ Account {account_id} is disabled")
            return False
        
        # Cache current session data if switching
        if self.current_session and self.current_session != account_id:
            self._cache_session_data(self.current_session)
        
        # Connect to new account
        account_config = self.accounts[account_id]
        if not self.mt5_connector.connect_account(account_config):
            return False
        
        # Ensure data files exist for this account
        self.data_manager.ensure_account_files(account_id)
        
        # Load cached data or initialize new session
        self._load_session_data(account_id)
        
        self.current_session = account_id
        print(f"🔄 Switched to account session: {account_id}")
        return True
    
    def _cache_session_data(self, account_id: str):
        """Cache current session data before switching"""
        # Implementation to cache current GUI state, unsaved data, etc.
        self.session_data_cache[account_id] = {
            'cached_at': datetime.now().isoformat(),
            # Add other session data as needed
        }
    
    def _load_session_data(self, account_id: str):
        """Load session data for account"""
        if account_id in self.session_data_cache:
            # Restore cached session data
            pass
    
    def get_current_account_id(self) -> Optional[str]:
        """Get current active account ID"""
        return self.current_session
    
    def get_current_account_config(self) -> Optional[AccountConfig]:
        """Get current account configuration"""
        if self.current_session:
            return self.accounts.get(self.current_session)
        return None
    
    def get_available_accounts(self) -> List[str]:
        """Get list of available account IDs"""
        return [acc_id for acc_id, config in self.accounts.items() if config.enabled]
    
    def add_account(self, account_config: AccountConfig):
        """Add new account configuration"""
        self.accounts[account_config.account_id] = account_config
        self.data_manager.ensure_account_files(account_config.account_id)
        self._save_accounts_config()
    
    def _save_accounts_config(self):
        """Save accounts configuration to file"""
        config_data = {}
        for account_id, config in self.accounts.items():
            config_data[account_id] = asdict(config)
        
        with open(self.accounts_config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    @contextmanager
    def account_context(self, account_id: str):
        """Context manager for temporary account switching"""
        original_account = self.current_session
        try:
            if self.switch_account(account_id):
                yield account_id
            else:
                raise RuntimeError(f"Failed to switch to account {account_id}")
        finally:
            if original_account and original_account != account_id:
                self.switch_account(original_account)

class DataSourceAbstraction:
    """Abstraction layer for all data sources - provides account-specific data access"""
    
    def __init__(self, session_manager: AccountSessionManager):
        self.session_manager = session_manager
    
    def get_trade_log_path(self, account_id: Optional[str] = None) -> str:
        """Get trade log path for specific account"""
        account_id = account_id or self.session_manager.get_current_account_id()
        if not account_id:
            raise RuntimeError("No active account session")
        
        return str(self.session_manager.data_manager.get_account_file_path(account_id, "trade_log.csv"))
    
    def get_balance_history_path(self, account_id: Optional[str] = None) -> str:
        """Get balance history path for specific account"""
        account_id = account_id or self.session_manager.get_current_account_id()
        if not account_id:
            raise RuntimeError("No active account session")
        
        return str(self.session_manager.data_manager.get_account_file_path(account_id, "balance_history.csv"))
    
    def get_ai_decision_log_path(self, account_id: Optional[str] = None) -> str:
        """Get AI decision log path for specific account"""
        account_id = account_id or self.session_manager.get_current_account_id()
        if not account_id:
            raise RuntimeError("No active account session")
        
        return str(self.session_manager.data_manager.get_account_file_path(account_id, "ai_decision_log.jsonl"))
    
    def load_trade_log(self, account_id: Optional[str] = None) -> pd.DataFrame:
        """Load trade log for specific account"""
        try:
            path = self.get_trade_log_path(account_id)
            if os.path.exists(path):
                return pd.read_csv(path)
            else:
                # Return empty DataFrame with correct columns
                return pd.DataFrame(columns=[
                    'timestamp', 'symbol', 'action', 'lot_size', 'price', 
                    'sl', 'tp', 'profit', 'balance', 'equity', 
                    'tech_score', 'ai_confidence', 'reasoning'
                ])
        except Exception as e:
            print(f"❌ Error loading trade log: {e}")
            return pd.DataFrame()
    
    def load_balance_history(self, account_id: Optional[str] = None) -> pd.DataFrame:
        """Load balance history for specific account"""
        try:
            path = self.get_balance_history_path(account_id)
            if os.path.exists(path):
                df = pd.read_csv(path)
                df['date'] = pd.to_datetime(df['date'])
                return df
            else:
                # Return empty DataFrame with correct columns
                return pd.DataFrame(columns=['date', 'balance', 'equity'])
        except Exception as e:
            print(f"❌ Error loading balance history: {e}")
            return pd.DataFrame()
    
    def get_mt5_account_info(self, account_id: Optional[str] = None) -> Optional[Dict]:
        """Get MT5 account info for specific account"""
        if account_id and account_id != self.session_manager.get_current_account_id():
            # Need to switch account context temporarily
            with self.session_manager.account_context(account_id):
                return self.session_manager.mt5_connector.get_account_info()
        else:
            return self.session_manager.mt5_connector.get_account_info()

# Global instance - to be initialized by application
account_session_manager: Optional[AccountSessionManager] = None
data_source: Optional[DataSourceAbstraction] = None

def initialize_account_system():
    """Initialize the global account management system"""
    global account_session_manager, data_source
    
    account_session_manager = AccountSessionManager()
    data_source = DataSourceAbstraction(account_session_manager)
    
    return account_session_manager, data_source

def get_account_manager() -> AccountSessionManager:
    """Get the global account session manager"""
    if account_session_manager is None:
        raise RuntimeError("Account system not initialized. Call initialize_account_system() first.")
    return account_session_manager

def get_data_source() -> DataSourceAbstraction:
    """Get the global data source abstraction"""
    if data_source is None:
        raise RuntimeError("Account system not initialized. Call initialize_account_system() first.")
    return data_source