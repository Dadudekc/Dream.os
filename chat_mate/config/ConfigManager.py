"""
Configuration manager for loading, validating, and managing application configuration.
"""

import os
import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path

from config.default_config import get_default_config
from config.logger_utils import get_logger
from config.driver_factory import DriverFactory

class ConfigManager:
    """
    Manages application configuration, including loading from files,
    environment variables, and providing access to configuration values.
    """
    
    def __init__(self, config_name: str = None, config_file: str = "config.json"):
        """
        Initialize ConfigManager with optional config name and file.
        
        Args:
            config_name: Optional name for this configuration instance
            config_file: Path to the config file (default: config.json)
        """
        self.config_name = config_name
        self.config_file = config_file
        self._config = {}
        self.driver_factory = None  # Initialize as None for safe cleanup
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file, creating if necessary."""
        try:
            if os.path.exists(self.config_file):
                if os.path.getsize(self.config_file) > 0:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        self._config = json.load(f)
                else:
                    self._config = {}
                    self._save_config()
            else:
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                self._config = {}
                self._save_config()
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            self._config = {}
    
    def _init_services(self) -> None:
        """Initialize required services."""
        try:
            # Initialize driver factory if webdriver config is present
            if "webdriver" in self._config:
                self.driver_factory = DriverFactory(self._config, self._logger)
        except Exception as e:
            self._logger.error(f"Error initializing services: {str(e)}")
    
    def load_config(self, config_file: str) -> None:
        """
        Load configuration from a file.
        
        Args:
            config_file: Path to configuration file
        """
        try:
            import yaml
            with open(config_file, 'r') as f:
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
            new_config: New configuration to merge
        """
        def merge_dicts(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
            for key, value in update.items():
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    merge_dicts(base[key], value)
                else:
                    base[key] = value
            return base
        
        self._config = merge_dicts(self._config, new_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
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
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        try:
            parts = key.split('.')
            config = self._config
            for part in parts[:-1]:
                config = config.setdefault(part, {})
            config[parts[-1]] = value
            self._logger.debug(f"Set config key '{key}' to {value}")
        except Exception as e:
            self._logger.error(f"Error setting config key '{key}': {str(e)}")
    
    def save_config(self, config_file: Optional[str] = None) -> None:
        """
        Save current configuration to a file.
        
        Args:
            config_file: Optional path to save configuration
        """
        if not config_file:
            config_file = Path(self._config["paths"]["config"]) / "config.yaml"
        
        try:
            import yaml
            with open(config_file, 'w') as f:
                yaml.safe_dump(self._config, f, default_flow_style=False)
            self._logger.info(f"Saved configuration to {config_file}")
        except Exception as e:
            self._logger.error(f"Error saving config to {config_file}: {str(e)}")
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = get_default_config()
        self._logger.info("Reset configuration to defaults")
        self._init_services()
    
    def create_driver(self, headless: Optional[bool] = None) -> Any:
        """
        Create a new WebDriver instance using the driver factory.
        
        Args:
            headless: Override the default headless setting
            
        Returns:
            WebDriver instance
        """
        if not self.driver_factory:
            raise RuntimeError("Driver factory not initialized")
        return self.driver_factory.create_driver(headless)
    
    def get_cached_driver(self, cache_key: str = "default") -> Optional[Any]:
        """
        Get a cached driver instance if available.
        
        Args:
            cache_key: Key to identify the cached driver
            
        Returns:
            Cached WebDriver instance or None
        """
        if not self.driver_factory:
            return None
        return self.driver_factory.get_cached_driver(cache_key)
    
    def clear_driver_cache(self) -> None:
        """Clear all cached driver instances."""
        if self.driver_factory:
            self.driver_factory.clear_cache()
    
    def __del__(self):
        """Safe cleanup of resources."""
        if hasattr(self, "driver_factory") and self.driver_factory:
            try:
                self.clear_driver_cache()
            except Exception as e:
                print(f"Error during ConfigManager cleanup: {str(e)}") 
