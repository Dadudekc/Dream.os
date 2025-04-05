import os
import json
import logging
from typing import Optional
from core.logging.factories.LoggerFactory import LoggerFactory
from datetime import datetime

# -------------------------------------------------------------------
# Directory & Log Setup
# -------------------------------------------------------------------

BASE_DIR = os.getcwd()  # Could use PathManager if available
UTILS_LOG_DIR = os.path.join(BASE_DIR, "utils", "logs")
JSON_LOG_DIR = os.path.join(UTILS_LOG_DIR, "json_logs")

os.makedirs(JSON_LOG_DIR, exist_ok=True)

# -------------------------------------------------------------------
# Python Logger Setup (Plain Text) - Using LoggerFactory
# -------------------------------------------------------------------

# Get logger using the factory
# Note: Log file will be in outputs/logs/aletheiautilslogs.log
logger = LoggerFactory.create_standard_logger(
    name="AletheiaUtilsLogs", 
    level=logging.DEBUG, # Keep DEBUG level
    log_to_file=True
)

# Removed manual handler creation and adding

logger.debug(f" Logging initialized via LoggerFactory")

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
