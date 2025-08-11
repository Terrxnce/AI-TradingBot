import os
import json
from typing import Dict, Any, Tuple
from datetime import datetime

class AccountSessionManager:
    def __init__(self):
        self.accounts_config_file = os.path.join(os.path.dirname(__file__), "accounts_config.json")
        self.accounts_config = {}
        self.load_accounts_config()

    def load_accounts_config(self):
        try:
            if os.path.exists(self.accounts_config_file):
                with open(self.accounts_config_file, 'r', encoding='utf-8') as f:
                    self.accounts_config = json.load(f)
            else:
                self.create_default_accounts_config()
        except:
            self.create_default_accounts_config()

    def create_default_accounts_config(self):
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
                    }
                },
                "current_account": "demo",
                "settings": {"auto_backup": True},
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }
            os.makedirs(os.path.dirname(self.accounts_config_file), exist_ok=True)
            with open(self.accounts_config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            self.accounts_config = default_config
        except:
            self.accounts_config = {
                "accounts": {"demo": {"type": "demo", "active": True}},
                "current_account": "demo"
            }

    def get_current_account(self) -> Dict[str, Any]:
        current_account_name = self.accounts_config.get("current_account", "demo")
        return self.accounts_config.get("accounts", {}).get(current_account_name, {})

    def get_account_info(self) -> Dict[str, Any]:
        current_account = self.get_current_account()
        return {
            "account_type": current_account.get("type", "demo"),
            "balance": current_account.get("balance", 10000),
            "currency": current_account.get("currency", "USD"),
            "leverage": current_account.get("leverage", 100),
            "active": current_account.get("active", True)
        }

class DataSource:
    def __init__(self):
        self.connected = True
        self.last_update = datetime.now()

    def connect(self) -> bool:
        self.connected = True
        return True

    def is_connected(self) -> bool:
        return self.connected

def initialize_account_system() -> Tuple[AccountSessionManager, DataSource]:
    account_manager = AccountSessionManager()
    data_source = DataSource()
    return account_manager, data_source