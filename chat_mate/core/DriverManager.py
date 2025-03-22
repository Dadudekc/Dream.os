import os
import sys
import shutil
import time
import pickle
import tempfile
import logging
import threading
from typing import Optional, Dict, Any, List

import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------
# Logger Setup
# ---------------------------
def setup_logger(name="DriverManager", log_dir=os.path.join(os.getcwd(), "logs", "core")):
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    file_handler = logging.FileHandler(os.path.join(log_dir, f"{name}.log"))
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
    return logger

logger = setup_logger()

# ---------------------------
# DriverManager Class
# ---------------------------
class DriverManager:
    """
    Singleton class for managing an undetected Chrome WebDriver instance.
    
    Features:
      - Persistent profile support (or temporary profiles in headless mode)
      - Cookie saving and loading for session persistence
      - Mobile emulation and headless mode support
      - Context management for automatic cleanup
      - Ability to update driver options dynamically
    """
    _instance: Optional['DriverManager'] = None
    _lock = threading.Lock()

    CHATGPT_URL = "https://chat.openai.com/"

    def __new__(cls, *args, **kwargs) -> 'DriverManager':
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance

    def __init__(self,
                 profile_dir: Optional[str] = None,
                 driver_cache_dir: Optional[str] = None,
                 headless: bool = False,
                 cookie_file: Optional[str] = None,
                 wait_timeout: int = 10,
                 mobile_emulation: bool = False,
                 additional_arguments: Optional[List[str]] = None):
        with self._lock:
            if self._initialized:
                return

            self.profile_dir = profile_dir or os.path.join(os.getcwd(), "chrome_profile", "default")
            self.driver_cache_dir = driver_cache_dir or os.path.join(os.getcwd(), "drivers")
            self.cookie_file = cookie_file or os.path.join(os.getcwd(), "cookies", "default.pkl")
            self.headless = headless
            self.wait_timeout = wait_timeout
            self.mobile_emulation = mobile_emulation
            self.additional_arguments = additional_arguments or []

            self.driver = None
            self.temp_profile = None  # For headless mode temporary profile

            os.makedirs(self.driver_cache_dir, exist_ok=True)
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)

            logger.info(f"DriverManager initialized: Headless={self.headless}, Mobile={self.mobile_emulation}")
            self._initialized = True

    # ---------------------------
    # Context Manager Support
    # ---------------------------
    def __enter__(self):
        self.get_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit_driver()

    # ---------------------------
    # Driver Download and Caching
    # ---------------------------
    def _get_cached_driver_path(self) -> str:
        return os.path.join(self.driver_cache_dir, "chromedriver.exe")

    def _download_driver_if_needed(self) -> str:
        cached_driver = self._get_cached_driver_path()
        if not os.path.exists(cached_driver):
            logger.warning("No cached ChromeDriver found. Downloading new version...")
            driver_path = ChromeDriverManager().install()
            os.makedirs(os.path.dirname(cached_driver), exist_ok=True)
            shutil.copyfile(driver_path, cached_driver)
            logger.info(f"Cached ChromeDriver at: {cached_driver}")
            return cached_driver
        logger.info(f"Using cached ChromeDriver: {cached_driver}")
        return cached_driver

    # ---------------------------
    # Driver Initialization
    # ---------------------------
    def get_driver(self, force_new: bool = False):
        with self._lock:
            if self.driver and not force_new:
                logger.info("Returning existing driver instance.")
                return self.driver

            driver_path = self._download_driver_if_needed()
            options = uc.ChromeOptions()
            options.add_argument("--start-maximized")
            for arg in self.additional_arguments:
                options.add_argument(arg)

            # Mobile emulation support
            if self.mobile_emulation:
                device_metrics = {"width": 375, "height": 812, "pixelRatio": 3.0}
                mobile_emulation_settings = {
                    "deviceMetrics": device_metrics,
                    "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_6 like Mac OS X) " +
                                 "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
                }
                options.add_experimental_option("mobileEmulation", mobile_emulation_settings)
                logger.info("Mobile emulation enabled.")

            # Headless mode: use a temporary profile to avoid affecting the persistent profile.
            if self.headless:
                self.temp_profile = tempfile.mkdtemp(prefix="chrome_profile_")
                options.add_argument(f"--user-data-dir={self.temp_profile}")
                options.add_argument("--headless=new")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                logger.info(f"Headless mode enabled with temp profile: {self.temp_profile}")
            else:
                options.add_argument(f"--user-data-dir={self.profile_dir}")

            options.add_argument("--disable-blink-features=AutomationControlled")
            service = ChromeService(executable_path=driver_path)
            logger.info("Launching undetected Chrome driver...")
            new_driver = uc.Chrome(service=service, options=options)
            logger.info("Chrome driver initialized and ready.")
            if not force_new:
                self.driver = new_driver
            return new_driver

    # ---------------------------
    # Driver Termination and Cleanup
    # ---------------------------
    def quit_driver(self):
        with self._lock:
            if self.driver:
                logger.info("Quitting Chrome driver...")
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.exception("Error during driver quit")
                finally:
                    self.driver = None
                    logger.info("Driver session closed.")
                    if self.temp_profile and os.path.exists(self.temp_profile):
                        logger.info(f"Cleaning up temp profile: {self.temp_profile}")
                        shutil.rmtree(self.temp_profile)
                        self.temp_profile = None

    # ---------------------------
    # Cookie Management
    # ---------------------------
    def save_cookies(self):
        if not self.driver:
            logger.warning("Driver not initialized. Cannot save cookies.")
            return
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            logger.info(f"Cookies saved to {self.cookie_file}")
        except Exception as e:
            logger.exception("Failed to save cookies")

    def load_cookies(self) -> bool:
        if not self.driver:
            logger.warning("Driver not initialized. Cannot load cookies.")
            return False
        if not os.path.exists(self.cookie_file):
            logger.warning(f"No cookie file found at {self.cookie_file}")
            return False
        try:
            with open(self.cookie_file, "rb") as f:
                cookies = pickle.load(f)
            self.driver.get(self.CHATGPT_URL)
            time.sleep(5)
            for cookie in cookies:
                cookie.pop("sameSite", None)
                self.driver.add_cookie(cookie)
            self.driver.refresh()
            time.sleep(5)
            logger.info("Cookies loaded and session refreshed.")
            return True
        except Exception as e:
            logger.exception("Failed to load cookies")
            return False

    # ---------------------------
    # Login Verification
    # ---------------------------
    def is_logged_in(self, retries: int = 3) -> bool:
        if not self.driver:
            logger.warning("Driver not initialized.")
            return False
        for attempt in range(1, retries + 1):
            try:
                self.driver.get(self.CHATGPT_URL)
                WebDriverWait(self.driver, self.wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'nav[aria-label="Chat history"]'))
                )
                logger.info("User is logged in.")
                return True
            except Exception as e:
                logger.warning(f"Login check attempt {attempt} failed: {e}")
                time.sleep(2)
        logger.warning("Exceeded login check retries.")
        return False

    # ---------------------------
    # Scrolling Utilities
    # ---------------------------
    def scroll_into_view(self, element):
        if not self.driver:
            logger.warning("Driver not initialized.")
            return
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            logger.info("Scrolled element into view.")
        except Exception as e:
            logger.exception("Failed to scroll element into view")

    def manual_scroll(self, scroll_pause_time: float = 1.0, max_scrolls: int = 10):
        if not self.driver:
            logger.warning("Driver not initialized.")
            return
        logger.info("Starting manual scrolling...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for i in range(max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            logger.info(f"Scroll {i+1}: Document height is {new_height}")
            if new_height == last_height:
                logger.info("Reached bottom of the page.")
                break
            last_height = new_height

    # ---------------------------
    # Updating Driver Options
    # ---------------------------
    def update_options(self, new_options: Dict[str, Any]) -> None:
        with self._lock:
            if "headless" in new_options:
                self.headless = new_options["headless"]
            if "mobile_emulation" in new_options:
                self.mobile_emulation = new_options["mobile_emulation"]
            if "additional_arguments" in new_options:
                self.additional_arguments.extend(new_options["additional_arguments"])
            self.quit_driver()
            self.get_driver(force_new=True)
            logger.info("Driver options updated and driver reinitialized.")

    def __del__(self):
        self.quit_driver()


# ---------------------------
# Example Execution
# ---------------------------
def main():
    with DriverManager(headless=True, mobile_emulation=False) as manager:
        driver = manager.get_driver()
        driver.get("https://chat.openai.com/")
        time.sleep(5)
        if not manager.is_logged_in():
            logger.warning("Manual login required...")
            driver.get("https://chat.openai.com/auth/login")
            input("Press ENTER once logged in...")
            manager.save_cookies()
        else:
            logger.info("Already logged in. Continuing session...")
            manager.save_cookies()
        # Example manual scrolling
        manager.manual_scroll(scroll_pause_time=1, max_scrolls=5)
        logger.info("✅ Session complete.")
        time.sleep(10)
        manager.quit_driver()


if __name__ == "__main__":
    main()