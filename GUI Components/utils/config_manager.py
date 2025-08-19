# ------------------------------------------------------------------------------------
# 🔧 config_manager.py – Safe Config Read/Write Operations
#
# This utility provides thread-safe configuration management for the D.E.V.I trading bot:
#
# ✅ load_config() – Loads current configuration from config.py
# ✅ save_config() – Safely saves configuration with backup
# ✅ create_backup() – Creates timestamped backup files
# ✅ validate_config() – Validates configuration values
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot GUI
# ------------------------------------------------------------------------------------

import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional
import ast
import importlib.util
import sys

class ConfigManager:
    def __init__(self, config_file: str = None, backup_dir: str = "backups"):
        if config_file is None:
            # Find config file in Data Files directory
            script_dir = os.path.dirname(os.path.dirname(__file__))
            config_file = os.path.join(script_dir, "..", "Data Files", "config.py")
        self.config_file = config_file
        self.backup_dir = backup_dir
        self.ensure_backup_dir()
    
    def ensure_backup_dir(self):
        """Ensure backup directory exists"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from config.py file"""
        try:
            # Import config module dynamically
            spec = importlib.util.spec_from_file_location("config", self.config_file)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            # Extract CONFIG and FTMO_PARAMS
            config_data = {
                "CONFIG": getattr(config_module, "CONFIG", {}),
                "FTMO_PARAMS": getattr(config_module, "FTMO_PARAMS", {})
            }
            return config_data
        except Exception as e:
            print(f"Error loading config: {e}")
            return {"CONFIG": {}, "FTMO_PARAMS": {}}
    
    def save_config(self, config_data: Dict[str, Any], create_backup: bool = True) -> bool:
        """Save configuration back to config.py file"""
        try:
            if create_backup:
                self.create_backup()
            
            # Read the original file to preserve comments and structure
            with open(self.config_file, 'r') as f:
                content = f.read()
            
            # Generate new content with updated values
            new_content = self._update_config_content(content, config_data)
            
            # Write back to file
            with open(self.config_file, 'w') as f:
                f.write(new_content)
            
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def _update_config_content(self, content: str, config_data: Dict[str, Any]) -> str:
        """Update the config file content while preserving structure"""
        lines = content.split('\n')
        new_lines = []
        in_config_block = False
        in_ftmo_block = False
        config_indent = ""
        ftmo_indent = ""
        
        for line in lines:
            stripped = line.strip()
            
            # Detect start of CONFIG block
            if stripped.startswith('CONFIG = {'):
                in_config_block = True
                config_indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(line)
                # Add updated CONFIG content
                new_lines.extend(self._format_dict_content(config_data.get("CONFIG", {}), config_indent + "    "))
                continue
            
            # Detect start of FTMO_PARAMS block
            elif stripped.startswith('FTMO_PARAMS = {'):
                in_ftmo_block = True
                ftmo_indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(line)
                # Add updated FTMO_PARAMS content
                new_lines.extend(self._format_dict_content(config_data.get("FTMO_PARAMS", {}), ftmo_indent + "    "))
                continue
            
            # Detect end of blocks
            elif in_config_block and stripped == '}':
                in_config_block = False
                new_lines.append(line)
                continue
            elif in_ftmo_block and stripped == '}':
                in_ftmo_block = False
                new_lines.append(line)
                continue
            
            # Skip lines inside config blocks (they'll be replaced)
            elif in_config_block or in_ftmo_block:
                continue
            
            # Keep all other lines
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def _format_dict_content(self, data: Dict[str, Any], indent: str) -> list:
        """Format dictionary content for config file"""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f'{indent}"{key}": {{')
                for sub_key, sub_value in value.items():
                    lines.append(f'{indent}    "{sub_key}": {repr(sub_value)},')
                lines.append(f'{indent}}},')
            else:
                lines.append(f'{indent}"{key}": {repr(value)},')
        return lines
    
    def create_backup(self) -> str:
        """Create a timestamped backup of the current config"""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        backup_filename = f"config_backup_{timestamp}.py"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            shutil.copy2(self.config_file, backup_path)
            return backup_path
        except Exception as e:
            print(f"Error creating backup: {e}")
            return ""
    
    def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, list]:
        """Validate configuration values"""
        errors = []
        
        config = config_data.get("CONFIG", {})
        ftmo = config_data.get("FTMO_PARAMS", {})
        
        # Validate required CONFIG fields
        required_fields = [
            "sl_pips", "tp_pips", "lot_size",
            "partial_close_trigger_percent", "full_close_trigger_percent"
        ]
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(config[field], (int, float)):
                errors.append(f"Field {field} must be numeric")
        
        # Validate tech_scoring section
        tech_scoring = config.get("tech_scoring", {})
        if "min_score_for_trade" not in tech_scoring:
            errors.append("Missing required field: tech_scoring.min_score_for_trade")
        elif not isinstance(tech_scoring.get("min_score_for_trade", 0), (int, float)):
            errors.append("Field tech_scoring.min_score_for_trade must be numeric")
        
        # Validate specific ranges
        min_score = tech_scoring.get("min_score_for_trade", 0)
        if min_score < 0 or min_score > 8:
            errors.append("tech_scoring.min_score_for_trade must be between 0 and 8")
        
        if config.get("lot_size", 0) <= 0:
            errors.append("lot_size must be positive")
        
        # Validate FTMO parameters
        if ftmo.get("initial_balance", 0) <= 0:
            errors.append("initial_balance must be positive")
        
        return len(errors) == 0, errors
    
    def get_backup_list(self) -> list:
        """Get list of available backup files"""
        try:
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("config_backup_") and filename.endswith(".py"):
                    filepath = os.path.join(self.backup_dir, filename)
                    timestamp = os.path.getmtime(filepath)
                    backups.append({
                        "filename": filename,
                        "path": filepath,
                        "timestamp": datetime.fromtimestamp(timestamp)
                    })
            return sorted(backups, key=lambda x: x["timestamp"], reverse=True)
        except Exception as e:
            print(f"Error getting backup list: {e}")
            return []

# Global instance
config_manager = ConfigManager()