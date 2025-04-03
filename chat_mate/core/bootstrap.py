"""
Bootstrap module for early system initialization.
This module MUST be imported before any other core modules.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional

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

# Register core paths
_PathRegistry.register('base', PROJECT_ROOT)
_PathRegistry.register('config', PROJECT_ROOT / 'config')
_PathRegistry.register('memory', PROJECT_ROOT / 'memory')
_PathRegistry.register('logs', PROJECT_ROOT / 'logs')
_PathRegistry.register('drivers', PROJECT_ROOT / 'drivers')
_PathRegistry.register('cache', PROJECT_ROOT / 'cache')

# Register template paths
_PathRegistry.register('templates', PROJECT_ROOT / 'templates')
_PathRegistry.register('discord_templates', PROJECT_ROOT / 'templates/discord_templates')
_PathRegistry.register('message_templates', PROJECT_ROOT / 'templates/message_templates')
_PathRegistry.register('general_templates', PROJECT_ROOT / 'templates/general_templates')

# Register output paths
_PathRegistry.register('outputs', PROJECT_ROOT / 'outputs')
_PathRegistry.register('dreamscape', PROJECT_ROOT / 'outputs/dreamscape')
_PathRegistry.register('cycles', PROJECT_ROOT / 'outputs/cycles')

# Register memory files
_PathRegistry.register('conversation_memory', PROJECT_ROOT / 'memory/conversation_memory.json')
_PathRegistry.register('persistent_memory', PROJECT_ROOT / 'memory/persistent_memory.json')
_PathRegistry.register('system_state', PROJECT_ROOT / 'memory/system_state.json')

# Register additional paths
_PathRegistry.register('workflow_audits', PROJECT_ROOT / 'outputs/cycles/workflow_audits')
_PathRegistry.register('discord_exports', PROJECT_ROOT / 'outputs/discord_exports')
_PathRegistry.register('reinforcement_logs', PROJECT_ROOT / 'outputs/reinforcement_logs')
_PathRegistry.register('engagement_templates', PROJECT_ROOT / 'templates/engagement_templates')
_PathRegistry.register('report_templates', PROJECT_ROOT / 'templates/report_templates')

# Register custom paths
strategies_path = PROJECT_ROOT / 'chat_mate' / 'social' / 'strategies'
context_db_path = strategies_path / 'context_db.json'
_PathRegistry.register('strategies', strategies_path)
_PathRegistry.register('context_db', context_db_path)

# --- Create context_db.json if missing ---
if not context_db_path.exists():
    default_context = {
        "recent_responses": [],
        "user_profiles": {},
        "platform_memories": {},
        "trending_tags": []
    }
    with context_db_path.open('w', encoding='utf-8') as f:
        json.dump(default_context, f, indent=2)
    logging.info(f"Created default context_db at {context_db_path}")

# --- Setup Logging ---
# Check if running under pytest to avoid conflicting with its log capture
if 'pytest' not in sys.modules:
    log_file = _PathRegistry._paths['logs'] / 'system.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            # logging.StreamHandler() # Removed for pytest compatibility
        ]
    )
    logging.info("Bootstrap: Logging configured.")
else:
    logging.info("Bootstrap: Skipping basicConfig for pytest run.")

# This info log might still cause issues if basicConfig wasn't run
# logging.info("Bootstrap: Registered paths: %s", {k: str(v) for k, v in _PathRegistry._paths.items()})

def get_bootstrap_paths() -> Dict[str, Path]:
    """Get all registered paths."""
    return _PathRegistry.get_paths()
