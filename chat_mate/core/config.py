import os
from pathlib import Path

# Base paths
ROOT_DIR = os.environ.get("ROOT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs")
LOGS_DIR = os.path.join(OUTPUTS_DIR, "logs")
MEMORY_DIR = os.path.join(ROOT_DIR, "memory")
CACHE_DIR = os.path.join(ROOT_DIR, "cache")
TEMPLATES_DIR = os.path.join(ROOT_DIR, "templates")

# Browser profile and cookie paths
PROFILE_DIR = os.path.join(ROOT_DIR, "chrome_profile")
DRIVERS_DIR = os.path.join(ROOT_DIR, "drivers")
COOKIES_DIR = os.path.join(ROOT_DIR, "cookies")

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)
os.makedirs(DRIVERS_DIR, exist_ok=True)
os.makedirs(COOKIES_DIR, exist_ok=True)

# Log paths
INTERACTION_LOG_PATH = os.path.join(LOGS_DIR, "interactions.log")
ERROR_LOG_PATH = os.path.join(LOGS_DIR, "errors.log")
DEBUG_LOG_PATH = os.path.join(LOGS_DIR, "debug.log")

# Operation settings
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds
DEFAULT_TIMEOUT = 30  # seconds
RESPONSE_WAIT_TIME = 5  # seconds

# Browser automation settings
HEADLESS_MODE = os.environ.get("HEADLESS_MODE", "False").lower() == "true"
MAX_SESSION_DURATION = int(os.environ.get("MAX_SESSION_DURATION", "3600"))  # 1 hour
DRIVER_RETRY_ATTEMPTS = int(os.environ.get("DRIVER_RETRY_ATTEMPTS", "3"))
DRIVER_RETRY_DELAY = int(os.environ.get("DRIVER_RETRY_DELAY", "5"))
USE_UNDETECTED_DRIVER = os.environ.get("USE_UNDETECTED_DRIVER", "True").lower() == "true"
MOBILE_EMULATION = os.environ.get("MOBILE_EMULATION", "False").lower() == "true"
CHROME_OPTIONS = [
    "--disable-extensions",
    "--disable-notifications", 
    "--disable-popup-blocking",
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox"
]

# API settings
DEFAULT_MODEL = "gpt-4"
ALLOWED_MODELS = ["gpt-4", "gpt-3.5-turbo", "gpt-4o", "claude-3-opus", "claude-3-sonnet"]

# Discord settings
DISCORD_ENABLED = False
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "")

# Memory settings
MAX_MEMORY_ENTRIES = 100
MEMORY_PERSISTENCE = True

# Default headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
} 
