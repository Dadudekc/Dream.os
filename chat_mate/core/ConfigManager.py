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
            "timeout": float,
            "headless": bool,
            "reverse_order": bool,
            "archive_enabled": bool
        },
        "ai": {
            "model": str,
            "temperature": float,
            "max_tokens": int,
            "stop_sequences": list,
            "presence_penalty": float,
            "frequency_penalty": float,
            "chatgpt_url": str,
            "custom_gpt_url": str,
            "prompt_input_selector": str,
            "response_container_selector": str,
            "stop_button_xpath": str,
            "retry_attempts": int,
            "retry_delay_seconds": int,
            "excluded_chats": list,
            "prompt_cycle": list,
            "agent_name": str,
            "agent_mode": str,
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
                "enabled": bool,
                "token": str,
                "channel_id": int,
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
            "compression": bool,
            "paths": {
                "logs": str,
                "output": str,
                "memory": str,
                "cookies": str,
                "profile": str,
                "driver": str
            }
        },
        "security": {
            "api_keys": dict,
            "allowed_ips": list,
            "rate_limits": dict
        },
        "driver": {
            "headless": bool,
            "window_size": list,
            "user_agent": str,
            "additional_arguments": list,
            "executable_path": str,
            "cache_path": str
        }
    }

    def __init__(
        self,
        config_name: str = "base.yaml",
        env_prefix: str = "CHATMATE_",
        auto_reload: bool = True,
        logger: Optional[ILoggingAgent] = None
    ):
        """
        Initialize the ConfigManager.
        
        Args:
            config_name: Name of the main config file (defaults to base.yaml)
            env_prefix: Prefix for environment variables
            auto_reload: Whether to watch for config file changes
            logger: Optional ILoggingAgent instance for logging
        """
        self.config_name = config_name
        self.env_prefix = env_prefix
        self.auto_reload = auto_reload
        self._logger = logger

        # Set up internal state BEFORE creating the logger.
        self._lock = threading.Lock()
        self._last_load_time = None
        self._config_cache: Dict[str, Any] = {}

        # Set up config paths using PathManager
        self.config_dir = PathManager.get_path('config')
        self.config_path = os.path.join(self.config_dir, config_name)
        os.makedirs(self.config_dir, exist_ok=True)

        # Load initial configuration
        self.reload()

        # Start auto-reload if enabled
        if auto_reload:
            self._start_auto_reload()

    @property
    def logger(self) -> ILoggingAgent:
        """Lazy load the logger if not already set."""
        if self._logger is None:
            # Lazy import to avoid circular dependencies
            from core.UnifiedLoggingAgent import UnifiedLoggingAgent
            self._logger = UnifiedLoggingAgent(self)
        return self._logger

    def set_logger(self, logger: ILoggingAgent) -> None:
        """Set the logger instance."""
        self._logger = logger

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
                "timeout": 30.0,
                "headless": False,
                "reverse_order": False,
                "archive_enabled": True
            },
            "ai": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
                "stop_sequences": [],
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0,
                "chatgpt_url": "",
                "custom_gpt_url": "",
                "prompt_input_selector": "",
                "response_container_selector": "",
                "stop_button_xpath": "",
                "retry_attempts": 3,
                "retry_delay_seconds": 5,
                "excluded_chats": [],
                "prompt_cycle": [],
                "agent_name": "",
                "agent_mode": "",
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
                    "enabled": False,
                    "token": "",
                    "channel_id": 0,
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
                "compression": True,
                "paths": {
                    "logs": "",
                    "output": "",
                    "memory": "",
                    "cookies": "",
                    "profile": "",
                    "driver": ""
                }
            },
            "security": {
                "api_keys": {},
                "allowed_ips": ["127.0.0.1"],
                "rate_limits": {
                    "default": 60,
                    "api": 100
                }
            },
            "driver": {
                "headless": False,
                "window_size": [1280, 720],
                "user_agent": "",
                "additional_arguments": [],
                "executable_path": "",
                "cache_path": ""
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

    def create_driver(self) -> 'webdriver.Chrome':
        """Initialize ChromeDriver with UC (undetected_chromedriver)."""
        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.chrome.options import Options
        except ImportError:
            self.logger.log_system_event(
                event_type="driver_error",
                message="Failed to import required driver packages. Please install undetected_chromedriver.",
                level="error"
            )
            raise

        options = uc.ChromeOptions()

        # Apply driver configuration
        driver_config = self.get("driver", {})
        
        if driver_config.get("headless", False):
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            window_size = driver_config.get("window_size", [1920, 1080])
            options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
            self.logger.log_system_event(
                event_type="driver_config",
                message="Headless mode enabled"
            )

        options.add_argument("--start-maximized")
        profile_dir = self.get("storage.paths.profile")
        if profile_dir:
            options.add_argument(f"--user-data-dir={profile_dir}")

        # Add any additional arguments
        for arg in driver_config.get("additional_arguments", []):
            options.add_argument(arg)

        driver_path = self._get_cached_driver()

        try:
            driver = uc.Chrome(options=options, driver_executable_path=driver_path)
            self.logger.log_system_event(
                event_type="driver_init",
                message="ChromeDriver initialized successfully"
            )
            return driver
        except Exception as e:
            self.logger.log_system_event(
                event_type="driver_error",
                message=f"Failed to initialize ChromeDriver: {str(e)}",
                level="error"
            )
            raise

    def _get_cached_driver(self) -> str:
        """Retrieve existing ChromeDriver or download/cache a fresh one."""
        from webdriver_manager.chrome import ChromeDriverManager
        import shutil

        driver_path = self.get("driver.executable_path")
        if not driver_path:
            driver_path = os.path.join(self.get("storage.paths.driver"), "chromedriver.exe")

        if os.path.exists(driver_path):
            self.logger.log_system_event(
                event_type="driver_cache",
                message=f"Using cached ChromeDriver at {driver_path}"
            )
            return driver_path

        self.logger.log_system_event(
            event_type="driver_cache",
            message="Cached ChromeDriver missing. Downloading latest..."
        )

        try:
            latest_driver = ChromeDriverManager().install()
            os.makedirs(os.path.dirname(driver_path), exist_ok=True)
            shutil.copy(latest_driver, driver_path)
            self.logger.log_system_event(
                event_type="driver_cache",
                message=f"ChromeDriver cached at {driver_path}"
            )
            return driver_path
        except Exception as e:
            self.logger.log_system_event(
                event_type="driver_error",
                message=f"Failed to download/cache ChromeDriver: {str(e)}",
                level="error"
            )
            raise

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
