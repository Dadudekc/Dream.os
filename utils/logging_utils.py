import os
import json
import logging
from typing import Optional
from core.logging.utils.setup import setup_logging
from datetime import datetime

# -------------------------------------------------------------------
# Directory & Log Setup
# -------------------------------------------------------------------

BASE_DIR = os.getcwd()  # Could use PathManager if available
UTILS_LOG_DIR = os.path.join(BASE_DIR, "utils", "logs")
JSON_LOG_DIR = os.path.join(UTILS_LOG_DIR, "json_logs")

os.makedirs(JSON_LOG_DIR, exist_ok=True)

# -------------------------------------------------------------------
# Python Logger Setup (Plain Text)
# -------------------------------------------------------------------

PLAIN_LOG_FILE = os.path.join(UTILS_LOG_DIR, "utils_activity.log")

logger = logging.getLogger("AletheiaUtilsLogs")
logger.setLevel(logging.DEBUG)  # Capture all levels for flexibility

# File handler for persistent logs
file_handler = logging.FileHandler(PLAIN_LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

# Optional: Console handler for immediate feedback
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.debug(f" Logging initialized at {UTILS_LOG_DIR}")

# -------------------------------------------------------------------
# Aletheia JSON Log Writer
# -------------------------------------------------------------------

def write_json_log(
    component: str,
    result: str,
    tags=None,
    ai_output=None,
    event_type="system",
    log_file="utils_activity.jsonl"
):
    """
    Unified JSON logger for all utility events.
    """
    tags = tags or []
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "component": component.lower(),
        "event_type": event_type.lower(),
        "result": result.lower(),
        "tags": tags,
        "ai_output": ai_output or ""
    }

    file_path = os.path.join(JSON_LOG_DIR, log_file)

    try:
        with open(file_path, "a", encoding="utf-8") as f:
            json.dump(log_entry, f)
            f.write("\n")
        logger.debug(f" JSON log recorded: {component.upper()} [{event_type.upper()}]")

    except Exception as e:
        logger.exception(f" Failed to write JSON log for {component.upper()}: {e}")

    # Synchronous plain-text INFO log
    logger.info(f"[{component.upper()}] {event_type.upper()} | Result: {result.upper()} | Tags: {tags} | AI Output: {ai_output or 'N/A'}")

# -------------------------------------------------------------------
# Shortcuts for Common Log Events
# -------------------------------------------------------------------

def log_success(component, message, tags=None, ai_output=None):
    write_json_log(component, "successful", tags or ["success"], ai_output, event_type="success")

def log_error(component, error_msg, tags=None):
    write_json_log(component, "failed", tags or ["error"], ai_output=error_msg, event_type="error")
    logger.error(f"[{component.upper()}] ERROR: {error_msg}")

def setup_basic_logging(
    logger_name: str,
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    log_to_file: bool = False,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """A simple wrapper around the advanced setup_logging function."""
    return setup_logging(
        logger_name=logger_name,
        log_level=log_level,
        log_to_console=log_to_console,
        log_to_file=log_to_file,
        log_file=log_file,
        log_format=log_format
    )
