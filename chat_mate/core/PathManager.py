import os
import logging
from typing import Dict
from core.bootstrap import get_bootstrap_paths
from pathlib import Path

logger = logging.getLogger(__name__)

class PathManagerMeta(type):
    """A metaclass to dynamically create properties for all registered paths."""
    
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        # Initialize internal storage and flag
        cls._paths = {}
        cls._initialized = False
        cls._instance = None
        return cls

    @classmethod
    def _generate_properties(mcs, cls):
        """Generate dynamic properties for all keys in _paths."""
        for key in cls._paths.keys():
            # If a property already exists, skip (avoid overwriting explicit definitions)
            if hasattr(cls, key):
                continue

            # Create a property getter that uses get_path
            def make_getter(path_key):
                return property(lambda self: cls.get_path(path_key))
            
            # Set the property with the original key
            setattr(cls, key, make_getter(key))

            # For backward compatibility, also create a property ending in '_dir' if needed
            if not key.endswith('_dir') and not key.endswith('_path'):
                compat_name = f"{key}_dir"
                if not hasattr(cls, compat_name):
                    setattr(cls, compat_name, make_getter(key))

class PathManager(metaclass=PathManagerMeta):
    """Unified PathManager for core functionalities."""
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PathManager, cls).__new__(cls)
            cls._ensure_initialized()
        return cls._instance
    
    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure paths are initialized from bootstrap if not already done."""
        if not cls._initialized:
            from core.bootstrap import get_bootstrap_paths
            cls._paths = get_bootstrap_paths()

            # 🔧 Register additional paths not included in bootstrap
            if "resonance_models" not in cls._paths:
                # You can adjust the subpath here if your folder structure changes
                cls._paths["resonance_models"] = Path(cls._paths["base"]) / "core" / "meredith" / "resonance_match_models"

            cls._initialized = True
            PathManagerMeta._generate_properties(cls)

    
    @classmethod
    def register_path(cls, key: str, path: str) -> None:
        """
        Register a new path and dynamically create a property for it.
        
        Args:
            key: Unique identifier for the path.
            path: The path to register.
        """
        cls._ensure_initialized()
        abs_path = Path(path)
        if key in cls._paths and cls._paths[key] != abs_path:
            logger.warning(f"Overwriting existing path for key '{key}'")
        cls._paths[key] = abs_path
        # Regenerate dynamic properties for the new key.
        PathManagerMeta._generate_properties(cls)
    
    @classmethod
    def get_path(cls, key: str) -> Path:
        """
        Retrieve a registered path.
        
        Args:
            key: The path identifier.
            
        Returns:
            The registered path.
            
        Raises:
            ValueError: If the path key is not found.
        """
        cls._ensure_initialized()
        if key not in cls._paths:
            logger.warning(f"Path key '{key}' not found.")
            raise ValueError(f"Path key '{key}' not found.")
        return cls._paths[key]
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all registered directories exist."""
        cls._ensure_initialized()
        for key, path in cls._paths.items():
            # Check if it's likely a file (has an extension)
            if path.suffix:
                # For file paths, ensure the parent directory exists
                parent_dir = path.parent
                parent_dir.mkdir(parents=True, exist_ok=True)
            else:
                # For directory paths, create the directory if missing
                path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def list_paths(cls) -> Dict[str, Path]:
        """
        List all registered paths.
        
        Returns:
            A copy of the dictionary of registered paths.
        """
        cls._ensure_initialized()
        return cls._paths.copy()
    
    @classmethod
    def get_relative_path(cls, key: str, *paths: str) -> Path:
        """
        Get a path relative to a registered base path.
        
        Args:
            key: The base path identifier.
            *paths: Additional path components to join.
            
        Returns:
            The combined path.
        """
        base = cls.get_path(key)
        return base.joinpath(*paths)
    
    @classmethod
    def describe_paths(cls) -> Dict[str, str]:
        """
        Describe all available paths.
        
        Returns:
            A dictionary mapping property names to their paths.
        """
        cls._ensure_initialized()
        result = {}
        # Include direct keys
        for key in cls._paths:
            result[key] = str(cls._paths[key])
        # Also include backward compatibility names
        for key in cls._paths:
            if not key.endswith('_dir') and not key.endswith('_path'):
                compat_name = f"{key}_dir"
                result[compat_name] = str(cls._paths[key])
        return result

    @classmethod
    def get_env_path(cls, filename=".env") -> Path:
        """
        Return absolute path to the .env file.
        Defaults to the project's base directory.
        """
        cls._ensure_initialized()
        base_dir = cls.get_path('base')
        return base_dir.joinpath(filename)

    @classmethod
    def get_rate_limit_state_path(cls, filename="rate_limit_state.json") -> Path:
        """
        Return absolute path to the rate limit state file.
        Defaults to the cache directory.
        """
        cls._ensure_initialized()
        return cls.get_path('cache').joinpath(filename)

    @classmethod
    def get_chrome_profile_path(cls, sub_dir="chrome_profiles") -> Path:
        """
        Return the chrome profile path, defaults to a subdirectory in drivers.
        """
        cls._ensure_initialized()
        return cls.get_path('drivers').joinpath(sub_dir)

    @classmethod
    def get_template_path(cls, subdir: str = "") -> Path:
        """
        Get the path to the templates directory or a subdirectory within it.
        
        Args:
            subdir (str): Optional subdirectory within the templates directory.
            
        Returns:
            Path: The full path to the templates directory or subdirectory.
        """
        base = cls.get_path('templates')
        return base.joinpath(subdir) if subdir else base

    @classmethod
    def ensure_path_exists(cls, name: str):
        """Ensure a registered path exists by creating directories if needed."""
        path = cls.get_path(name)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_config_path(cls, filename: str = "") -> Path:
        """
        Return absolute path to a file or directory inside the config directory.

        Args:
            filename (str): Optional filename inside the config directory.
        Returns:
            Path: Full path to the config file or directory.
        """
        cls._ensure_initialized()
        base = cls.get_path("config")
        return base / filename if filename else base

    @classmethod
    def get_memory_path(cls, filename: str = "") -> Path:
        """
        Return absolute path to a file or directory inside the memory directory.

        Args:
            filename (str): Optional filename inside the memory directory.
        Returns:
            Path: Full path to the memory file or directory.
        """
        cls._ensure_initialized()
        base = cls.get_path("memory")
        return base / filename if filename else base

    @classmethod
    def get_workspace_path(cls) -> Path:
        """
        Get the root workspace path.
        
        Returns:
            Path: The workspace root path
        """
        cls._ensure_initialized()
        return cls.get_path("base")
