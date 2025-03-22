import logging
from typing import Optional, Dict, Any
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from .ConfigManager import ConfigManager

class DriverSessionManager:
    """
    Manages browser driver sessions, including initialization, cleanup,
    and handling of scraping sessions.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the driver session manager.
        
        :param config_manager: The configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.driver = None
        self.session_start_time = None
        self.max_session_duration = self.config_manager.get('MAX_SESSION_DURATION', 3600)  # 1 hour
        self.retry_attempts = self.config_manager.get('DRIVER_RETRY_ATTEMPTS', 3)
        self.retry_delay = self.config_manager.get('DRIVER_RETRY_DELAY', 5)

    def initialize_driver(self, headless: bool = False) -> bool:
        """
        Initialize a new browser driver session.
        
        :param headless: Whether to run in headless mode
        :return: True if successful, False otherwise
        """
        if self.driver:
            self.logger.warning("Driver already initialized")
            return True

        for attempt in range(self.retry_attempts):
            try:
                chrome_options = Options()
                if headless:
                    chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                
                # Add any additional options from config
                for option in self.config_manager.get('CHROME_OPTIONS', []):
                    chrome_options.add_argument(option)
                
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.session_start_time = datetime.now()
                self.logger.info("Driver initialized successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Driver initialization attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error("All driver initialization attempts failed")
                    return False

    def get_driver(self) -> Optional[webdriver.Chrome]:
        """
        Get the current driver instance.
        
        :return: The current driver instance or None if not initialized
        """
        if not self.driver:
            self.logger.warning("Driver not initialized")
            return None
            
        # Check session duration
        if self._is_session_expired():
            self.logger.warning("Session expired, reinitializing driver")
            self.shutdown_driver()
            self.initialize_driver()
            
        return self.driver

    def _is_session_expired(self) -> bool:
        """
        Check if the current session has expired.
        
        :return: True if session has expired, False otherwise
        """
        if not self.session_start_time:
            return True
            
        session_duration = (datetime.now() - self.session_start_time).total_seconds()
        return session_duration > self.max_session_duration

    def shutdown_driver(self) -> None:
        """Shutdown the current driver session."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.session_start_time = None
                self.logger.info("Driver shutdown complete")
            except Exception as e:
                self.logger.error(f"Error during driver shutdown: {e}")

    def refresh_session(self) -> bool:
        """
        Refresh the current driver session.
        
        :return: True if successful, False otherwise
        """
        if not self.driver:
            self.logger.warning("No active session to refresh")
            return False
            
        try:
            self.shutdown_driver()
            return self.initialize_driver()
        except Exception as e:
            self.logger.error(f"Error refreshing session: {e}")
            return False

    def execute_with_retry(self, action: callable, max_retries: int = 3) -> Any:
        """
        Execute an action with automatic retry on failure.
        
        :param action: The action to execute
        :param max_retries: Maximum number of retry attempts
        :return: The result of the action
        """
        for attempt in range(max_retries):
            try:
                return action()
            except Exception as e:
                self.logger.warning(f"Action attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay)
                    if self._is_session_expired():
                        self.refresh_session()
                else:
                    self.logger.error("All action attempts failed")
                    raise

    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.
        
        :return: Dictionary containing session information
        """
        if not self.driver or not self.session_start_time:
            return {
                'status': 'inactive',
                'start_time': None,
                'duration': 0,
                'expired': True
            }
            
        duration = (datetime.now() - self.session_start_time).total_seconds()
        return {
            'status': 'active',
            'start_time': self.session_start_time.isoformat(),
            'duration': duration,
            'expired': self._is_session_expired()
        }

    def set_session_timeout(self, timeout: int) -> None:
        """
        Set the maximum session duration.
        
        :param timeout: Maximum session duration in seconds
        """
        self.max_session_duration = timeout
        self.logger.info(f"Session timeout set to {timeout} seconds")

    def clear_cookies(self) -> bool:
        """
        Clear all cookies from the current session.
        
        :return: True if successful, False otherwise
        """
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