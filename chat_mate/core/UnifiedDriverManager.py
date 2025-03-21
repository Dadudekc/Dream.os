import threading
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def default_options() -> Dict[str, Any]:
    """Default Chrome options configuration."""
    options = {
        "headless": False,
        "user_data_dir": None,
        "window_size": (1920, 1080),
        "disable_gpu": True,
        "no_sandbox": True,
        "disable_dev_shm": True,
        "additional_arguments": []
    }
    return options

def create_driver(options: Dict[str, Any]) -> webdriver.Chrome:
    """
    Create a new Chrome WebDriver instance with the specified options.
    
    Args:
        options: Dictionary of driver configuration options
        
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
    """
    chrome_options = Options()
    
    if options.get("headless", False):
        chrome_options.add_argument("--headless")
        
    if options.get("user_data_dir"):
        chrome_options.add_argument(f"--user-data-dir={options['user_data_dir']}")
        
    if options.get("window_size"):
        width, height = options["window_size"]
        chrome_options.add_argument(f"--window-size={width},{height}")
        
    if options.get("disable_gpu", True):
        chrome_options.add_argument("--disable-gpu")
        
    if options.get("no_sandbox", True):
        chrome_options.add_argument("--no-sandbox")
        
    if options.get("disable_dev_shm", True):
        chrome_options.add_argument("--disable-dev-shm-usage")
        
    # Add any additional arguments
    for arg in options.get("additional_arguments", []):
        chrome_options.add_argument(arg)
        
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("✅ Chrome WebDriver initialized successfully")
        return driver
    except WebDriverException as e:
        logger.error(f"❌ Failed to initialize Chrome WebDriver: {e}")
        raise

class UnifiedDriverManager:
    """
    Singleton class for managing Selenium WebDriver instances.
    Ensures only one WebDriver instance exists across the application.
    """
    _instance: Optional['UnifiedDriverManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls, driver_options: Dict[str, Any] = None) -> 'UnifiedDriverManager':
        """
        Create or return the existing Singleton instance.
        Thread-safe implementation using a Lock.
        
        Args:
            driver_options: Optional dictionary of driver configuration options
            
        Returns:
            UnifiedDriverManager: The Singleton instance
        """
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance
    
    def __init__(self, driver_options: Dict[str, Any] = None):
        """
        Initialize the driver manager if not already initialized.
        
        Args:
            driver_options: Optional dictionary of driver configuration options
        """
        with self._lock:
            if not self._initialized:
                self.driver_options = driver_options or default_options()
                self.driver: Optional[webdriver.Chrome] = None
                self._initialized = True
                logger.info("🔧 UnifiedDriverManager initialized")
    
    def init_driver(self) -> None:
        """Initialize the WebDriver with current options if not already running."""
        with self._lock:
            if self.driver is None:
                try:
                    self.driver = create_driver(self.driver_options)
                    logger.info("🚀 WebDriver instance created")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize WebDriver: {e}")
                    raise
    
    def get_driver(self) -> Optional[webdriver.Chrome]:
        """
        Get the current WebDriver instance, initializing if necessary.
        
        Returns:
            webdriver.Chrome: The current WebDriver instance
        """
        with self._lock:
            if self.driver is None:
                self.init_driver()
            return self.driver
    
    def update_options(self, new_options: Dict[str, Any]) -> None:
        """
        Update driver options and reinitialize the driver if necessary.
        
        Args:
            new_options: Dictionary of new driver options to apply
        """
        with self._lock:
            self.driver_options.update(new_options)
            if self.driver is not None:
                self.quit()
                self.init_driver()
                logger.info("🔄 WebDriver reinitialized with new options")
    
    def quit(self) -> None:
        """Safely quit the current WebDriver instance."""
        with self._lock:
            if self.driver is not None:
                try:
                    self.driver.quit()
                    logger.info("👋 WebDriver instance closed")
                except Exception as e:
                    logger.error(f"❌ Error closing WebDriver: {e}")
                finally:
                    self.driver = None
    
    def __del__(self):
        """Ensure driver is quit when the manager is destroyed."""
        self.quit() 