import os
import json
import logging
from datetime import datetime

# -------------------------------------------------------------------
# Directory & Log Setup
# -------------------------------------------------------------------

BASE_DIR = os.getcwd()  # Could use PathManager if available
SOCIAL_LOG_DIR = os.path.join(BASE_DIR, "social", "logs")
JSON_LOG_DIR = os.path.join(SOCIAL_LOG_DIR, "json_logs")

os.makedirs(JSON_LOG_DIR, exist_ok=True)

# -------------------------------------------------------------------
# Python Logger Setup (Plain Text)
# -------------------------------------------------------------------

PLAIN_LOG_FILE = os.path.join(SOCIAL_LOG_DIR, "platform_activity.log")

logger = logging.getLogger("AletheiaSocialLogs")
logger.setLevel(logging.DEBUG)  # Capture all levels for flexibility

# File handler for persistent logs
file_handler = logging.FileHandler(PLAIN_LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

# Optional: Console handler for immediate feedback
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.debug(f" Logging initialized at {SOCIAL_LOG_DIR}")

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

    # Synchronous plain-text INFO log
    logger.info(f"[{platform.upper()}] {event_type.upper()} | Result: {result.upper()} | Tags: {tags} | AI Output: {ai_output or 'N/A'}")

# -------------------------------------------------------------------
# Shortcuts for Common Log Events
# -------------------------------------------------------------------

def log_login(platform, result="successful", tags=None, ai_output=None):
    write_json_log(platform, result, tags or ["login"], ai_output, event_type="login")

def log_post(platform, result="successful", tags=None, ai_output=None):
    write_json_log(platform, result, tags or ["post"], ai_output, event_type="post")

def log_error(platform, error_msg, tags=None):
    write_json_log(platform, "failed", tags or ["error"], ai_output=error_msg, event_type="error")
    logger.error(f"[{platform.upper()}] ERROR: {error_msg}")

# -------------------------------------------------------------------
# Future Extension: Discord Webhook Alerts
# -------------------------------------------------------------------

# def send_discord_alert(message: str, webhook_url: str):
#     import requests
#     try:
#         payload = {"content": message}
#         response = requests.post(webhook_url, json=payload)
#         if response.status_code in [200, 204]:
#             logger.info(f" Discord alert sent: {message}")
#         else:
#             logger.warning(f"️ Discord alert failed. Status: {response.status_code}")
#     except Exception as e:
#         logger.exception(f" Failed to send Discord alert: {e}")

# -------------------------------------------------------------------
# Future Extension: JSON Log Rotation (Optional)
# -------------------------------------------------------------------

# def rotate_json_log(base_file: str, max_lines: int = 10000):
#     """
#     Rotate JSONL logs after hitting max_lines.
#     """
#     file_path = os.path.join(JSON_LOG_DIR, base_file)
#     if not os.path.exists(file_path):
#         return
#     with open(file_path, "r", encoding="utf-8") as f:
#         lines = f.readlines()
#     if len(lines) > max_lines:
#         rotated_file = f"{base_file}.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.bak"
#         rotated_path = os.path.join(JSON_LOG_DIR, rotated_file)
#         os.rename(file_path, rotated_path)
#         logger.info(f" Rotated JSON log: {rotated_file}")

# -------------------------------------------------------------------
# Example Usage (Local Testing)
# -------------------------------------------------------------------

if __name__ == "__main__":
    logger.info(" Running log writer test sequence...")

    log_login("twitter", tags=["cookie_login", "session_restore"])
    log_post("linkedin", result="successful", tags=["ai_generated", "scheduled"])
    log_error("reddit", error_msg="❌ Post button missing after DOM update.")
    
    # Uncomment if testing Discord alerts
    # send_discord_alert("VictorOS alert test!", webhook_url="YOUR_WEBHOOK_URL_HERE")

    logger.info(" Log writer test complete.")
