import os
import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections import defaultdict

from utils.path_manager import PathManager

logger = logging.getLogger(__name__)

class SimpleDriverManager:
    """
    A simplified driver manager that doesn't auto-start the browser
    """
    def __init__(self, headless=True, user_data_dir=None):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.driver = None
        self.current_url = None
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"SimpleDriverManager initialized: Headless={headless}, UserDataDir={user_data_dir}")
    
    def start_browser(self):
        """Start a new browser session if not already running"""
        if self.driver:
            self.logger.info("Browser already running")
            return False

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            import os
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            # Add user data directory for persistence
            if self.user_data_dir:
                # Use provided user data directory
                user_data_dir = self.user_data_dir
            else:
                # Use default from PathManager
                user_data_dir = PathManager.get_path('drivers', 'chrome_profile/openai')
                
            options.add_argument(f"--user-data-dir={user_data_dir}")
            
            # Try multiple methods to get a working ChromeDriver
            driver_path = None
            
            # Method 1: Look for chromedriver in our drivers directory
            local_driver_path = PathManager.get_path('drivers', 'chromedriver.exe')
            if os.path.exists(local_driver_path):
                driver_path = local_driver_path
                self.logger.info(f"Using local ChromeDriver at: {driver_path}")
                service = Service(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                # Method 2: Try webdriver_manager as fallback
                try:
                    self.logger.info("Local ChromeDriver not found, using webdriver_manager...")
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
                except Exception as e:
                    self.logger.error(f"Failed to get ChromeDriver using webdriver_manager: {e}")
                    
                    # Method 3: Last resort - try without specifying driver path
                    self.logger.info("Trying to initialize Chrome without specific driver path...")
                    self.driver = webdriver.Chrome(options=options)
            
            if self.driver:
                self.logger.info("Browser started successfully")
                return True
            else:
                self.logger.error("Failed to start browser")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting browser: {e}")
            return False
    
    def close(self):
        """Close the browser if it's running"""
        if self.driver:
            logger.info("Closing browser...")
            self.driver = None

class SimpleChatEngineManager:
    """
    A simplified version of ChatEngineManager that can accept parameters
    and doesn't auto-start the browser.
    """
    
    def __init__(self, config: Dict[str, Any], base_dir: Optional[str] = None):
        """
        Initialize the SimpleChatEngineManager.
        
        Args:
            config: Configuration dictionary with settings for all components
            base_dir: Base directory for file operations (default: current working directory)
        """
        self.config = config
        self.base_dir = base_dir or os.getcwd()
        
        # Initialize driver manager but don't start browser yet
        self._driver_manager = SimpleDriverManager(
            headless=self.config.get('headless', False),
            user_data_dir=self.config.get('user_data_dir', None)
        )
        
        self._is_initialized = False
        logger.info("SimpleChatEngineManager instantiated")
    
    def initialize(self) -> bool:
        """
        Initialize all components but don't start the browser.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing SimpleChatEngineManager components")
            # We're not doing much here in this simplified version
            self._is_initialized = True
            logger.info("SimpleChatEngineManager initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SimpleChatEngineManager: {str(e)}", exc_info=True)
            self._is_initialized = False
            return False
    
    def shutdown(self) -> None:
        """
        Gracefully shut down all components.
        """
        logger.info("Shutting down SimpleChatEngineManager")
        
        # Shutdown driver manager
        if self._driver_manager:
            try:
                self._driver_manager.close()
            except Exception as e:
                logger.warning(f"Error closing driver manager: {str(e)}")
            self._driver_manager = None
        
        self._is_initialized = False
        logger.info("SimpleChatEngineManager shutdown complete")
    
    def get_driver_manager(self):
        """Get the driver manager instance."""
        return self._driver_manager
    
    def is_initialized(self) -> bool:
        """Check if the manager has been successfully initialized."""
        return self._is_initialized 