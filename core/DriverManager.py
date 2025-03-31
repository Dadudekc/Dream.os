import os
import sys
import shutil
import time
import pickle
import tempfile
import logging
import threading
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Optional undetected_chromedriver support
try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

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
# Consolidated DriverManager Class
# ---------------------------
class DriverManager:
    """
    Unified DriverManager for Selenium-based browser automation.
    
    Features:
      - Singleton pattern to ensure a single active driver instance
      - Session management with automatic expiration (default 1 hour) and renewal
      - Persistent profile support (or temporary profiles in headless mode)
      - Cookie saving/loading for session persistence
      - Support for headless mode, mobile emulation, and optional undetected mode
      - Auto-downloading and caching of the ChromeDriver executable
      - Robust retry mechanisms for resilient browser operations
      - Utilities for waiting, scrolling, and option updates
    """
    _instance: Optional['DriverManager'] = None
    _lock = threading.Lock()

    # Default constants
    CHATGPT_URL = "https://chat.openai.com/"
    DEFAULT_TIMEOUT = 10
    DEFAULT_MAX_SESSION_DURATION = 3600  # seconds (1 hour)
    DEFAULT_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 5

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
                 wait_timeout: int = DEFAULT_TIMEOUT,
                 mobile_emulation: bool = False,
                 additional_arguments: Optional[List[str]] = None,
                 undetected_mode: bool = True,
                 max_session_duration: int = DEFAULT_MAX_SESSION_DURATION,
                 retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
                 retry_delay: int = DEFAULT_RETRY_DELAY,
                 timeout: Optional[int] = None,
                 logger: Optional[logging.Logger] = None,
                 **kwargs):
        """
        Initialize DriverManager.
        
        Args:
            profile_dir: Directory for Chrome profile persistence.
            driver_cache_dir: Directory to cache downloaded WebDriver.
            headless: Run browser in headless mode.
            cookie_file: File path to save/load cookies.
            wait_timeout: Default WebDriverWait timeout.
            mobile_emulation: Enable mobile emulation.
            additional_arguments: Additional Chrome command-line arguments.
            undetected_mode: Use undetected_chromedriver if available.
            max_session_duration: Session expiration time in seconds.
            retry_attempts: Retry attempts for driver operations.
            retry_delay: Delay between retry attempts.
            timeout: Alias for wait_timeout, for backward compatibility.
            logger: Optional logger instance.
            **kwargs: Additional configuration options.
        """
        with self._lock:
            if self._initialized:
                return

            # Set up logger
            self.logger = logger or setup_logger()

            # Set configuration
            self.profile_dir = profile_dir or os.path.join(os.getcwd(), "chrome_profile", "default")
            self.driver_cache_dir = driver_cache_dir or os.path.join(os.getcwd(), "drivers")
            self.cookie_file = cookie_file or os.path.join(os.getcwd(), "cookies", "default.pkl")
            self.headless = headless
            self.wait_timeout = timeout or wait_timeout  # Use timeout if provided, else wait_timeout
            self.mobile_emulation = mobile_emulation
            self.additional_arguments = additional_arguments or []
            self.undetected_mode = undetected_mode and UNDETECTED_AVAILABLE
            self.max_session_duration = max_session_duration
            self.retry_attempts = retry_attempts
            self.retry_delay = retry_delay

            # Store additional kwargs for future use
            self.additional_options = kwargs

            # Runtime state
            self.driver: Optional[webdriver.Chrome] = None
            self.temp_profile: Optional[str] = None
            self.session_start_time: Optional[datetime] = None

            # Create necessary directories
            os.makedirs(self.driver_cache_dir, exist_ok=True)
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            if not os.path.exists(self.profile_dir) and not self.headless:
                os.makedirs(self.profile_dir, exist_ok=True)

            self.logger.info(f"DriverManager initialized: Headless={self.headless}, "
                        f"Mobile={self.mobile_emulation}, Undetected={self.undetected_mode}")
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
    # ChromeDriver Caching
    # ---------------------------
    def _get_cached_driver_path(self) -> str:
        return os.path.join(self.driver_cache_dir, "chromedriver.exe")

    def _download_driver_if_needed(self) -> str:
        cached_driver = self._get_cached_driver_path()
        if not os.path.exists(cached_driver):
            self.logger.warning("No cached ChromeDriver found. Downloading new version...")
            driver_path = ChromeDriverManager().install()
            os.makedirs(os.path.dirname(cached_driver), exist_ok=True)
            shutil.copyfile(driver_path, cached_driver)
            self.logger.info(f"Cached ChromeDriver at: {cached_driver}")
            return cached_driver
        self.logger.info(f"Using cached ChromeDriver: {cached_driver}")
        return cached_driver

    # ---------------------------
    # Session Management
    # ---------------------------
    def _is_session_expired(self) -> bool:
        if not self.session_start_time:
            return True
        session_duration = (datetime.now() - self.session_start_time).total_seconds()
        expired = session_duration > self.max_session_duration
        if expired:
            self.logger.info(f"Session expired after {session_duration:.2f} seconds")
        return expired

    def refresh_session(self) -> bool:
        if not self.driver:
            self.logger.warning("No active session to refresh")
            return False
        try:
            self.quit_driver()
            return bool(self.get_driver(force_new=True))
        except Exception as e:
            self.logger.error(f"Error refreshing session: {e}")
            return False

    def get_session_info(self) -> Dict[str, Any]:
        if not self.driver or not self.session_start_time:
            return {
                'status': 'inactive',
                'start_time': None,
                'duration': 0,
                'expired': True,
                'headless': self.headless,
                'undetected_mode': self.undetected_mode
            }
        duration = (datetime.now() - self.session_start_time).total_seconds()
        return {
            'status': 'active',
            'start_time': self.session_start_time.isoformat(),
            'duration': duration,
            'expired': self._is_session_expired(),
            'headless': self.headless,
            'undetected_mode': self.undetected_mode
        }

    def set_session_timeout(self, timeout: int) -> None:
        self.max_session_duration = timeout
        self.logger.info(f"Session timeout set to {timeout} seconds")

    # ---------------------------
    # Chrome Options Creation
    # ---------------------------
    def _create_chrome_options(self) -> Options:
        options = uc.ChromeOptions() if self.undetected_mode else Options()
        # Common arguments
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        for arg in self.additional_arguments:
            options.add_argument(arg)
        # Mobile emulation
        if self.mobile_emulation:
            device_metrics = {"width": 375, "height": 812, "pixelRatio": 3.0}
            mobile_emulation_settings = {
                "deviceMetrics": device_metrics,
                "userAgent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_6 like Mac OS X) "
                              "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")
            }
            options.add_experimental_option("mobileEmulation", mobile_emulation_settings)
            self.logger.info("Mobile emulation enabled.")
        # Headless mode: use temporary profile if headless
        if self.headless:
            self.temp_profile = tempfile.mkdtemp(prefix="chrome_profile_")
            options.add_argument(f"--user-data-dir={self.temp_profile}")
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            self.logger.info(f"Headless mode enabled with temp profile: {self.temp_profile}")
        else:
            options.add_argument(f"--user-data-dir={self.profile_dir}")
            self.logger.info(f"Using persistent profile: {self.profile_dir}")
            
        # Experimental options to potentially reduce detection
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Configure logging level for Selenium/Browser
        options.set_capability('goog:loggingPrefs', {'browser': 'WARNING'})

        return options

    # ---------------------------
    # Driver Initialization
    # ---------------------------
    def get_driver(self, force_new: bool = False) -> Optional[webdriver.Chrome]:
        with self._lock:
            if self.driver and not force_new and not self._is_session_expired():
                return self.driver
            if self.driver and self._is_session_expired():
                self.logger.info("Session expired, creating new driver.")
                self.quit_driver()
            for attempt in range(1, self.retry_attempts + 1):
                try:
                    driver_path = self._download_driver_if_needed()
                    options = self._create_chrome_options()
                    service = ChromeService(executable_path=driver_path)
                    if self.undetected_mode:
                        self.logger.info("Launching undetected Chrome driver...")
                        new_driver = uc.Chrome(service=service, options=options)
                    else:
                        self.logger.info("Launching standard Chrome driver...")
                        new_driver = webdriver.Chrome(service=service, options=options)
                    self.session_start_time = datetime.now()
                    self.driver = new_driver
                    return new_driver
                except Exception as e:
                    self.logger.error(f"Driver initialization attempt {attempt} failed: {e}")
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_delay)
                    else:
                        self.logger.error("All driver initialization attempts failed")
                        return None

    # ---------------------------
    # Driver Termination and Cleanup
    # ---------------------------
    def quit_driver(self) -> None:
        with self._lock:
            if self.driver:
                self.logger.info("Quitting Chrome driver...")
                try:
                    self.driver.quit()
                except Exception as e:
                    self.logger.exception(f"Error during driver quit: {e}")
                finally:
                    self.driver = None
                    self.session_start_time = None
                    self.logger.info("Driver session closed.")
                    if self.temp_profile and os.path.exists(self.temp_profile):
                        self.logger.info(f"Cleaning up temp profile: {self.temp_profile}")
                        shutil.rmtree(self.temp_profile)
                        self.temp_profile = None

    # ---------------------------
    # Cookie Management
    # ---------------------------
    def save_cookies(self) -> bool:
        if not self.driver:
            self.logger.warning("Driver not initialized. Cannot save cookies.")
            return False
        try:
            cookies = self.driver.get_cookies()
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            with open(self.cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            self.logger.info(f"Cookies saved to {self.cookie_file}")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to save cookies: {e}")
            return False

    def load_cookies(self) -> bool:
        if not self.driver:
            self.logger.warning("Driver not initialized. Cannot load cookies.")
            return False
        if not os.path.exists(self.cookie_file):
            self.logger.warning(f"No cookie file found at {self.cookie_file}")
            return False
        try:
            with open(self.cookie_file, "rb") as f:
                cookies = pickle.load(f)
            current_url = self.driver.current_url
            if not current_url.startswith("http"):
                self.driver.get(self.CHATGPT_URL)
                time.sleep(2)
            for cookie in cookies:
                if "sameSite" in cookie:
                    cookie.pop("sameSite", None)
                try:
                    self.driver.add_cookie(cookie)
                except Exception as cookie_ex:
                    self.logger.warning(f"Could not add cookie: {cookie_ex}")
            self.driver.refresh()
            time.sleep(2)
            self.logger.info("Cookies loaded and session refreshed.")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to load cookies: {e}")
            return False

    def clear_cookies(self) -> bool:
        if not self.driver:
            self.logger.warning("No active session to clear cookies")
            return False
        try:
            self.driver.delete_all_cookies()
            self.logger.info("Cookies cleared successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing cookies: {e}")
            return False

    # ---------------------------
    # Login Verification
    # ---------------------------
    def is_logged_in(self, retries: int = 3) -> bool:
        if not self.driver:
            self.logger.warning("Driver not initialized.")
            return False
        for attempt in range(1, retries + 1):
            try:
                self.driver.get(self.CHATGPT_URL)
                WebDriverWait(self.driver, self.wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'nav[aria-label="Chat history"]'))
                )
                self.logger.info("User is logged in.")
                return True
            except Exception as e:
                self.logger.warning(f"Login check attempt {attempt} failed: {e}")
                time.sleep(2)
        self.logger.warning("Exceeded login check retries.")
        return False

    # ---------------------------
    # Retry Execution Helper
    # ---------------------------
    def execute_with_retry(self, action: Callable, max_retries: int = None) -> Any:
        max_retries = max_retries or self.retry_attempts
        for attempt in range(1, max_retries + 1):
            try:
                return action()
            except Exception as e:
                self.logger.warning(f"Action attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    time.sleep(self.retry_delay)
                    if self._is_session_expired():
                        self.refresh_session()
                else:
                    self.logger.error("All action attempts failed")
                    raise

    # ---------------------------
    # Scrolling Utilities
    # ---------------------------
    def scroll_into_view(self, element) -> None:
        if not self.driver:
            self.logger.warning("Driver not initialized.")
            return
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            self.logger.info("Scrolled element into view.")
        except Exception as e:
            self.logger.exception(f"Failed to scroll element into view: {e}")

    def manual_scroll(self, scroll_pause_time: float = 1.0, max_scrolls: int = 10) -> None:
        if not self.driver:
            self.logger.warning("Driver not initialized.")
            return
        self.logger.info("Starting manual scrolling...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for i in range(max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            self.logger.info(f"Scroll {i+1}: Document height is {new_height}")
            if new_height == last_height:
                self.logger.info("Reached bottom of the page.")
                break
            last_height = new_height

    # ---------------------------
    # Update Options & Restart if Needed
    # ---------------------------
    def update_options(self, new_options: Dict[str, Any]) -> None:
        with self._lock:
            restart_needed = False
            # Options that require a driver restart when changed
            restart_options = ["headless", "mobile_emulation", "undetected_mode", 
                               "additional_arguments", "profile_dir"]
            for option, value in new_options.items():
                if hasattr(self, option):
                    if option in restart_options and getattr(self, option) != value:
                        restart_needed = True
                    setattr(self, option, value)
                    self.logger.info(f"Updated option {option} to {value}")
                else:
                    self.logger.warning(f"Unknown option: {option}")
            if restart_needed and self.driver:
                self.logger.info("Restarting driver with new options...")
                self.quit_driver()
                self.get_driver(force_new=True)
            self.logger.info("Driver options updated successfully.")

    def shutdown_driver(self):
        """Cleanly shutdown the driver and force kill any leftover browser processes."""
        try:
            if self.driver:
                self.logger.info("Shutting down WebDriver...")
                try:
                    self.driver.quit()
                except Exception as e:
                    self.logger.error(f"Error quitting driver: {e}")
                finally:
                    self.driver = None
                    
            # Force kill any remaining browser processes
            self.force_kill_browsers()
            
            self.logger.info("WebDriver shutdown complete.")
        except Exception as e:
            self.logger.error(f"Error during driver shutdown: {e}")
            
    def force_kill_browsers(self):
        """
        Force kill any remaining browser and WebDriver processes
        that might be hanging around.
        """
        import platform
        import subprocess
        
        self.logger.info("Checking for remaining browser processes...")
        
        try:
            # Kill based on operating system
            if platform.system() == "Windows":
                # Kill Chrome and ChromeDriver processes
                subprocess.run("taskkill /f /im chromedriver.exe", shell=True, capture_output=True)
                subprocess.run("taskkill /f /im chrome.exe", shell=True, capture_output=True)
                subprocess.run("taskkill /f /im msedgedriver.exe", shell=True, capture_output=True)
                subprocess.run("taskkill /f /im msedge.exe", shell=True, capture_output=True)
            elif platform.system() == "Linux":
                # Linux process killing
                subprocess.run("pkill -f chromedriver", shell=True, capture_output=True)
                subprocess.run("pkill -f chrome", shell=True, capture_output=True)
                subprocess.run("pkill -f chromium", shell=True, capture_output=True)
            elif platform.system() == "Darwin":  # macOS
                # macOS process killing
                subprocess.run("pkill -f chromedriver", shell=True, capture_output=True)
                subprocess.run("pkill -f Chrome", shell=True, capture_output=True)
            
            self.logger.info("Browser cleanup completed.")
        except Exception as e:
            self.logger.error(f"Error during browser cleanup: {e}")
            # Continue anyway, as this is a best-effort cleanup

    def __del__(self):
        """
        Safer approach to handle object deletion.
        Use explicit shutdown_driver instead of quit_driver for better cleanup.
        """
        try:
            self.shutdown_driver()
        except Exception:
            # Don't raise exceptions during garbage collection
            pass


# ---------------------------
# Example Execution
# ---------------------------
def main():
    """
    Example usage:
      - Initializes the DriverManager
      - Navigates to ChatGPT
      - Checks login status and prompts for manual login if needed
      - Saves cookies, retrieves session info, and performs scrolling
      - Demonstrates updating an option (e.g. wait_timeout)
    """
    with DriverManager(headless=False, undetected_mode=True) as manager:
        driver = manager.get_driver()
        if not driver:
            logger.error("Driver failed to initialize.")
            return

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

        session_info = manager.get_session_info()
        logger.info(f"Session info: {session_info}")

        manager.manual_scroll(scroll_pause_time=1, max_scrolls=5)
        manager.update_options({"wait_timeout": 20})

        logger.info("Session complete.")
        time.sleep(5)


if __name__ == "__main__":
    main()
