import os
import logging
from typing import Dict, Optional
from core.bootstrap import get_bootstrap_paths

logger = logging.getLogger(__name__)

class PathManager:
    """
    Centralized path management system.
    Initialized with bootstrap paths to avoid circular imports.
    """
    _paths: Dict[str, str] = {}
    _initialized: bool = False
    
    # === Backward compatibility properties ===
    @classmethod
    def __getattr__(cls, name):
        """Legacy property access for backward compatibility."""
        # Try to map old property names to new path keys
        if name == 'base_dir':
            return cls.get_path('base')
        elif name == 'outputs_dir':
            return cls.get_path('outputs')
        elif name == 'memory_dir':
            return cls.get_path('memory')
        elif name == 'templates_dir':
            return cls.get_path('templates')
        elif name == 'drivers_dir':
            return cls.get_path('drivers')
        elif name == 'configs_dir':
            return cls.get_path('configs')
        elif name == 'logs_dir':
            return cls.get_path('logs')
        elif name == 'cycles_dir':
            return cls.get_path('cycles')
        elif name == 'dreamscape_dir':
            return cls.get_path('dreamscape')
        elif name == 'workflow_audit_dir':
            return cls.get_path('workflow_audits')
        elif name == 'discord_exports_dir':
            return cls.get_path('discord_exports')
        elif name == 'reinforcement_logs_dir':
            return cls.get_path('reinforcement_logs')
        elif name == 'discord_templates_dir':
            return cls.get_path('discord_templates')
        elif name == 'message_templates_dir':
            return cls.get_path('message_templates')
        elif name == 'engagement_templates_dir':
            return cls.get_path('engagement_templates')
        elif name == 'report_templates_dir':
            return cls.get_path('report_templates')
        elif name == 'strategies_dir':
            return cls.get_path('strategies')
        elif name == 'context_db_path':
            return cls.get_path('context_db')
        
        raise AttributeError(f"'{cls.__name__}' has no attribute '{name}'")
    
    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure paths are initialized from bootstrap."""
        if not cls._initialized:
            cls._paths = get_bootstrap_paths()
            cls._initialized = True
    
    @classmethod
    def register_path(cls, key: str, path: str) -> None:
        """
        Register a new path.
        
        Args:
            key: Unique identifier for the path
            path: The path to register
        """
        cls._ensure_initialized()
        abs_path = os.path.abspath(path)
        if key in cls._paths and cls._paths[key] != abs_path:
            logger.warning(f"⚠️ Overwriting existing path for key '{key}'")
        cls._paths[key] = abs_path
    
    @classmethod
    def get_path(cls, key: str) -> str:
        """
        Get a registered path.
        
        Args:
            key: The path identifier
            
        Returns:
            The registered path
            
        Raises:
            ValueError: If the path key is not found
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
            # Skip file paths (those with extensions)
            if os.path.splitext(path)[1]:
                # For file paths, ensure parent directory exists
                parent_dir = os.path.dirname(path)
                os.makedirs(parent_dir, exist_ok=True)
            else:
                # For directory paths, ensure directory exists
                os.makedirs(path, exist_ok=True)
    
    @classmethod
    def list_paths(cls) -> Dict[str, str]:
        """List all registered paths."""
        cls._ensure_initialized()
        return cls._paths.copy()
    
    @classmethod
    def get_relative_path(cls, key: str, *paths: str) -> str:
        """
        Get a path relative to a registered base path.
        
        Args:
            key: The base path identifier
            *paths: Additional path components to join
            
        Returns:
            The complete path
        """
        base = cls.get_path(key)
        return os.path.join(base, *paths)
