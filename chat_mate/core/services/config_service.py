import os
import json
import logging
from typing import Dict, Any

class ConfigService:
    """
    Service for managing application configuration.
    Handles loading, saving, and accessing configuration values.
    """

    def __init__(self):
        """Initialize the configuration service."""
        self.logger = logging.getLogger(__name__)
        self.config_file = "config.json"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default if not exists."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                return self._create_default_config()
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create and return default configuration."""
        default_config = {
            "max_tokens": 1000,
            "temperature": 70,
            "prompt_types": ["General", "Creative", "Technical"],
            "default_prompts": {
                "General": "You are a helpful assistant.",
                "Creative": "You are a creative writing assistant.",
                "Technical": "You are a technical documentation assistant."
            }
        }
        self._save_config(default_config)
        return default_config

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save to file."""
        self.config[key] = value
        self._save_config(self.config)

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self.config = self._create_default_config()
        self._save_config(self.config) 
