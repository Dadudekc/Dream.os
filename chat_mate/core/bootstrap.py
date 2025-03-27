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


# --- Register Essential Paths ---
_PathRegistry.register('data', 'data')
_PathRegistry.register('logs', 'outputs/logs')
_PathRegistry.register('outputs', 'outputs')
_PathRegistry.register('config', 'config')
_PathRegistry.register('cache', 'cache')

# --- Extended Paths ---
_PathRegistry.register('memory', 'memory')
_PathRegistry.register('templates', 'templates')
_PathRegistry.register('drivers', 'drivers')
_PathRegistry.register('cycles', 'outputs/cycles')
_PathRegistry.register('dreamscape', 'outputs/cycles/dreamscape')
_PathRegistry.register('workflow_audits', 'outputs/cycles/workflow_audits')
_PathRegistry.register('discord_exports', 'outputs/discord_exports')
_PathRegistry.register('reinforcement_logs', 'outputs/reinforcement_logs')
_PathRegistry.register('discord_templates', 'templates/discord_templates')
_PathRegistry.register('message_templates', 'templates/message_templates')
_PathRegistry.register('engagement_templates', 'templates/engagement_templates')
_PathRegistry.register('report_templates', 'templates/report_templates')
_PathRegistry.register('base', PROJECT_ROOT)

# --- Custom Paths ---
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
log_file = _PathRegistry._paths['logs'] / 'system.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logging.info("Bootstrap: Registered paths: %s", {k: str(v) for k, v in _PathRegistry._paths.items()})


def get_bootstrap_paths() -> Dict[str, Path]:
    """Get the registered path map as Path objects."""
    return _PathRegistry.get_paths()
