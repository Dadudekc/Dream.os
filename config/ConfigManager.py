"""
Configuration manager for handling application settings and configuration.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from config.default_config import get_default_config
from config.logger_utils import get_logger

class ConfigManager:
    """
    Manages application configuration settings.
    """
    
    _instance = None
    
    def __new__(cls, config_name: str = None, config_file: str = None):
        """
        Create or return the singleton instance of ConfigManager.
        
        Args:
            config_name (str): Optional name for this configuration instance
            config_file (str): Path to the config file
        """
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_name: str = None, config_file: str = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_name (str): Optional name for this configuration instance
            config_file (str): Path to the config file
        """
        if self._initialized:
            return
            
        self.config_name = config_name
        self.config_file = config_file or os.path.join(os.getenv('DATA_DIR', './data'), 'config.json')
        self._config = {}
        self._logger = get_logger(__name__)
        self._load_config()
        self._initialized = True
    
    def _load_config(self) -> None:
        """Load configuration from file, creating if necessary."""
        try:
            if os.path.exists(self.config_file):
                if os.path.getsize(self.config_file) > 0:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        self._config = json.load(f)
                else:
                    self._config = get_default_config()
                    self._save_config()
            else:
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                self._config = get_default_config()
                self._save_config()
        except Exception as e:
            self._logger.error(f"Error loading config: {str(e)}")
            self._config = get_default_config()
    
    def _save_config(self) -> None:
        """Save current configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            self._logger.error(f"Error saving config: {str(e)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key (str): Configuration key (supports dot notation)
            default (Any): Default value if key not found
            
        Returns:
            Any: Configuration value or default
        """
        try:
            value = self._config
            for part in key.split('.'):
                value = value.get(part, {})
            return value if value != {} else default
        except Exception as e:
            self._logger.error(f"Error getting config key '{key}': {str(e)}")
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key (str): Configuration key (supports dot notation)
            value (Any): Value to set
        """
        try:
            parts = key.split('.')
            config = self._config
            for part in parts[:-1]:
                config = config.setdefault(part, {})
            config[parts[-1]] = value
            self._save_config()
        except Exception as e:
            self._logger.error(f"Error setting config key '{key}': {str(e)}")
    
    def delete(self, key: str) -> None:
        """
        Delete a configuration value.
        
        Args:
            key (str): Configuration key to delete
        """
        try:
            parts = key.split('.')
            config = self._config
            for part in parts[:-1]:
                config = config.get(part, {})
            if parts[-1] in config:
                del config[parts[-1]]
                self._save_config()
        except Exception as e:
            self._logger.error(f"Error deleting config key '{key}': {str(e)}")
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dict[str, Any]: All configuration values
        """
        return self._config.copy()
    
    def clear(self) -> None:
        """Clear all configuration values and reset to defaults."""
        self._config = get_default_config()
        self._save_config()
    
    def load_yaml_config(self, config_file: str) -> None:
        """
        Load configuration from a YAML file.
        
        Args:
            config_file (str): Path to YAML configuration file
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config:
                    self._merge_config(loaded_config)
                    self._logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            self._logger.error(f"Error loading config from {config_file}: {str(e)}")
    
    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """
        Merge new configuration with existing config.
        
        Args:
            new_config (Dict[str, Any]): New configuration to merge
        """
        def merge_dicts(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
            for key, value in update.items():
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    merge_dicts(base[key], value)
                else:
                    base[key] = value
            return base
        
        self._config = merge_dicts(self._config, new_config)
        self._save_config()
    
    @property
    def config_path(self) -> str:
        """Get the path to the configuration file."""
        return self.config_file 
