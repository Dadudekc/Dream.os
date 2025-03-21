import os
import json
import logging
import shutil
import re
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Import our PathManager
try:
    from core.PathManager import PathManager
except ImportError:
    # Fallback to a simple path if core is not available
    class PathManager:
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        
        @classmethod
        def ensure_directories(cls):
            os.makedirs(cls.logs_dir, exist_ok=True)

class Config:
    """
    Centralized runtime configuration for ChatMate Agents.
    Handles paths, environment setup, and driver management.
    """

    # ----------------------
    # Constants / Defaults
    # ----------------------
    CHATGPT_URL = "https://chat.openai.com"
    DEFAULT_MODEL = "gpt-4o"
    ALLOWED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4o-jawbone",
        "gpt-4-5",
        "o3-mini-high",
        "o1"
    ]

    DEFAULT_EXCLUDED_CHATS = [
        "ChatGPT", "Sora", "Freeride Investor",
        "Tbow Tactic Generator", "Explore GPTs", "Axiom",
        "work project", "prompt library", "Bot",
        "smartstock-pro", "Code Copilot"
    ]

    def __init__(self, config_file: str = None):
        # Paths from PathManager
        self.logs_dir = PathManager.logs_dir
        self.output_dir = PathManager.cycles_dir
        self.memory_file = os.path.join(PathManager.memory_dir, "persistent_memory.json")
        self.cookies_file = os.path.join(PathManager.memory_dir, "cookies", "openai.pkl")
        self.profile_dir = os.path.join(PathManager.drivers_dir, "chrome_profile", "openai")
        self.driver_dir = PathManager.drivers_dir
        self.driver_path = os.path.join(self.driver_dir, "chromedriver.exe")

        # Operational Flags
        self.headless = True
        self.reverse_order = False
        self.archive_enabled = True

        # AI & Discord Config
        self.default_model = self.DEFAULT_MODEL
        self.discord_enabled = False
        self.discord_token = ""
        self.discord_channel_id = 0

        # Prompts / Exclusions / Agent Identity
        self.excluded_chats = self.DEFAULT_EXCLUDED_CHATS.copy()
        self.prompt_cycle = ["dreamscape", "workflow_audit", "personal_strategy_review"]
        self.agent_name = "ChatAgent"
        self.agent_mode = "executor"
        self.chatgpt_url = self.CHATGPT_URL

        # Bootstrapping
        self._ensure_directories()
        self.logger = self._setup_logger("Config")

        self.logger.info("⚙️ Config initialization started.")

        if config_file:
            self.load_from_file(config_file)

        self.logger.info("✅ Config initialized successfully.")

    # ----------------------
    # JSON Config Loading
    # ----------------------
    def load_from_file(self, path: str):
        """Load runtime overrides from JSON configuration."""
        self.logger.info(f"📂 Loading configuration from: {path}")

        if not os.path.isfile(path):
            self.logger.error(f"❌ Config file not found: {path}")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            for key, value in config_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    self.logger.info(f"🔧 Loaded config value: {key} = {value}")

            self.logger.info("✅ Configuration successfully loaded.")

        except Exception as e:
            self.logger.error(f"❌ Failed to load config: {e}")

    # ----------------------
    # Directory Setup
    # ----------------------
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        paths = [
            self.logs_dir,
            self.output_dir,
            os.path.dirname(self.cookies_file),
            self.profile_dir,
            self.driver_dir
        ]

        for path in paths:
            try:
                os.makedirs(path, exist_ok=True)
                self.logger and self.logger.info(f"📁 Ensured directory: {path}")
            except Exception as e:
                print(f"❌ Failed to create directory {path}: {e}")

    # ----------------------
    # ChromeDriver Management
    # ----------------------
    def create_driver(self):
        """Initialize ChromeDriver with UC (undetected_chromedriver)."""
        options = uc.ChromeOptions()

        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            self.logger.info("✅ Headless mode enabled.")

        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir={self.profile_dir}")

        driver_path = self._get_cached_driver()

        try:
            driver = uc.Chrome(options=options, driver_executable_path=driver_path)
            self.logger.info("🚀 ChromeDriver initialized successfully.")
            return driver
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize ChromeDriver: {e}")
            raise

    def _get_cached_driver(self):
        """Retrieve existing ChromeDriver or download/cache a fresh one."""
        if os.path.exists(self.driver_path):
            self.logger.info(f"✅ Using cached ChromeDriver at {self.driver_path}")
            return self.driver_path

        self.logger.warning("⚠️ Cached ChromeDriver missing. Downloading latest...")

        try:
            latest_driver = ChromeDriverManager().install()
            shutil.copy(latest_driver, self.driver_path)
            self.logger.info(f"✅ ChromeDriver cached at {self.driver_path}")
            return self.driver_path
        except Exception as e:
            self.logger.error(f"❌ Failed to download/cache ChromeDriver: {e}")
            raise

    # ----------------------
    # Logger Setup
    # ----------------------
    def _setup_logger(self, name: str):
        """Set up and return a logger instance."""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            os.makedirs(self.logs_dir, exist_ok=True)
            log_file = os.path.join(self.logs_dir, f"{name}.log")

            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
            file_handler.setFormatter(formatter)

            logger.addHandler(file_handler)

        return logger

    # ----------------------
    # Helpers & Utilities
    # ----------------------
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove unsafe characters from filenames."""
        return re.sub(r'[\\/*?:"<>| ]+', "_", filename).strip("_")[:50]

    def get(self, key: str, default=None):
        """Dict-style accessor."""
        return getattr(self, key, default)

    def to_dict(self) -> dict:
        """Return the current config as a dictionary."""
        return {
            "headless": self.headless,
            "reverse_order": self.reverse_order,
            "archive_enabled": self.archive_enabled,
            "default_model": self.default_model,
            "allowed_models": self.ALLOWED_MODELS,
            "discord_enabled": self.discord_enabled,
            "discord_token": self.discord_token,
            "discord_channel_id": self.discord_channel_id,
            "excluded_chats": self.excluded_chats,
            "prompt_cycle": self.prompt_cycle,
            "agent_name": self.agent_name,
            "agent_mode": self.agent_mode,
            "chatgpt_url": self.chatgpt_url
        }

def get_logger(name: str = "chat_mate", log_dir: str = None):
    """
    Configure and return a logger instance.

    Args:
        name (str): The logger name.
        log_dir (str): Directory to store log files. Defaults to Config.LOG_DIR.

    Returns:
        logging.Logger: Configured logger instance.
    """
    if log_dir is None:
        try:
            log_dir = PathManager.get_path('logs')
        except (AttributeError, ValueError):
            # Fallback to the legacy property or a default path
            try:
                log_dir = PathManager.logs_dir
            except AttributeError:
                log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        return logger

    # File Handler
    log_file = os.path.join(log_dir, f"{name}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.debug(f"✅ Logger '{name}' initialized at {log_file}")

    return logger
