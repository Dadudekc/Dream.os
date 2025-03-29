import os
import logging
from datetime import datetime

# --------------------------------------------------------------------
# Project Root & Template Path Handling
# --------------------------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEMPLATE_DIR = os.path.join(ROOT_DIR, "templates", "discord_templates")

# --------------------------------------------------------------------
# Configuration Constants (moved to config if available)
# --------------------------------------------------------------------
try:
    from utils.chat_mate_config import Config
    config = Config()
    RATE_LIMIT_DELAY = config.get('rate_limit_delay', 10)
    MAX_ACTIONS_BEFORE_COOLDOWN = config.get('max_actions_before_cooldown', 5)
    COOLDOWN_PERIOD = config.get('cooldown_period', 60)
    BASE_OUTPUT_PATH = config.get('base_output_path', "prompt_cycle_outputs")
except ImportError:
    RATE_LIMIT_DELAY = 10
    MAX_ACTIONS_BEFORE_COOLDOWN = 5
    COOLDOWN_PERIOD = 60
    BASE_OUTPUT_PATH = "prompt_cycle_outputs"

# --------------------------------------------------------------------
# Logging Setup and Icon Definitions
# --------------------------------------------------------------------
logger = logging.getLogger("PromptCycle")
logging.basicConfig(level=logging.INFO)

LOG_ICONS = {
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "❌",
    "success": "✅",
    "cooldown": "⏳",
    "upload": "📤",
}

def sanitize(text: str) -> str:
    """Utility to sanitize file names or strings if needed."""
    return "".join(c for c in text if c.isalnum() or c in (' ', '_', '-')).rstrip()

def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()

def ensure_directory(path: str) -> None:
    """Ensure a directory exists, create if it doesn't."""
    if not os.path.exists(path):
        os.makedirs(path) 