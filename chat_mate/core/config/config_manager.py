import os
import json
from pathlib import Path
from typing import Union, Any, Optional

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self._config = {}
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value, validating and converting paths if applicable.
        
        Args:
            key: The configuration key
            default: Default value if key not found
            
        Returns:
            The configuration value, with paths converted to strings
        """
        value = self._config.get(key, default)
        
        # Handle path-like values
        if key.endswith('_path') or key.endswith('_dir') or key.endswith('_file'):
            return self._ensure_valid_path(key, value)
        
        return value

    def _ensure_valid_path(self, key: str, value: Any) -> str:
        """
        Ensure a value is a valid path string.
        
        Args:
            key: The configuration key
            value: The value to validate
            
        Returns:
            A string representation of the path
            
        Raises:
            TypeError: If the value cannot be converted to a valid path
        """
        if value is None:
            return ""
            
        # Handle Path objects
        if isinstance(value, Path):
            return str(value)
            
        # Handle strings
        if isinstance(value, str):
            return value
            
        # Handle objects with get_path method
        if hasattr(value, 'get_path'):
            return str(value.get_path())
            
        # Try to convert to string
        try:
            return str(value)
        except Exception as e:
            raise TypeError(f"Configuration value for '{key}' cannot be converted to a path: {str(e)}")

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value, validating paths if applicable.
        
        Args:
            key: The configuration key
            value: The value to set
        """
        if key.endswith('_path') or key.endswith('_dir') or key.endswith('_file'):
            value = self._ensure_valid_path(key, value)
        
        self._config[key] = value
        self._save_config()

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

    def _save_config(self):
        """Save configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {str(e)}")

    def get_path(self) -> str:
        """Get the path to the config file."""
        return self.config_file 
