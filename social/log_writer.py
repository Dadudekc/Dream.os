import os
import json
import logging
import functools
from datetime import datetime
from logging.handlers import RotatingFileHandler
import requests

# -------------------------------------------------------------------
# Directory & Log Setup
# -------------------------------------------------------------------

BASE_DIR = os.getcwd()  # Adjust if using a different base path
SOCIAL_LOG_DIR = os.path.join(BASE_DIR, "social", "logs")
JSON_LOG_DIR = os.path.join(SOCIAL_LOG_DIR, "json_logs")

os.makedirs(SOCIAL_LOG_DIR, exist_ok=True)
os.makedirs(JSON_LOG_DIR, exist_ok=True)

PLAIN_LOG_FILE = os.path.join(SOCIAL_LOG_DIR, "platform_activity.log")
JSON_LOG_FILE = os.path.join(JSON_LOG_DIR, "social_activity.jsonl")

# -------------------------------------------------------------------
# Plain Logger Setup with Log Rotation
# -------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def get_social_logger() -> logging.Logger:
    """Returns a logger for plain text logging with rotation."""
    logger_instance = logging.getLogger("AletheiaSocialLogs")
    if not logger_instance.handlers:
        logger_instance.setLevel(logging.DEBUG)

        # RotatingFileHandler rotates at 5 MB with up to 5 backups.
        file_handler = RotatingFileHandler(PLAIN_LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

        logger_instance.addHandler(file_handler)
        logger_instance.addHandler(console_handler)
    return logger_instance

# -------------------------------------------------------------------
# JSON Logger Setup with Custom Formatter & Rotation
# -------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured log entries."""
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "platform": record.__dict__.get("platform", "unknown").lower(),
            "event_type": record.__dict__.get("event_type", "system").lower(),
            "result": record.__dict__.get("result", "unknown").lower(),
            "tags": record.__dict__.get("tags", []),
            "ai_output": record.__dict__.get("ai_output", "")
        }
        return json.dumps(log_entry)

@functools.lru_cache(maxsize=None)
def get_json_logger() -> logging.Logger:
    """Returns a logger for JSON logging with rotation."""
    json_logger = logging.getLogger("AletheiaJSONLogs")
    if not json_logger.handlers:
        json_logger.setLevel(logging.DEBUG)
        # Use rotating handler for JSON logs too.
        json_handler = RotatingFileHandler(JSON_LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
        json_handler.setFormatter(JSONFormatter())
        json_logger.addHandler(json_handler)
    return json_logger

# -------------------------------------------------------------------
# Unified JSON Log Writer
# -------------------------------------------------------------------

def write_json_log(
    platform: str,
    result: str,
    tags=None,
    ai_output=None,
    event_type="system"
):
    """
    Writes a structured JSON log entry and also logs on the plain logger.
    """
    tags = tags or []
    extra = {
        "platform": platform,
        "event_type": event_type,
        "result": result,
        "tags": tags,
        "ai_output": ai_output or ""
    }
    json_logger = get_json_logger()
    # Create an empty message and pass extra attributes.
    json_logger.info("", extra=extra)
    
    plain_logger = get_social_logger()
    plain_logger.info(f"[{platform.upper()}] {event_type.upper()} | Result: {result.upper()} | Tags: {tags} | AI Output: {ai_output or 'N/A'}")

# -------------------------------------------------------------------
# Shortcuts for Common Log Events
# -------------------------------------------------------------------

def log_login(platform, result="successful", tags=None, ai_output=None):
    """Shortcut to log a login event."""
    write_json_log(platform, result, tags or ["login"], ai_output, event_type="login")

def log_post(platform, result="successful", tags=None, ai_output=None):
    """Shortcut to log a post event."""
    write_json_log(platform, result, tags or ["post"], ai_output, event_type="post")

def log_error(platform, error_msg, tags=None):
    """Shortcut to log an error event."""
    write_json_log(platform, "failed", tags or ["error"], ai_output=error_msg, event_type="error")
    logger = get_social_logger()
    logger.error(f"[{platform.upper()}] ERROR: {error_msg}")

# -------------------------------------------------------------------
# Discord Webhook Alerts
# -------------------------------------------------------------------

def send_discord_alert(message: str, webhook_url: str):
    """
    Sends a Discord alert via webhook.
    """
    logger = get_social_logger()
    try:
        data = {"content": message}
        response = requests.post(webhook_url, json=data)
        if response.status_code == 204:
            logger.info("Discord alert sent successfully.")
        else:
            logger.error(f"Failed to send Discord alert. Status: {response.status_code} - {response.text}")
    except Exception as e:
        logger.exception(f"Error sending Discord alert: {e}")

# -------------------------------------------------------------------
# Example Usage (Local Testing)
# -------------------------------------------------------------------

if __name__ == "__main__":
    logger = get_social_logger()
    logger.info("Running advanced log writer test sequence...")

    log_login("twitter", tags=["cookie_login", "session_restore"])
    log_post("linkedin", result="successful", tags=["ai_generated", "scheduled"])
    log_error("reddit", error_msg="❌ Post button missing after DOM update.")

    # Test Discord alert (ensure you have a valid webhook URL)
    # send_discord_alert("VictorOS alert test!", webhook_url="YOUR_WEBHOOK_URL_HERE")

    logger.info("Log writer test complete.")
