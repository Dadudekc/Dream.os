"""Service for managing chat and browser interactions."""

import logging
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional, Any

from core.micro_factories.chat_factory import ChatFactory

class ChatService:
    """
    Manages the lifecycle of the ChatManager and Selenium WebDriver
    for chat execution. Provides helper methods to interact with
    the chat interface, retrieve responses, and manage driver options.
    """

    def __init__(self, config):
        """
        Initialize the ChatService.

        :param config: A configuration object or dictionary with attributes:
                       - default_model (str)
                       - headless (bool)
                       - excluded_chats (list)
                       - logger (logging.Logger instance)
        """
        self.config = config
        self.chat_manager = None
        self.logger = config.logger if hasattr(config, 'logger') else logging.getLogger("ChatService")
        self._lock = threading.Lock()

        self.logger.info("ChatService initialized.")

    def create_chat_manager(self, model=None, headless=None, excluded_chats=None,
                            timeout=180, stable_period=10, poll_interval=5):
        """
        Create or reinitialize a ChatManager instance using provided or default settings.

        :param model: AI model for chat interactions (defaults to config.default_model)
        :param headless: Run ChromeDriver in headless mode (defaults to config.headless)
        :param excluded_chats: List of chat titles to exclude (defaults to config.excluded_chats)
        :param timeout: Maximum wait time for chat responses (seconds)
        :param stable_period: Stability check period (seconds)
        :param poll_interval: Interval for polling chat status (seconds)
        """
        with self._lock:
            if self.chat_manager:
                self.logger.info("Shutting down existing ChatManager before reinitializing.")
                self.chat_manager.shutdown_driver()

            default_model = self.config.get("default_model", "gpt-4o") if hasattr(self.config, "get") else getattr(self.config, "default_model", "gpt-4o")
            default_headless = self.config.get("headless", True) if hasattr(self.config, "get") else getattr(self.config, "headless", True) 
            default_excluded_chats = self.config.get("excluded_chats", []) if hasattr(self.config, "get") else getattr(self.config, "excluded_chats", [])
            
            model = model or default_model
            headless = headless if headless is not None else default_headless
            excluded_chats = excluded_chats or default_excluded_chats

            self.chat_manager = create_chat_manager(
                config_manager=self.config,
                logger=self.logger
            )

            self.logger.info(f"ChatManager created with model='{model}', headless={headless}")

    def shutdown(self):
        """Shutdown the ChatManager and release resources."""
        with self._lock:
            if self.chat_manager:
                self.logger.info("Shutting down ChatManager...")
                self.chat_manager.shutdown_driver()
                self.chat_manager = None
                self.logger.info("ChatManager shutdown complete.")

    def is_running(self) -> bool:
        """Check if the ChatManager is currently running."""
        return self.chat_manager is not None

    def get_chat_manager(self) -> Optional[Any]:
        """
        Get the active ChatManager instance.
        
        :return: The active ChatManager instance or None if not initialized.
        """
        return self.chat_manager

    def get_chat_history(self):
        """Retrieve chat history from the ChatManager."""
        if not self.chat_manager:
            return None
        return self.chat_manager.get_chat_history()

    def send_message(self, message: str) -> bool:
        """
        Send a message via the ChatManager.
        
        :param message: The message text to send
        :return: True if sent successfully, False otherwise
        """
        if not self.chat_manager:
            self.logger.error("Cannot send message - ChatManager not initialized")
            return False
        try:
            self.chat_manager.send_message(message)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False

    def get_response(self) -> Optional[str]:
        """
        Retrieve the latest response from the ChatManager.
        
        :return: Response text or None if not available
        """
        if not self.chat_manager:
            return None
        return self.chat_manager.get_response()

    def get_model(self) -> Optional[str]:
        """Get the AI model used by the ChatManager."""
        if not self.chat_manager:
            return None
        return self.chat_manager.model

    def get_config(self):
        """Get the service configuration."""
        return self.config

    def _get_driver_options(self, headless=True) -> Options:
        """
        Configure ChromeOptions for Selenium WebDriver.

        :param headless: Whether to run the browser in headless mode
        :return: Configured ChromeOptions
        """
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return options

    def get_driver(self, headless=True) -> Optional[webdriver.Chrome]:
        """
        Create and return a new Selenium Chrome WebDriver instance.

        :param headless: Whether to run the browser in headless mode
        :return: Chrome WebDriver instance or None if initialization fails
        """
        try:
            service = self._get_driver_service()
            options = self._get_driver_options(headless=headless)
            driver = webdriver.Chrome(service=service, options=options)
            self.logger.info("Chrome WebDriver initialized successfully.")
            return driver
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            return None

    def _get_driver_service(self) -> Service:
        """Create a Selenium Service using ChromeDriver."""
        driver_path = ChromeDriverManager().install()
        return Service(driver_path) 
