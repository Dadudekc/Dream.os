import os
import yaml
import json
import threading
from typing import Any, Dict, Optional, List, Union
from pathlib import Path
from datetime import datetime

from core.PathManager import PathManager
from core.interfaces.ILoggingAgent import ILoggingAgent

# Do not import UnifiedLoggingAgent here to avoid circular imports.

class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass

class ConfigManager:
    """
    Centralized configuration management system for ChatMate.
    Features:
    - YAML and JSON config support
    - Environment variable overrides
    - Nested configuration access
    - Configuration validation
    - Hot reload support
    - Configuration change logging
    - Default fallbacks
    """

    # Default configuration schema (you can expand this as needed)
    CONFIG_SCHEMA = {
        "app": {
            "name": str,
            "version": str,
            "debug": bool,
            "log_level": str,
            "max_retries": int,
            "timeout": float
        },
        "ai": {
            "model": str,
            "temperature": float,
            "max_tokens": int,
            "stop_sequences": list,
            "presence_penalty": float,
            "frequency_penalty": float,
            "memory": {
                "max_entries": int,
                "min_score": float,
                "prune_threshold": float,
                "contexts": {
                    "dreamscape": {
                        "max_entries": int,
                        "min_score": float
                    },
                    "workflow": {
                        "max_entries": int,
                        "min_score": float
                    },
                    "social": {
                        "max_entries": int,
                        "min_score": float
                    }
                }
            },
            "reinforcement": {
                "enabled": bool,
                "feedback_types": list,
                "score_weights": dict,
                "learning_rate": float,
                "decay_factor": float,
                "min_samples": int,
                "update_interval": int
            }
        },
        "social": {
            "discord": {
                "token": str,
                "prefix": str,
                "channels": list,
                "allowed_roles": list
            },
            "twitter": {
                "api_key": str,
                "api_secret": str,
                "access_token": str,
                "access_secret": str
            }
        },
        "storage": {
            "base_path": str,
            "max_log_size": int,
            "backup_count": int,
            "compression": bool
        },
        "security": {
            "api_keys": dict,
            "allowed_ips": list,
            "rate_limits": dict
        }
    }

    def __init__(self, logger: ILoggingAgent = None):
        self.logger = logger

    def set_logger(self, logger: ILoggingAgent):
        self.logger = logger

    def __init__(
        self,
        config_name: str = "unified_config.yaml",
        env_prefix: str = "CHATMATE_",
        auto_reload: bool = True
    ):
        """
        Initialize the ConfigManager.
        
        Args:
            config_name: Name of the main config file
            env_prefix: Prefix for environment variables
            auto_reload: Whether to watch for config file changes
        """
        self.config_name = config_name
        self.env_prefix = env_prefix
        self.auto_reload = auto_reload

        # Set up internal state BEFORE creating the logger.
        self._lock = threading.Lock()
        self._last_load_time = None
        self._config_cache: Dict[str, Any] = {}

        # Set up config paths using PathManager
        self.config_dir = PathManager.get_path('configs')
        self.config_path = os.path.join(self.config_dir, config_name)
        os.makedirs(self.config_dir, exist_ok=True)

        # Lazy import to avoid circular dependencies:
        from core.UnifiedLoggingAgent import UnifiedLoggingAgent
        # Pass self as the config service:
        self.logger = UnifiedLoggingAgent(self)

        # Load initial configuration
        self.reload()

        # Start auto-reload if enabled
        if auto_reload:
            self._start_auto_reload()

    def _start_auto_reload(self) -> None:
        """Start the auto-reload thread."""
        def watch_config():
            while True:
                if self._config_changed():
                    self.reload()
                threading.Event().wait(30)  # Check every 30 seconds
        thread = threading.Thread(target=watch_config, daemon=True)
        thread.start()

    def _config_changed(self) -> bool:
        """Check if the config file has been modified."""
        try:
            stat = os.stat(self.config_path)
            return stat.st_mtime > (self._last_load_time or 0)
        except Exception:
            return False

    def reload(self) -> None:
        """Reload configuration from file and apply environment overrides."""
        with self._lock:
            try:
                self._config_cache = self._load_config()
                self._apply_env_overrides()
                self._validate_config()
                self._last_load_time = datetime.now().timestamp()

                self.logger.log_system_event(
                    event_type="config_reload",
                    message=f"Configuration reloaded from {self.config_name}",
                    metadata={"config_path": self.config_path}
                )
            except Exception as e:
                self.logger.log_system_event(
                    event_type="config_error",
                    message=f"Failed to reload configuration: {str(e)}",
                    level="error"
                )
                raise

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not os.path.exists(self.config_path):
            self._create_default_config()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                if self.config_path.endswith('.yaml'):
                    return yaml.safe_load(f) or {}
                elif self.config_path.endswith('.json'):
                    return json.load(f) or {}
        except Exception as e:
            self.logger.log_system_event(
                event_type="config_error",
                message=f"Error loading config file: {str(e)}",
                level="error"
            )
            return {}

    def _create_default_config(self) -> None:
        """Create a default configuration file."""
        default_config = {
            "app": {
                "name": "ChatMate",
                "version": "1.0.0",
                "debug": False,
                "log_level": "INFO",
                "max_retries": 3,
                "timeout": 30.0
            },
            "ai": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
                "stop_sequences": [],
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0,
                "memory": {
                    "max_entries": 10000,
                    "min_score": -0.5,
                    "prune_threshold": 0.8,
                    "contexts": {
                        "dreamscape": {
                            "max_entries": 5000,
                            "min_score": -0.3
                        },
                        "workflow": {
                            "max_entries": 3000,
                            "min_score": -0.4
                        },
                        "social": {
                            "max_entries": 2000,
                            "min_score": -0.5
                        }
                    }
                },
                "reinforcement": {
                    "enabled": True,
                    "feedback_types": ["user", "automated", "metric"],
                    "score_weights": {
                        "user": 1.0,
                        "automated": 0.8,
                        "metric": 0.6
                    },
                    "learning_rate": 0.01,
                    "decay_factor": 0.95,
                    "min_samples": 100,
                    "update_interval": 3600
                }
            },
            "social": {
                "discord": {
                    "token": "",
                    "prefix": "!",
                    "channels": [],
                    "allowed_roles": []
                },
                "twitter": {
                    "api_key": "",
                    "api_secret": "",
                    "access_token": "",
                    "access_secret": ""
                }
            },
            "storage": {
                "base_path": str(PathManager.get_path('data')),
                "max_log_size": 10485760,
                "backup_count": 5,
                "compression": True
            },
            "security": {
                "api_keys": {},
                "allowed_ips": ["127.0.0.1"],
                "rate_limits": {
                    "default": 60,
                    "api": 100
                }
            }
        }

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                if self.config_path.endswith('.yaml'):
                    yaml.safe_dump(default_config, f, default_flow_style=False)
                elif self.config_path.endswith('.json'):
                    json.dump(default_config, f, indent=2)

            self.logger.log_system_event(
                event_type="config_created",
                message=f"Created default configuration at {self.config_path}"
            )
        except Exception as e:
            self.logger.log_system_event(
                event_type="config_error",
                message=f"Failed to create default config: {str(e)}",
                level="error"
            )
            raise

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                config_key = key[len(self.env_prefix):].lower()
                self._set_nested_value(config_key, value)

    def _validate_config(self) -> None:
        """Validate configuration against schema."""
        def validate_dict(schema: Dict, config: Dict, path: str = "") -> None:
            for key, value_type in schema.items():
                full_path = f"{path}.{key}" if path else key

                if key not in config:
                    raise ConfigValidationError(f"Missing required config key: {full_path}")

                if isinstance(value_type, dict):
                    if not isinstance(config[key], dict):
                        raise ConfigValidationError(
                            f"Invalid type for {full_path}: expected dict, got {type(config[key])}"
                        )
                    validate_dict(value_type, config[key], full_path)
                elif not isinstance(config[key], value_type):
                    raise ConfigValidationError(
                        f"Invalid type for {full_path}: expected {value_type}, got {type(config[key])}"
                    )

        try:
            validate_dict(self.CONFIG_SCHEMA, self._config_cache)
        except ConfigValidationError as e:
            self.logger.log_system_event(
                event_type="config_validation",
                message=str(e),
                level="error"
            )
            raise

    def get(self, key: str, default: Any = None, required: bool = False) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Dot-notation key (e.g., "social.discord.token")
            default: Default value if key not found
            required: Whether to raise error if key not found
            
        Returns:
            Configuration value
        """
        try:
            value = self._get_nested_value(key)
            if value is None and required:
                raise KeyError(f"Required config key not found: {key}")
            return value if value is not None else default
        except Exception as e:
            self.logger.log_system_event(
                event_type="config_access",
                message=f"Error accessing config key {key}: {str(e)}",
                level="error"
            )
            if required:
                raise
            return default

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Dot-notation key
            value: Value to set
            persist: Whether to save to file
        """
        with self._lock:
            try:
                self._set_nested_value(key, value)
                if persist:
                    self._save_config()
                self.logger.log_system_event(
                    event_type="config_update",
                    message=f"Updated config key: {key}",
                    metadata={"key": key, "value": str(value)}
                )
            except Exception as e:
                self.logger.log_system_event(
                    event_type="config_error",
                    message=f"Failed to set config key {key}: {str(e)}",
                    level="error"
                )
                raise

    def _get_nested_value(self, key: str) -> Any:
        """Get a nested configuration value using dot notation."""
        current = self._config_cache
        for part in key.split('.'):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    def _set_nested_value(self, key: str, value: Any) -> None:
        """Set a nested configuration value using dot notation."""
        parts = key.split('.')
        current = self._config_cache
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                if self.config_path.endswith('.yaml'):
                    yaml.safe_dump(self._config_cache, f, default_flow_style=False)
                elif self.config_path.endswith('.json'):
                    json.dump(self._config_cache, f, indent=2)
            self.logger.log_system_event(
                event_type="config_saved",
                message=f"Configuration saved to {self.config_path}"
            )
        except Exception as e:
            self.logger.log_system_event(
                event_type="config_error",
                message=f"Failed to save config: {str(e)}",
                level="error"
            )
            raise

    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration."""
        return self._config_cache.copy()

    def reset(self) -> None:
        """Reset configuration to defaults."""
        with self._lock:
            self._create_default_config()
            self.reload()

    def merge(self, config: Dict[str, Any], persist: bool = True) -> None:
        """
        Merge configuration with existing.
        
        Args:
            config: Configuration dict to merge
            persist: Whether to save to file
        """
        def deep_merge(source: Dict, update: Dict) -> Dict:
            for key, value in update.items():
                if key in source and isinstance(source[key], dict) and isinstance(value, dict):
                    deep_merge(source[key], value)
                else:
                    source[key] = value
            return source

        with self._lock:
            self._config_cache = deep_merge(self._config_cache, config)
            if persist:
                self._save_config()
            self.logger.log_system_event(
                event_type="config_merge",
                message="Configuration merged successfully",
                metadata=config
            )

# Singleton wrapper

from typing import Optional, Any, Dict
from core.ConfigManager import ConfigManager

class ConfigurationSingleton:
    """
    Singleton class that provides global access to the ConfigManager.
    Ensures only one instance of the configuration manager exists.
    """
    _instance: Optional['ConfigurationSingleton'] = None
    _config_manager: Optional[ConfigManager] = None

    def __new__(cls) -> 'ConfigurationSingleton':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_manager = ConfigManager()
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'ConfigurationSingleton':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ConfigurationSingleton()
        return cls._instance

    def get(self, key: str, default: Any = None, required: bool = False) -> Any:
        """Get a configuration value."""
        return self._config_manager.get(key, default, required)

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """Set a configuration value."""
        self._config_manager.set(key, value, persist)

    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration."""
        return self._config_manager.get_all()

    def reload(self) -> None:
        """Reload the configuration from disk."""
        self._config_manager.reload()

    def reset(self) -> None:
        """Reset the configuration to defaults."""
        self._config_manager.reset()

    def merge(self, config: Dict[str, Any], persist: bool = True) -> None:
        """Merge configuration with existing."""
        self._config_manager.merge(config, persist)

# Global configuration instance
config = ConfigurationSingleton.get_instance()
