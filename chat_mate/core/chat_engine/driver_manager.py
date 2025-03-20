import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, NoSuchElementException

logger = logging.getLogger("DriverManager")
logger.setLevel(logging.INFO)

class DriverManager:
    """
    DriverManager handles browser driver operations:
      - Lazy initialization
      - Headless mode support
      - Login checks
      - Graceful shutdown
    """

    def __init__(self, headless: bool = True):
        self._driver = None
        self.headless = headless

    def get_driver(self):
        """
        Lazy init the driver if it doesn't exist yet.
        """
        if self._driver is None:
            logger.info("🚀 Initializing Chrome driver...")
            self._driver = self._init_driver_lazy()
        return self._driver

    def _init_driver_lazy(self):
        """
        Initialize Selenium Chrome driver with optional headless mode.
        """
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")

        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        try:
            driver = webdriver.Chrome(options=options)
            logger.info("✅ Chrome driver initialized successfully.")
            return driver
        except WebDriverException as e:
            logger.exception(f"❌ Failed to initialize Chrome driver: {e}")
            raise

    def shutdown_driver(self):
        """
        Gracefully close and quit the driver.
        """
        if self._driver:
            try:
                logger.info("🛑 Shutting down Chrome driver...")
                self._driver.quit()
                logger.info("✅ Chrome driver shut down successfully.")
            except Exception as e:
                logger.warning(f"⚠️ Error during driver shutdown: {e}")
            finally:
                self._driver = None

    def is_logged_in(self):
        """
        Check if the current session is authenticated.
        Modify the selector to suit your system.
        """
        driver = self.get_driver()

        try:
            logger.info("🔎 Checking login status...")
            driver.get("https://chat.openai.com/")  # Or your target URL
            time.sleep(3)

            # Example: Look for user profile icon or another element
            if driver.find_elements("css selector", "div[data-testid='user-avatar']"):
                logger.info("✅ Logged in.")
                return True
            else:
                logger.warning("❌ Not logged in.")
                return False

        except Exception as e:
            logger.exception(f"❌ Error checking login status: {e}")
            return False
