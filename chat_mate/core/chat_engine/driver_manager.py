import os
import time
import logging
import threading
from datetime import datetime
import pickle
import tempfile
from typing import Optional, Dict, Any, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

logger = logging.getLogger("DriverManager")
logger.setLevel(logging.INFO)

class DriverManager:
    """
    Enhanced DriverManager for browser automation:
    - Singleton pattern for one driver instance
    - Support for headless mode and mobile emulation
    - Session management with automatic renewal
    - Optional undetected mode (if package available)
    - Auto-downloading ChromeDriver via webdriver_manager
    - Advanced error handling and retries
    """
    _instance = None
    _lock = threading.Lock()
    
    CHATGPT_URL = "https://chat.openai.com/"
    DEFAULT_TIMEOUT = 10
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DriverManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, headless=True, profile_dir=None, cookie_file=None, 
                 mobile_emulation=False, undetected_mode=False, 
                 timeout=DEFAULT_TIMEOUT, additional_options=None):
        """
        Initialize the driver manager with flexible configuration.
        
        Args:
            headless: Whether to run in headless mode
            profile_dir: Chrome profile directory path
            cookie_file: Path to save/load cookies
            mobile_emulation: Whether to emulate a mobile device
            undetected_mode: Use undetected_chromedriver (if available)
            timeout: WebDriverWait timeout in seconds
            additional_options: List of additional Chrome options
        """
        # Skip re-initialization if already initialized
        with self._lock:
            if self._initialized:
                return
                
            # Configuration
            self.headless = headless
            self.profile_dir = profile_dir or os.path.join(os.getcwd(), "chrome_profile")
            self.cookie_file = cookie_file
            self.mobile_emulation = mobile_emulation
            self.undetected_mode = undetected_mode and UNDETECTED_AVAILABLE
            self.timeout = timeout
            self.additional_options = additional_options or []
            
            # Runtime state
            self._driver = None
            self.session_start_time = None
            
            # Create directories
            if self.profile_dir:
                os.makedirs(self.profile_dir, exist_ok=True)
            if self.cookie_file:
                os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
                
            logger.info(f"DriverManager initialized: Headless={headless}, "
                       f"Mobile={mobile_emulation}, Undetected={self.undetected_mode}")
            self._initialized = True

    def get_driver(self, force_new=False):
        """
        Get or create a WebDriver instance.
        
        Args:
            force_new: Force creation of a new driver instance
            
        Returns:
            WebDriver instance
        """
        with self._lock:
            # Return existing driver if valid
            if self._driver and not force_new:
                logger.info("Returning existing driver instance")
                return self._driver
                
            # Initialize a new driver
            for attempt in range(3):  # Retry logic
                try:
                    logger.info(f"Initializing Chrome driver (attempt {attempt+1}/3)...")
                    self._driver = self._init_driver()
                    self.session_start_time = datetime.now()
                    logger.info("Chrome driver initialized successfully")
                    return self._driver
                except Exception as e:
                    logger.error(f"Failed to initialize Chrome driver: {e}")
                    if attempt < 2:  # Don't sleep on last attempt
                        time.sleep(2)
            
            # If all attempts failed
            logger.error("All driver initialization attempts failed")
            return None
            
    def _init_driver(self):
        """
        Initialize Selenium Chrome driver with current settings.
        """
        # Set up Chrome options
        options = self._create_chrome_options()
        
        # Get or download ChromeDriver
        driver_path = ChromeDriverManager().install()
        service = ChromeService(executable_path=driver_path)
        
        # Initialize the appropriate driver type
        if self.undetected_mode and UNDETECTED_AVAILABLE:
            logger.info("Using undetected_chromedriver mode")
            driver = uc.Chrome(options=options, service=service)
        else:
            driver = webdriver.Chrome(options=options, service=service)
            
        return driver
            
    def _create_chrome_options(self):
        """
        Create Chrome options with current settings.
        """
        options = uc.ChromeOptions() if self.undetected_mode and UNDETECTED_AVAILABLE else Options()
        
        # Set up headless mode
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
        
        # Add standard options
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox") 
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Set up mobile emulation if enabled
        if self.mobile_emulation:
            device_metrics = {"width": 375, "height": 812, "pixelRatio": 3.0}
            mobile_emulation = {
                "deviceMetrics": device_metrics,
                "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
            }
            options.add_experimental_option("mobileEmulation", mobile_emulation)
        
        # Set up profile directory
        if self.profile_dir and not self.headless:
            options.add_argument(f"--user-data-dir={self.profile_dir}")
        
        # Add additional options
        for option in self.additional_options:
            options.add_argument(option)
            
        return options
        
    def shutdown_driver(self):
        """
        Gracefully close and quit the driver.
        """
        with self._lock:
            if self._driver:
                try:
                    logger.info("Shutting down Chrome driver...")
                    self._driver.quit()
                    logger.info("Chrome driver shut down successfully")
                except Exception as e:
                    logger.warning(f"Error during driver shutdown: {e}")
                finally:
                    self._driver = None
                    self.session_start_time = None
    
    # Alias for compatibility with the monolithic version
    def quit_driver(self):
        """Alias for shutdown_driver for API compatibility."""
        self.shutdown_driver()
    
    def is_logged_in(self):
        """
        Check if the current session is authenticated.
        """
        driver = self.get_driver()
        if not driver:
            return False
            
        try:
            logger.info("Checking login status...")
            driver.get(self.CHATGPT_URL)
            time.sleep(3)
            
            # Look for chat history nav or user avatar
            selectors = [
                "nav[aria-label='Chat history']",
                "div[data-testid='user-avatar']"
            ]
            
            for selector in selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info("User is logged in")
                    return True
                    
            logger.warning("User is not logged in")
            return False
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False
            
    # --- Cookie Management ---
    
    def save_cookies(self):
        """Save current browser cookies to file."""
        if not self._driver or not self.cookie_file:
            return False
            
        try:
            cookies = self._driver.get_cookies()
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            with open(self.cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            logger.info(f"Cookies saved to {self.cookie_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False
            
    def load_cookies(self):
        """Load cookies from file and apply to current browser session."""
        if not self._driver or not self.cookie_file or not os.path.exists(self.cookie_file):
            return False
            
        try:
            with open(self.cookie_file, "rb") as f:
                cookies = pickle.load(f)
            
            current_url = self._driver.current_url
            if not current_url.startswith("http"):
                self._driver.get(self.CHATGPT_URL)
                time.sleep(2)
                
            for cookie in cookies:
                if "sameSite" in cookie:
                    cookie.pop("sameSite", None)
                try:
                    self._driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Could not add cookie: {e}")
                    
            self._driver.refresh()
            time.sleep(2)
            logger.info("Cookies loaded and session refreshed")
            return True
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False
            
    # --- Wait functions ---
    
    def wait_and_find_element(self, by, value, timeout=None):
        """Wait for an element to be present and return it."""
        timeout = timeout or self.timeout
        driver = self.get_driver()
        if not driver:
            return None
            
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except Exception as e:
            logger.warning(f"Element not found: {value} (timeout: {timeout}s)")
            return None
            
    def wait_for_url_change(self, current_url, timeout=None):
        """Wait for URL to change from the current URL."""
        timeout = timeout or self.timeout
        driver = self.get_driver()
        if not driver:
            return False
            
        try:
            return WebDriverWait(driver, timeout).until(
                lambda d: d.current_url != current_url
            )
        except Exception:
            return False
