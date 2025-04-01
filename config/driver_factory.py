"""
WebDriver factory for creating and managing browser driver instances.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class DriverFactory:
    """Factory class for creating and managing WebDriver instances."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize the DriverFactory.
        
        Args:
            config: Configuration dictionary containing webdriver settings
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.driver_cache = {}
        
        # Ensure cache directory exists
        cache_dir = self.config.get("webdriver", {}).get("cache_dir", ".cache/selenium")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def create_driver(self, headless: Optional[bool] = None) -> webdriver.Chrome:
        """
        Create a new Chrome WebDriver instance.
        
        Args:
            headless: Override the default headless setting from config
            
        Returns:
            Chrome WebDriver instance
            
        Raises:
            Exception: If driver creation fails
        """
        try:
            options = self._get_chrome_options(headless)
            service = self._get_driver_service()
            
            driver = webdriver.Chrome(service=service, options=options)
            self.logger.info("Chrome WebDriver initialized successfully")
            return driver
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
            raise
    
    def _get_chrome_options(self, headless: Optional[bool] = None) -> Options:
        """
        Configure Chrome options based on configuration.
        
        Args:
            headless: Override the default headless setting
            
        Returns:
            Configured ChromeOptions instance
        """
        webdriver_config = self.config.get("webdriver", {})
        options = Options()
        
        # Set headless mode
        use_headless = headless if headless is not None else webdriver_config.get("headless", True)
        if use_headless:
            options.add_argument("--headless")
        
        # Set window size
        window_size = webdriver_config.get("window_size", (1920, 1080))
        options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
        
        # Add other Chrome options from config
        if webdriver_config.get("disable_gpu", True):
            options.add_argument("--disable-gpu")
        if webdriver_config.get("no_sandbox", True):
            options.add_argument("--no-sandbox")
        if webdriver_config.get("disable_dev_shm", True):
            options.add_argument("--disable-dev-shm-usage")
        
        return options
    
    def _get_driver_service(self) -> Service:
        """
        Create a ChromeDriver service using WebDriver Manager.
        
        Returns:
            Configured Service instance
        """
        driver_path = ChromeDriverManager(
            path=str(self.cache_dir)
        ).install()
        return Service(driver_path)
    
    def get_cached_driver(self, cache_key: str = "default") -> Optional[webdriver.Chrome]:
        """
        Get a cached driver instance if available.
        
        Args:
            cache_key: Key to identify the cached driver
            
        Returns:
            Cached Chrome WebDriver instance or None if not found
        """
        return self.driver_cache.get(cache_key)
    
    def cache_driver(self, driver: webdriver.Chrome, cache_key: str = "default") -> None:
        """
        Cache a driver instance for reuse.
        
        Args:
            driver: Chrome WebDriver instance to cache
            cache_key: Key to identify the cached driver
        """
        self.driver_cache[cache_key] = driver
    
    def clear_cache(self) -> None:
        """Clear all cached driver instances."""
        for driver in self.driver_cache.values():
            try:
                driver.quit()
            except Exception as e:
                self.logger.warning(f"Error closing cached driver: {str(e)}")
        self.driver_cache.clear()
    
    def __del__(self):
        """Ensure all drivers are closed on deletion."""
        self.clear_cache() 
