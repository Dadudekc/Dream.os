import os
from typing import Dict, Any, Optional, List, Type
from selenium.webdriver.remote.webdriver import WebDriver
from core.logging.LoggingService import LoggingService
from core.DriverManager import DriverManager
from .BasePlatformLoginService import BasePlatformLoginService

class SocialLoginManager:
    """
    Manages social platform login services and orchestrates their lifecycle.
    Provides a unified interface for managing social platform connections.
    """

    def __init__(self, logger: Optional[LoggingService] = None):
        """
        Initialize the social login manager.

        Args:
            logger: Optional LoggingService instance for logging
        """
        self.logger = logger or LoggingService(__name__)
        self.driver_manager = DriverManager()
        self.driver = None
        self.services: Dict[str, BasePlatformLoginService] = {}
        self._registered_service_classes: Dict[str, Type[BasePlatformLoginService]] = {}

    def register_service(self, platform: str, service_class: Type[BasePlatformLoginService]) -> None:
        """
        Register a platform-specific login service class.

        Args:
            platform: Platform identifier (e.g., 'discord', 'twitter')
            service_class: The service class to register
        """
        self._registered_service_classes[platform.lower()] = service_class
        self.logger.info(f"Registered login service for platform: {platform}")

    def initialize_services(self, platforms: Optional[List[str]] = None) -> None:
        """
        Initialize login services for specified platforms or all registered platforms.

        Args:
            platforms: Optional list of platform identifiers to initialize
        """
        if not self.driver:
            self.driver = self.driver_manager.get_driver()

        target_platforms = [p.lower() for p in (platforms or self._registered_service_classes.keys())]
        
        for platform in target_platforms:
            if platform not in self._registered_service_classes:
                self.logger.warning(f"No login service registered for platform: {platform}")
                continue

            service_class = self._registered_service_classes[platform]
            self.services[platform] = service_class(driver=self.driver, logger=self.logger)
            self.logger.info(f"Initialized login service for platform: {platform}")

    def connect_platform(self, platform: str, credentials: Dict[str, Any]) -> bool:
        """
        Connect to a specific platform using provided credentials.

        Args:
            platform: Platform identifier
            credentials: Platform-specific credentials

        Returns:
            bool: True if connection successful, False otherwise
        """
        platform = platform.lower()
        if platform not in self.services:
            self.logger.error(f"No login service initialized for platform: {platform}")
            return False

        return self.services[platform].connect(credentials)

    def disconnect_platform(self, platform: str) -> bool:
        """
        Disconnect from a specific platform.

        Args:
            platform: Platform identifier

        Returns:
            bool: True if disconnection successful, False otherwise
        """
        platform = platform.lower()
        if platform not in self.services:
            self.logger.error(f"No login service initialized for platform: {platform}")
            return False

        return self.services[platform].disconnect()

    def test_platform_connection(self, platform: str) -> bool:
        """
        Test connection to a specific platform.

        Args:
            platform: Platform identifier

        Returns:
            bool: True if connection is valid, False otherwise
        """
        platform = platform.lower()
        if platform not in self.services:
            self.logger.error(f"No login service initialized for platform: {platform}")
            return False

        return self.services[platform].test_connection()

    def get_platform_status(self, platform: str) -> Dict[str, Any]:
        """
        Get connection status for a specific platform.

        Args:
            platform: Platform identifier

        Returns:
            Dict containing platform connection status
        """
        platform = platform.lower()
        if platform not in self.services:
            return {
                "is_connected": False,
                "last_error": "Service not initialized",
                "session_data": {}
            }

        return self.services[platform].get_connection_status()

    def get_all_platform_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get connection status for all initialized platforms.

        Returns:
            Dict mapping platform identifiers to their status dictionaries
        """
        return {
            platform: service.get_connection_status()
            for platform, service in self.services.items()
        }

    def cleanup(self) -> None:
        """Clean up resources and disconnect all services."""
        for platform, service in self.services.items():
            try:
                if service.is_connected:
                    service.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting from {platform}: {e}")

        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None 