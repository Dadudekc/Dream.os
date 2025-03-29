"""
Bootstrap module for early system initialization.
This module MUST be imported before any other core modules.
"""

import logging
import json
from pathlib import Path
from typing import Dict

# Calculate project root using pathlib
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Early path registration before any other imports
class _PathRegistry:
    """Internal path registry to avoid circular imports."""
    _paths: Dict[str, Path] = {}

    @classmethod
    def register(cls, key: str, path: str | Path) -> None:
        """Register a path before PathManager is available."""
        path = Path(path)
        if not path.is_absolute():
            abs_path = PROJECT_ROOT / path
        else:
            abs_path = path

        cls._paths[key] = abs_path

        # Handle file vs directory creation
        if abs_path.suffix:  # It's a file
            abs_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            abs_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_paths(cls) -> Dict[str, Path]:
        return cls._paths.copy()


def get_bootstrap_paths() -> Dict[str, Path]:
    """
    Get registered bootstrap paths and ensure essential directories exist.
    
    Returns:
        Dictionary of project paths.
    """
    # Base path registrations - absolute references first
    if not _PathRegistry._paths:
        # Base directory (root of the project)
        _PathRegistry.register('base', PROJECT_ROOT)
        
        # Essential working directories
        _PathRegistry.register('config', PROJECT_ROOT / 'config')
        _PathRegistry.register('logs', PROJECT_ROOT / 'logs')
        _PathRegistry.register('memory', PROJECT_ROOT / 'memory')
        _PathRegistry.register('outputs', PROJECT_ROOT / 'outputs')
        _PathRegistry.register('templates', PROJECT_ROOT / 'templates')
        _PathRegistry.register('drivers', PROJECT_ROOT / 'drivers')
        _PathRegistry.register('cycles', PROJECT_ROOT / 'cycles')
        
        # Specific output directories
        _PathRegistry.register('dreamscape', PROJECT_ROOT / 'outputs' / 'dreamscape')
        _PathRegistry.register('workflow_audits', PROJECT_ROOT / 'outputs' / 'workflow_audits')
        _PathRegistry.register('discord_exports', PROJECT_ROOT / 'outputs' / 'discord_exports')
        _PathRegistry.register('reinforcement_logs', PROJECT_ROOT / 'logs' / 'reinforcement')
        
        # Template subdirectories
        _PathRegistry.register('discord_templates', PROJECT_ROOT / 'templates' / 'discord_templates')
        _PathRegistry.register('message_templates', PROJECT_ROOT / 'templates' / 'message_templates')
        _PathRegistry.register('engagement_templates', PROJECT_ROOT / 'templates' / 'engagement_templates')
        _PathRegistry.register('report_templates', PROJECT_ROOT / 'templates' / 'report_templates')
        _PathRegistry.register('dreamscape_templates', PROJECT_ROOT / 'templates' / 'dreamscape_templates')
        
        # Strategy
        _PathRegistry.register('strategies', PROJECT_ROOT / 'strategy_templates')
        
        # Storage
        _PathRegistry.register('context_db', PROJECT_ROOT / 'memory' / 'context.db')
        
    return _PathRegistry.get_paths()


def initialize_essential_directories():
    """Ensure all essential directories exist."""
    get_bootstrap_paths()  # This will trigger all directory creation
    
    # Add custom paths if needed for further initialization
    for key, path in _PathRegistry.get_paths().items():
        if not path.suffix:  # Skip files (with extensions)
            path.mkdir(parents=True, exist_ok=True)
            logging.debug(f"Ensured directory: {path}")


# Initialize essentials when this module is imported
initialize_essential_directories()
