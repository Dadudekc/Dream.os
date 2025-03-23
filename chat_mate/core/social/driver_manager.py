import os
import sys
import random
import shutil
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from social.social_config import social_config
from social.log_writer import logger
from utils.proxy_utils import get_random_proxy
from utils.ua_utils import get_random_user_agent

logger = logging.getLogger("DriverManager")


class DriverSession:
    """
    Manages a single Selenium WebDriver session.
    """

    def __init__(self, session_id, proxy=None, headless=False, disable_images=False):
        self.session_id = session_id
        self.proxy = proxy or get_random_proxy()
        self.headless = headless
        self.disable_images = disable_images
        self.driver = None

    def initialize_driver(self):
        logger.info(f" Initializing driver for session: {self.session_id}")
        options = self._build_chrome_options()

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self._apply_stealth_settings()

            logger.info(f" Driver initialized for session {self.session_id}")
            return self.driver

        except Exception as e:
            logger.error(f" Failed to initialize driver for session {self.session_id}: {e}")
            self.cleanup_profile()
            sys.exit(1)

    def _build_chrome_options(self):
        options = Options()

        # Basic browser setup
        options.add_argument("--start-maximized")

        # Headless mode
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")

        # Anti-detection flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Proxy setup
        if self.proxy:
            logger.info(f"️ Using proxy for session {self.session_id}: {self.proxy}")
            options.add_argument(f"--proxy-server={self.proxy}")

        # User agent spoofing
        user_agent = get_random_user_agent()
        logger.info(f"🦸 User-Agent for session {self.session_id}: {user_agent}")
        options.add_argument(f"user-agent={user_agent}")

        # Disable images for faster loading (optional)
        if self.disable_images:
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)

        # Chrome profile management
        profile_dir = self._get_profile_dir()
        os.makedirs(profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
        logger.info(f" Chrome profile directory: {profile_dir}")

        return options

    def _apply_stealth_settings(self):
        if not self.driver:
            return

        logger.debug(f"️ Applying stealth settings for session {self.session_id}")
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            """
        })

    def shutdown_driver(self):
        if self.driver:
            logger.info(f" Shutting down driver for session {self.session_id}")
            self.driver.quit()
            self.driver = None

    def cleanup_profile(self):
        profile_dir = self._get_profile_dir()

        if os.path.exists(profile_dir):
            try:
                logger.info(f"🧹 Cleaning up profile for session {self.session_id}")
                shutil.rmtree(profile_dir)
            except Exception as e:
                logger.warning(f"️ Failed to remove profile directory {profile_dir}: {e}")

    def restart_driver(self):
        logger.info(f"️ Restarting driver for session {self.session_id}")
        self.shutdown_driver()
        return self.initialize_driver()

    def _get_profile_dir(self):
        base_profile_dir = social_config.get_env(
            "CHROME_PROFILE_PATH",
            os.path.join(os.getcwd(), "chrome_profiles")
        )
        return os.path.join(base_profile_dir, self.session_id)


def get_multi_driver_sessions(session_ids, proxy_rotation=True, headless=False, disable_images=False):
    """
    Initialize multiple driver sessions with optional proxy rotation.
    """
    sessions = []

    for session_id in session_ids:
        proxy = get_random_proxy() if proxy_rotation else None
        driver_session = DriverSession(
            session_id=session_id,
            proxy=proxy,
            headless=headless,
            disable_images=disable_images
        )
        driver_session.initialize_driver()
        sessions.append(driver_session)

    logger.info(f" {len(sessions)} driver sessions initialized.")
    return sessions
