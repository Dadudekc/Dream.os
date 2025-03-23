import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import time
from selenium import webdriver

from .DriverManager import DriverManager
from .ConfigManager import ConfigManager

class DriverSessionManager:
    """
    Backward compatibility wrapper for the legacy DriverSessionManager.
    This class maintains the same interface as the original DriverSessionManager 
    but delegates all functionality to the new unified DriverManager.
    
    DO NOT use this class for new code. Use DriverManager directly instead.
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
        
        # Extract configuration from config_manager
        self.max_session_duration = self.config_manager.get('MAX_SESSION_DURATION', 3600)
        self.retry_attempts = self.config_manager.get('DRIVER_RETRY_ATTEMPTS', 3)
        self.retry_delay = self.config_manager.get('DRIVER_RETRY_DELAY', 5)
        
        # Initialize the unified driver manager
        self._driver_manager = DriverManager(
            headless=self.config_manager.get('HEADLESS_MODE', False),
            max_session_duration=self.max_session_duration,
            retry_attempts=self.retry_attempts,
            retry_delay=self.retry_delay,
            additional_arguments=self.config_manager.get('CHROME_OPTIONS', []),
            undetected_mode=self.config_manager.get('USE_UNDETECTED_DRIVER', True)
        )
        
        self.logger.info("DriverSessionManager initialized (compatibility wrapper)")

    def initialize_driver(self, headless: bool = False) -> bool:
        """
        Initialize a new browser driver session.
        
        :param headless: Whether to run in headless mode
        :return: True if successful, False otherwise
        """
        try:
            # Update headless mode if different from initial setting
            if headless != self._driver_manager.headless:
                self._driver_manager.update_options({"headless": headless})
                
            # Get the driver
            self.driver = self._driver_manager.get_driver(force_new=True)
            self.session_start_time = datetime.now()
            
            return self.driver is not None
        except Exception as e:
            self.logger.error(f"Failed to initialize driver: {e}")
            return False

    def get_driver(self) -> Optional[webdriver.Chrome]:
        """
        Get the current driver instance.
        
        :return: The current driver instance or None if not initialized
        """
        try:
            # Get the driver from the unified manager
            self.driver = self._driver_manager.get_driver()
            
            # Update the session start time if it's a new driver
            if self.driver and not self.session_start_time:
                self.session_start_time = datetime.now()
                
            return self.driver
        except Exception as e:
            self.logger.error(f"Error getting driver: {e}")
            return None

    def _is_session_expired(self) -> bool:
        """
        Check if the current session has expired.
        
        :return: True if session has expired, False otherwise
        """
        return self._driver_manager._is_session_expired()

    def shutdown_driver(self) -> None:
        """Shutdown the current driver session."""
        try:
            self._driver_manager.quit_driver()
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
        try:
            result = self._driver_manager.refresh_session()
            if result:
                self.driver = self._driver_manager.driver
                self.session_start_time = datetime.now()
            return result
        except Exception as e:
            self.logger.error(f"Error refreshing session: {e}")
            return False

    def execute_with_retry(self, action: Callable, max_retries: int = 3) -> Any:
        """
        Execute an action with automatic retry on failure.
        
        :param action: The action to execute
        :param max_retries: Maximum number of retry attempts
        :return: The result of the action
        """
        return self._driver_manager.execute_with_retry(action, max_retries)

    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.
        
        :return: Dictionary containing session information
        """
        return self._driver_manager.get_session_info()

    def set_session_timeout(self, timeout: int) -> None:
        """
        Set the maximum session duration.
        
        :param timeout: Maximum session duration in seconds
        """
        self._driver_manager.set_session_timeout(timeout)
        self.max_session_duration = timeout

    def clear_cookies(self) -> bool:
        """
        Clear all cookies from the current session.
        
        :return: True if successful, False otherwise
        """
        return self._driver_manager.clear_cookies() 