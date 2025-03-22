import os
import logging
from typing import Dict
from core.bootstrap import get_bootstrap_paths

logger = logging.getLogger(__name__)

class PathManagerMeta(type):
    """A metaclass to dynamically create properties for all registered paths."""
    
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        # Initialize internal storage and flag
        cls._paths = {}
        cls._initialized = False
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
    """
    Centralized path management system with dynamic property generation.
    
    Once initialized (via bootstrap), all registered paths become available as
    class properties. For example, if 'logs' is registered, you can access it as:
    
        PathManager.logs_dir  # Backward-compatible alias
        PathManager.logs      # Direct key access
    
    Also provides methods to register paths, ensure directories exist, and to
    describe available paths.
    """
    
    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure paths are initialized from bootstrap if not already done."""
        if not cls._initialized:
            cls._paths = get_bootstrap_paths()
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
        abs_path = os.path.abspath(path)
        if key in cls._paths and cls._paths[key] != abs_path:
            logger.warning(f"⚠️ Overwriting existing path for key '{key}'")
        cls._paths[key] = abs_path
        # Regenerate dynamic properties for the new key.
        cls.__class__._generate_properties()
    
    @classmethod
    def get_path(cls, key: str) -> str:
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
            logger.warning(f"⚠️ Path key '{key}' not found.")
            raise ValueError(f"Path key '{key}' not found.")
        return cls._paths[key]
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all registered directories exist."""
        cls._ensure_initialized()
        for key, path in cls._paths.items():
            # Check if it's likely a file (has an extension)
            if os.path.splitext(path)[1]:
                # For file paths, ensure the parent directory exists
                parent_dir = os.path.dirname(path)
                os.makedirs(parent_dir, exist_ok=True)
            else:
                # For directory paths, create the directory if missing
                os.makedirs(path, exist_ok=True)
    
    @classmethod
    def list_paths(cls) -> Dict[str, str]:
        """
        List all registered paths.
        
        Returns:
            A copy of the dictionary of registered paths.
        """
        cls._ensure_initialized()
        return cls._paths.copy()
    
    @classmethod
    def get_relative_path(cls, key: str, *paths: str) -> str:
        """
        Get a path relative to a registered base path.
        
        Args:
            key: The base path identifier.
            *paths: Additional path components to join.
            
        Returns:
            The combined path.
        """
        base = cls.get_path(key)
        return os.path.join(base, *paths)
    
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
            result[key] = cls._paths[key]
        # Also include backward compatibility names
        for key in cls._paths:
            if not key.endswith('_dir') and not key.endswith('_path'):
                compat_name = f"{key}_dir"
                result[compat_name] = cls._paths[key]
        return result
