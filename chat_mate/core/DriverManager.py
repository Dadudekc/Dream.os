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

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------
# Logger Setup
# ---------------------------
def setup_logger(name="DriverManager", log_dir=os.path.join(os.getcwd(), "logs", "core")):
    """Set up a logger for the DriverManager module."""
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
    Unified driver manager for browser automation.
    
    Features:
      - Singleton pattern ensures one driver instance across the application
      - Session management with automatic expiration and renewal
      - Persistent profile support (or temporary profiles in headless mode)
      - Cookie saving and loading for session persistence
      - Mobile emulation and headless mode support
      - Context management for automatic cleanup
      - Retry mechanisms for resilient browser operations
      - Support for both regular Chrome and undetected Chrome
    """
    _instance: Optional['DriverManager'] = None
    _lock = threading.Lock()

    CHATGPT_URL = "https://chat.openai.com/"
    DEFAULT_TIMEOUT = 10
    DEFAULT_MAX_SESSION_DURATION = 3600  # 1 hour in seconds
    DEFAULT_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 5

    def __new__(cls, *args, **kwargs) -> 'DriverManager':
        """Ensure singleton pattern."""
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
                 retry_delay: int = DEFAULT_RETRY_DELAY):
        """
        Initialize the driver manager.
        
        Args:
            profile_dir: Path to the Chrome profile directory
            driver_cache_dir: Path to store downloaded WebDrivers
            headless: Whether to run in headless mode
            cookie_file: Path to store browser cookies
            wait_timeout: Default timeout for WebDriverWait
            mobile_emulation: Whether to emulate a mobile device
            additional_arguments: Additional Chrome options
            undetected_mode: Use undetected_chromedriver instead of regular selenium
            max_session_duration: Maximum session duration in seconds
            retry_attempts: Number of retry attempts for driver operations
            retry_delay: Delay between retry attempts in seconds
        """
        with self._lock:
            if self._initialized:
                return

            # Paths and file settings
            self.profile_dir = profile_dir or os.path.join(os.getcwd(), "chrome_profile", "default")
            self.driver_cache_dir = driver_cache_dir or os.path.join(os.getcwd(), "drivers")
            self.cookie_file = cookie_file or os.path.join(os.getcwd(), "cookies", "default.pkl")
            
            # Driver behavior settings
            self.headless = headless
            self.wait_timeout = wait_timeout
            self.mobile_emulation = mobile_emulation
            self.additional_arguments = additional_arguments or []
            self.undetected_mode = undetected_mode
            
            # Session management settings
            self.max_session_duration = max_session_duration
            self.retry_attempts = retry_attempts
            self.retry_delay = retry_delay
            
            # Runtime state
            self.driver = None
            self.temp_profile = None
            self.session_start_time = None
            
            # Create necessary directories
            os.makedirs(self.driver_cache_dir, exist_ok=True)
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            if not os.path.exists(self.profile_dir) and not self.headless:
                os.makedirs(self.profile_dir, exist_ok=True)

            logger.info(f"DriverManager initialized: Headless={self.headless}, "
                       f"Mobile={self.mobile_emulation}, Undetected={self.undetected_mode}")
            self._initialized = True

    # ---------------------------
    # Context Manager Support
    # ---------------------------
    def __enter__(self):
        """Support for context manager pattern (with statement)."""
        self.get_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources when exiting context manager."""
        self.quit_driver()

    # ---------------------------
    # Driver Download and Caching
    # ---------------------------
    def _get_cached_driver_path(self) -> str:
        """Get the path to the cached ChromeDriver executable."""
        return os.path.join(self.driver_cache_dir, "chromedriver.exe")

    def _download_driver_if_needed(self) -> str:
        """Download and cache the ChromeDriver if not already present."""
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
    # Session Management
    # ---------------------------
    def _is_session_expired(self) -> bool:
        """Check if the current session has expired."""
        if not self.session_start_time:
            return True
            
        session_duration = (datetime.now() - self.session_start_time).total_seconds()
        expired = session_duration > self.max_session_duration
        if expired:
            logger.info(f"Session expired after {session_duration:.2f} seconds")
        return expired

    def refresh_session(self) -> bool:
        """Refresh the current driver session."""
        if not self.driver:
            logger.warning("No active session to refresh")
            return False
            
        try:
            self.quit_driver()
            return bool(self.get_driver(force_new=True))
        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return False

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session."""
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
        """Set the maximum session duration."""
        self.max_session_duration = timeout
        logger.info(f"Session timeout set to {timeout} seconds")

    # ---------------------------
    # Driver Initialization
    # ---------------------------
    def _create_chrome_options(self) -> Options:
        """Create Chrome options based on the current configuration."""
        options = Options() if not self.undetected_mode else uc.ChromeOptions()
        
        # Common arguments
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Add user-provided arguments
        for arg in self.additional_arguments:
            options.add_argument(arg)

        # Mobile emulation settings
        if self.mobile_emulation:
            device_metrics = {"width": 375, "height": 812, "pixelRatio": 3.0}
            mobile_emulation_settings = {
                "deviceMetrics": device_metrics,
                "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_6 like Mac OS X) " +
                            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
            }
            options.add_experimental_option("mobileEmulation", mobile_emulation_settings)
            logger.info("Mobile emulation enabled.")

        # Headless mode settings
        if self.headless:
            self.temp_profile = tempfile.mkdtemp(prefix="chrome_profile_")
            options.add_argument(f"--user-data-dir={self.temp_profile}")
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            logger.info(f"Headless mode enabled with temp profile: {self.temp_profile}")
        else:
            options.add_argument(f"--user-data-dir={self.profile_dir}")
            
        return options

    def get_driver(self, force_new: bool = False):
        """
        Get or create a WebDriver instance.
        
        If force_new is True, a new driver will be created even if one already exists.
        Otherwise, the existing driver will be returned if it exists and the session
        has not expired.
        """
        with self._lock:
            # Return existing driver if valid
            if self.driver and not force_new and not self._is_session_expired():
                logger.info("Returning existing driver instance.")
                return self.driver

            # If session expired, quit the existing driver
            if self.driver and self._is_session_expired():
                logger.info("Session expired, creating new driver.")
                self.quit_driver()

            # Retry driver creation
            for attempt in range(1, self.retry_attempts + 1):
                try:
                    driver_path = self._download_driver_if_needed()
                    options = self._create_chrome_options()
                    service = ChromeService(executable_path=driver_path)
                    
                    # Create the appropriate driver type
                    if self.undetected_mode:
                        logger.info("Launching undetected Chrome driver...")
                        new_driver = uc.Chrome(service=service, options=options)
                    else:
                        logger.info("Launching standard Chrome driver...")
                        new_driver = webdriver.Chrome(service=service, options=options)
                    
                    logger.info("Chrome driver initialized and ready.")
                    self.session_start_time = datetime.now()
                    
                    if not force_new:
                        self.driver = new_driver
                    return new_driver
                
                except Exception as e:
                    logger.error(f"Driver initialization attempt {attempt} failed: {e}")
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_delay)
                    else:
                        logger.error("All driver initialization attempts failed")
                        return None

    # ---------------------------
    # Driver Termination and Cleanup
    # ---------------------------
    def quit_driver(self):
        """Quit the current driver and clean up resources."""
        with self._lock:
            if self.driver:
                logger.info("Quitting Chrome driver...")
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.exception(f"Error during driver quit: {e}")
                finally:
                    self.driver = None
                    self.session_start_time = None
                    logger.info("Driver session closed.")
                    if self.temp_profile and os.path.exists(self.temp_profile):
                        logger.info(f"Cleaning up temp profile: {self.temp_profile}")
                        shutil.rmtree(self.temp_profile)
                        self.temp_profile = None

    # ---------------------------
    # Cookie Management
    # ---------------------------
    def save_cookies(self):
        """Save current browser cookies to file."""
        if not self.driver:
            logger.warning("Driver not initialized. Cannot save cookies.")
            return False
        try:
            cookies = self.driver.get_cookies()
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            with open(self.cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            logger.info(f"Cookies saved to {self.cookie_file}")
            return True
        except Exception as e:
            logger.exception(f"Failed to save cookies: {e}")
            return False

    def load_cookies(self) -> bool:
        """Load cookies from file and apply to current browser session."""
        if not self.driver:
            logger.warning("Driver not initialized. Cannot load cookies.")
            return False
        if not os.path.exists(self.cookie_file):
            logger.warning(f"No cookie file found at {self.cookie_file}")
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
                    logger.warning(f"Could not add cookie: {cookie_ex}")
            self.driver.refresh()
            time.sleep(2)
            logger.info("Cookies loaded and session refreshed.")
            return True
        except Exception as e:
            logger.exception(f"Failed to load cookies: {e}")
            return False

    def clear_cookies(self) -> bool:
        """Clear all cookies from the current session."""
        if not self.driver:
            logger.warning("No active session to clear cookies")
            return False
            
        try:
            self.driver.delete_all_cookies()
            logger.info("Cookies cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Error clearing cookies: {e}")
            return False

    # ---------------------------
    # Login Verification
    # ---------------------------
    def is_logged_in(self, retries: int = 3) -> bool:
        """Check if the user is logged in to the target website."""
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
    # Advanced Operations with Retry
    # ---------------------------
    def execute_with_retry(self, action: Callable, max_retries: int = None) -> Any:
        """
        Execute an action with automatic retry on failure.
        
        Args:
            action: Callable function to execute
            max_retries: Maximum number of retry attempts (defaults to self.retry_attempts)
            
        Returns:
            The result of the action or raises the last exception
        """
        max_retries = max_retries or self.retry_attempts
        
        for attempt in range(1, max_retries + 1):
            try:
                return action()
            except Exception as e:
                logger.warning(f"Action attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    time.sleep(self.retry_delay)
                    if self._is_session_expired():
                        self.refresh_session()
                else:
                    logger.error("All action attempts failed")
                    raise

    # ---------------------------
    # Scrolling Utilities
    # ---------------------------
    def scroll_into_view(self, element):
        """Scroll an element into view smoothly."""
        if not self.driver:
            logger.warning("Driver not initialized.")
            return
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            logger.info("Scrolled element into view.")
        except Exception as e:
            logger.exception(f"Failed to scroll element into view: {e}")

    def manual_scroll(self, scroll_pause_time: float = 1.0, max_scrolls: int = 10):
        """Manually scroll down the page to load dynamic content."""
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
    # Configuration Updates
    # ---------------------------
    def update_options(self, new_options: Dict[str, Any]) -> None:
        """
        Update driver options and reinitialize if needed.
        
        Args:
            new_options: Dictionary containing options to update
        """
        with self._lock:
            restart_needed = False
            
            # Update settings that require driver restart
            restart_options = ["headless", "mobile_emulation", "undetected_mode", 
                              "additional_arguments", "profile_dir"]
            
            for option, value in new_options.items():
                if hasattr(self, option):
                    if option in restart_options and getattr(self, option) != value:
                        restart_needed = True
                    setattr(self, option, value)
                    logger.info(f"Updated option {option} to {value}")
                else:
                    logger.warning(f"Unknown option: {option}")
            
            # Restart driver if needed
            if restart_needed and self.driver:
                logger.info("Restarting driver with new options...")
                self.quit_driver()
                self.get_driver(force_new=True)
            
            logger.info("Driver options updated successfully.")

    def __del__(self):
        """Ensure driver is quit when object is garbage collected."""
        self.quit_driver()


# ---------------------------
# Example Execution
# ---------------------------
def main():
    """Example usage of the DriverManager class."""
    # Example: Create a manager instance with default settings
    with DriverManager(headless=False, undetected_mode=True) as manager:
        # Get the driver and navigate to a page
        driver = manager.get_driver()
        driver.get("https://chat.openai.com/")
        time.sleep(5)
        
        # Check login status and handle if needed
        if not manager.is_logged_in():
            logger.warning("Manual login required...")
            driver.get("https://chat.openai.com/auth/login")
            input("Press ENTER once logged in...")
            manager.save_cookies()
        else:
            logger.info("Already logged in. Continuing session...")
            manager.save_cookies()
            
        # Example: Get session info
        session_info = manager.get_session_info()
        logger.info(f"Session info: {session_info}")
        
        # Example: Scroll the page
        manager.manual_scroll(scroll_pause_time=1, max_scrolls=5)
        
        # Example: Update options
        manager.update_options({"wait_timeout": 20})
        
        logger.info("Session complete.")
        time.sleep(5)


if __name__ == "__main__":
    main()