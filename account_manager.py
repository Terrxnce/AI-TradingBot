"""
Account Management System for D.E.V.I Trading Bot

This module provides account session management functionality including:
- Account configuration management
- Session initialization
- Default account setup

Author: Terrence Ndifor (Terry)
Project: D.E.V.I Trading Bot
"""

import os
import json
import sys
from typing import Dict, Any, Optional, Tuple
from datetime import datetime


class AccountSessionManager:
    """Manages account sessions and configurations for the trading bot."""
    
    def __init__(self):
        """Initialize the account session manager."""
        self.accounts_config_file = os.path.join(os.path.dirname(__file__), "accounts_config.json")
        self.accounts_config = {}
        self.load_accounts_config()
    
    def load_accounts_config(self):
        """Load accounts configuration from file or create default if not exists."""
        try:
            if os.path.exists(self.accounts_config_file):
                with open(self.accounts_config_file, 'r') as f:
                    self.accounts_config = json.load(f)
                print(f"✅ Loaded accounts config from: {self.accounts_config_file}")
            else:
                print(f"⚠️ Accounts config not found. Creating default...")
                self.create_default_accounts_config()
        except Exception as e:
            print(f"❌ Error loading accounts config: {e}")
            print(f"📝 Creating default accounts config...")
            self.create_default_accounts_config()
    
    def create_default_accounts_config(self):
        """Create default accounts configuration."""
        try:
            default_config = {
                "accounts": {
                    "demo": {
                        "type": "demo",
                        "balance": 10000,
                        "currency": "USD",
                        "leverage": 100,
                        "active": True,
                        "created_at": datetime.now().isoformat()
                    },
                    "live": {
                        "type": "live", 
                        "balance": 0,
                        "currency": "USD",
                        "leverage": 100,
                        "active": False,
                        "created_at": datetime.now().isoformat()
                    }
                },
                "current_account": "demo",
                "settings": {
                    "auto_backup": True,
                    "backup_interval": "daily",
                    "max_backup_files": 30
                },
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.accounts_config_file), exist_ok=True)
            
            # Save default config
            with open(self.accounts_config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            
            self.accounts_config = default_config
            print(f"📝 Created default accounts config: {self.accounts_config_file}")
            
        except Exception as e:
            print(f"❌ Error creating default accounts config: {e}")
            # Fallback to minimal config
            self.accounts_config = {
                "accounts": {"demo": {"type": "demo", "active": True}},
                "current_account": "demo"
            }
    
    def get_current_account(self) -> Dict[str, Any]:
        """Get the currently active account configuration."""
        current_account_name = self.accounts_config.get("current_account", "demo")
        return self.accounts_config.get("accounts", {}).get(current_account_name, {})
    
    def set_current_account(self, account_name: str) -> bool:
        """Set the current active account."""
        if account_name in self.accounts_config.get("accounts", {}):
            self.accounts_config["current_account"] = account_name
            self.save_accounts_config()
            return True
        return False
    
    def save_accounts_config(self):
        """Save the current accounts configuration to file."""
        try:
            with open(self.accounts_config_file, 'w') as f:
                json.dump(self.accounts_config, f, indent=4)
            print(f"💾 Saved accounts config to: {self.accounts_config_file}")
        except Exception as e:
            print(f"❌ Error saving accounts config: {e}")
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get information about the current account."""
        current_account = self.get_current_account()
        return {
            "account_type": current_account.get("type", "demo"),
            "balance": current_account.get("balance", 0),
            "currency": current_account.get("currency", "USD"),
            "leverage": current_account.get("leverage", 100),
            "active": current_account.get("active", False)
        }


class DataSource:
    """Simple data source placeholder for compatibility."""
    
    def __init__(self):
        """Initialize data source."""
        self.connected = False
        self.last_update = None
    
    def connect(self) -> bool:
        """Connect to data source."""
        try:
            # Placeholder for actual data source connection
            self.connected = True
            self.last_update = datetime.now()
            print("📊 Data source connected successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to data source: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from data source."""
        self.connected = False
        print("📊 Data source disconnected")
    
    def is_connected(self) -> bool:
        """Check if data source is connected."""
        return self.connected


def initialize_account_system() -> Tuple[AccountSessionManager, DataSource]:
    """
    Initialize the account management system.
    
    Returns:
        Tuple[AccountSessionManager, DataSource]: Account manager and data source instances
    """
    try:
        print("🔧 Initializing account management system...")
        
        # Initialize account session manager
        account_manager = AccountSessionManager()
        
        # Initialize data source
        data_source = DataSource()
        data_source.connect()
        
        print("✅ Account management system initialized successfully")
        return account_manager, data_source
        
    except Exception as e:
        print(f"❌ Failed to initialize account system: {e}")
        # Return minimal working instances
        account_manager = AccountSessionManager()
        data_source = DataSource()
        return account_manager, data_source


# Convenience functions for external use
def get_account_manager() -> AccountSessionManager:
    """Get a new instance of AccountSessionManager."""
    return AccountSessionManager()


def get_data_source() -> DataSource:
    """Get a new instance of DataSource."""
    return DataSource()


if __name__ == "__main__":
    # Test the account manager
    print("🧪 Testing Account Manager...")
    account_manager, data_source = initialize_account_system()
    
    print("\n📊 Current Account Info:")
    account_info = account_manager.get_account_info()
    for key, value in account_info.items():
        print(f"  {key}: {value}")
    
    print(f"\n🔌 Data Source Connected: {data_source.is_connected()}")