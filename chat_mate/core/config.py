from typing import Optional, Any, Dict
from core.UnifiedConfigManager import UnifiedConfigManager

class ConfigurationSingleton:
    """
    Singleton class that provides global access to the UnifiedConfigManager.
    Ensures only one instance of the configuration manager exists.
    """
    _instance: Optional['ConfigurationSingleton'] = None
    _config_manager: Optional[UnifiedConfigManager] = None

    def __new__(cls) -> 'ConfigurationSingleton':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_manager = UnifiedConfigManager()
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