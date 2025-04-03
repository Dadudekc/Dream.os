import os
import json
import logging
import functools  # Added
from datetime import datetime

# -------------------------------------------------------------------
# Directory & Log Setup
# -------------------------------------------------------------------

BASE_DIR = os.getcwd()  # Could use PathManager if available
SOCIAL_LOG_DIR = os.path.join(BASE_DIR, "social", "logs")
JSON_LOG_DIR = os.path.join(SOCIAL_LOG_DIR, "json_logs")

os.makedirs(JSON_LOG_DIR, exist_ok=True)

# -------------------------------------------------------------------
# Logger Setup (Deferred)
# -------------------------------------------------------------------

PLAIN_LOG_FILE = os.path.join(SOCIAL_LOG_DIR, "platform_activity.log")

@functools.lru_cache(maxsize=None)
def get_social_logger() -> logging.Logger:
    """Gets and configures the AletheiaSocialLogs logger."""
    logger_instance = logging.getLogger("AletheiaSocialLogs")
    if not logger_instance.handlers:
        logger_instance.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(PLAIN_LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

        logger_instance.addHandler(file_handler)
        logger_instance.addHandler(console_handler)

        # logger_instance.debug(f" Logging initialized at {SOCIAL_LOG_DIR}") # Keep commented

    return logger_instance

# -------------------------------------------------------------------
# Aletheia JSON Log Writer
# -------------------------------------------------------------------

def write_json_log(
    platform: str,
    result: str,
    tags=None,
    ai_output=None,
    event_type="system",
    log_file="social_activity.jsonl"
):
    """
    Unified JSON logger for all platform events.
    """
    logger = get_social_logger() # Use the getter
    tags = tags or []
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "platform": platform.lower(),
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
        logger.debug(f" JSON log recorded: {platform.upper()} [{event_type.upper()}]")

    except Exception as e:
        logger.exception(f" Failed to write JSON log for {platform.upper()}: {e}")

    logger.info(f"[{platform.upper()}] {event_type.upper()} | Result: {result.upper()} | Tags: {tags} | AI Output: {ai_output or 'N/A'}")

# -------------------------------------------------------------------
# Shortcuts for Common Log Events
# -------------------------------------------------------------------

def log_login(platform, result="successful", tags=None, ai_output=None):
    write_json_log(platform, result, tags or ["login"], ai_output, event_type="login")

def log_post(platform, result="successful", tags=None, ai_output=None):
    write_json_log(platform, result, tags or ["post"], ai_output, event_type="post")

def log_error(platform, error_msg, tags=None):
    logger = get_social_logger() # Use the getter
    write_json_log(platform, "failed", tags or ["error"], ai_output=error_msg, event_type="error")
    logger.error(f"[{platform.upper()}] ERROR: {error_msg}")

# -------------------------------------------------------------------
# Future Extension: Discord Webhook Alerts
# -------------------------------------------------------------------

# def send_discord_alert(message: str, webhook_url: str):
#     logger = get_social_logger() # Needs getter if uncommented
#     import requests
#     # ... rest of function ...

# -------------------------------------------------------------------
# Future Extension: JSON Log Rotation (Optional)
# -------------------------------------------------------------------

# def rotate_json_log(base_file: str, max_lines: int = 10000):
#     logger = get_social_logger() # Needs getter if uncommented
#     # ... rest of function ...

# -------------------------------------------------------------------
# Example Usage (Local Testing)
# -------------------------------------------------------------------

if __name__ == "__main__":
    logger = get_social_logger() # Use the getter
    logger.info(" Running log writer test sequence...")

    log_login("twitter", tags=["cookie_login", "session_restore"])
    log_post("linkedin", result="successful", tags=["ai_generated", "scheduled"])
    log_error("reddit", error_msg="❌ Post button missing after DOM update.")

    # Uncomment if testing Discord alerts
    # send_discord_alert("VictorOS alert test!", webhook_url="YOUR_WEBHOOK_URL_HERE")

    logger.info(" Log writer test complete.")
