"""
Bootstrap module for early system initialization.
This module MUST be imported before any other core modules.
"""
import os
import logging
import json
from typing import Dict

# Calculate project root for absolute paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Early path registration before any other imports
class _PathRegistry:
    """Internal path registry to avoid circular imports."""
    _paths: Dict[str, str] = {}
    
    @classmethod
    def register(cls, key: str, path: str) -> None:
        """Register a path before PathManager is available."""
        # Convert to absolute path if not already
        if not os.path.isabs(path):
            abs_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
        else:
            abs_path = path
            
        cls._paths[key] = abs_path
        
        # Check if path points to a file (has extension)
        if os.path.splitext(path)[1]:  # Has file extension
            # Create parent directory for file paths
            parent_dir = os.path.dirname(abs_path)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
        else:
            # Create directory for directory paths
            os.makedirs(abs_path, exist_ok=True)
        
    @classmethod
    def get_paths(cls) -> Dict[str, str]:
        """Get registered paths."""
        return cls._paths.copy()

# Register essential paths before any imports
_PathRegistry.register('data', './data')
_PathRegistry.register('logs', './outputs/logs')
_PathRegistry.register('outputs', './outputs')
_PathRegistry.register('config', './config')
_PathRegistry.register('configs', './configs')  # Both 'config' and 'configs' for backwards compatibility
_PathRegistry.register('cache', './cache')

# Additional paths from old PathManager
_PathRegistry.register('memory', './memory')
_PathRegistry.register('templates', './templates')
_PathRegistry.register('drivers', './drivers')
_PathRegistry.register('cycles', './outputs/cycles')
_PathRegistry.register('dreamscape', './outputs/cycles/dreamscape')
_PathRegistry.register('workflow_audits', './outputs/cycles/workflow_audits')
_PathRegistry.register('discord_exports', './outputs/discord_exports')
_PathRegistry.register('reinforcement_logs', './outputs/reinforcement_logs')
_PathRegistry.register('discord_templates', './templates/discord_templates')
_PathRegistry.register('message_templates', './templates/message_templates')
_PathRegistry.register('engagement_templates', './templates/engagement_templates')
_PathRegistry.register('report_templates', './templates/report_templates')
_PathRegistry.register('base', PROJECT_ROOT)  # Add 'base' path for the project root

# Fix strategies path to be relative to project root only once
_PathRegistry.register('strategies', os.path.join(PROJECT_ROOT, 'chat_mate', 'social', 'strategies'))

# Set path for context_db
_PathRegistry.register('context_db', os.path.join(PROJECT_ROOT, 'chat_mate', 'social', 'strategies', 'context_db.json'))

# Create empty context_db.json file if it doesn't exist
context_db_path = _PathRegistry._paths['context_db']
strategies_path = _PathRegistry._paths['strategies']

# Ensure strategies directory exists
if not os.path.exists(strategies_path):
    os.makedirs(strategies_path, exist_ok=True)
    logging.info(f"Created strategies directory at {strategies_path}")

# Create default context_db.json if needed
if not os.path.exists(context_db_path):
    default_context = {
        "recent_responses": [],
        "user_profiles": {},
        "platform_memories": {},
        "trending_tags": []
    }
    with open(context_db_path, 'w', encoding='utf-8') as f:
        json.dump(default_context, f, indent=2)
    logging.info(f"Created default context_db at {context_db_path}")

# Set up basic logging configuration
os.makedirs(_PathRegistry._paths['logs'], exist_ok=True)
log_file = os.path.join(_PathRegistry._paths['logs'], 'system.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Log the bootstrap process
logging.info("Bootstrap: Registered paths: %s", _PathRegistry._paths)

def get_bootstrap_paths() -> Dict[str, str]:
    """Get the paths registered during bootstrap."""
    return _PathRegistry.get_paths() 