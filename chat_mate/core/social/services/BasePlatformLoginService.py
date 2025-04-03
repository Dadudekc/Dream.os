from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from core.logging.LoggingService import LoggingService

class BasePlatformLoginService(ABC):
    """
    Abstract base class for platform-specific login services.
    Defines the common interface that all social platform login services must implement.
    """

    def __init__(self, driver: Optional[WebDriver] = None, logger: Optional[LoggingService] = None):
        """
        Initialize the login service.

        Args:
            driver: Optional Selenium WebDriver instance for browser automation
            logger: Optional LoggingService instance for logging
        """
        self.driver = driver
        self.logger = logger or LoggingService(__name__)
        self.is_connected = False
        self.last_error = None
        self.session_data = {}

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Get the name of the platform (e.g., 'Discord', 'Twitter')."""
        pass

    @abstractmethod
    def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Attempt to connect to the platform using provided credentials.

        Args:
            credentials: Dictionary containing platform-specific credentials

        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the platform and clean up resources.

        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the current connection is valid.

        Returns:
            bool: True if connection is valid, False otherwise
        """
        pass

    @abstractmethod
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed status of the current connection.

        Returns:
            Dict containing:
                - is_connected (bool)
                - last_error (Optional[str])
                - session_data (Dict[str, Any])
                - additional platform-specific status info
        """
        pass

    def _log_error(self, error: str) -> None:
        """Log an error and update the last_error field."""
        self.last_error = error
        self.logger.error(f"[{self.platform_name}] {error}")

    def _log_info(self, message: str) -> None:
        """Log an informational message."""
        self.logger.info(f"[{self.platform_name}] {message}")

    def _update_connection_state(self, is_connected: bool, error: Optional[str] = None) -> None:
        """Update the connection state and optionally log an error."""
        self.is_connected = is_connected
        if error:
            self._log_error(error)
        elif is_connected:
            self._log_info("Connection established successfully")
        else:
            self._log_info("Disconnected from platform") 