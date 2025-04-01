"""
Configuration singleton for global access to application configuration.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from config.default_config import get_default_config
from config.logger_utils import get_logger

class ConfigurationSingleton:
    """
    Singleton class for managing global configuration state.
    Ensures only one configuration instance exists throughout the application.
    """
    
    _instance = None
    _config: Dict[str, Any] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigurationSingleton, cls).__new__(cls)
            cls._initialize()
        return cls._instance
    
    @classmethod
    def _initialize(cls) -> None:
        """Initialize the configuration with defaults."""
        if cls._config is None:
            cls._config = get_default_config()
            cls._setup_logging()
    
    @classmethod
    def _setup_logging(cls) -> None:
        """Set up logging based on configuration."""
        if cls._logger is None:
            cls._logger = get_logger(cls._config, "ConfigurationSingleton")
    
    @classmethod
    def get_instance(cls) -> 'ConfigurationSingleton':
        """
        Get the singleton instance.
        
        Returns:
            ConfigurationSingleton instance
        """
        return cls()
    
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
                    self._config.update(loaded_config)
                    self._logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            self._logger.error(f"Error loading config from {config_file}: {str(e)}")
    
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

# Global configuration instance
config = ConfigurationSingleton.get_instance() 
