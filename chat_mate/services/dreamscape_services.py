import logging
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Import your ChatManager (ensure it is implemented in your project)
from core.ChatManager import ChatManager

class DreamscapeService:
    """
    Manages the lifecycle of the ChatManager and Selenium WebDriver
    for chat execution. Provides helper methods to interact with
    the chat interface, retrieve responses, and manage driver options.
    """

    def __init__(self, config):
        """
        Initialize the DreamscapeService.

        :param config: A configuration object or dictionary with attributes:
                       - default_model (str)
                       - headless (bool)
                       - excluded_chats (list)
                       - logger (logging.Logger instance)
        """
        self.config = config
        self.chat_manager = None
        self.logger = config.logger if hasattr(config, 'logger') else logging.getLogger("DreamscapeService")
        self._lock = threading.Lock()

        self.logger.info("DreamscapeService initialized.")

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

            model = model or self.config.default_model
            headless = headless if headless is not None else self.config.headless
            excluded_chats = excluded_chats or self.config.excluded_chats

            driver_options = self._get_driver_options(headless)

            self.chat_manager = ChatManager(
                driver_options=driver_options,
                excluded_chats=excluded_chats,
                model=model,
                timeout=timeout,
                stable_period=stable_period,
                poll_interval=poll_interval,
                headless=headless
            )

            self.logger.info(f"ChatManager created with model='{model}', headless={headless}")

    def shutdown(self):
        """
        Shutdown the ChatManager and release resources.
        """
        with self._lock:
            if self.chat_manager:
                self.logger.info("Shutting down ChatManager...")
                self.chat_manager.shutdown_driver()
                self.chat_manager = None
                self.logger.info("ChatManager shutdown complete.")

    def is_running(self) -> bool:
        """
        Check if the ChatManager is currently running.

        :return: True if active, False otherwise.
        """
        return self.chat_manager is not None

    def get_chat_manager(self) -> ChatManager:
        """
        Ensure the ChatManager is initialized and return it.

        :return: The active ChatManager instance.
        :raises RuntimeError: If ChatManager is not initialized.
        """
        if not self.chat_manager:
            raise RuntimeError("ChatManager is not initialized. Call create_chat_manager() first.")
        return self.chat_manager

    def get_chat_history(self):
        """
        Retrieve chat history from the ChatManager.

        :return: Chat history data.
        """
        return self.get_chat_manager().get_chat_history()

    def send_message(self, message):
        """
        Send a message via the ChatManager.

        :param message: The message text to send.
        """
        self.get_chat_manager().send_message(message)

    def get_response(self):
        """
        Retrieve the latest response from the ChatManager.

        :return: Response text.
        """
        return self.get_chat_manager().get_response()

    def get_model(self):
        """
        Retrieve the AI model used by the ChatManager.

        :return: Model name.
        """
        return self.get_chat_manager().model

    def get_config(self):
        """
        Retrieve the service configuration.

        :return: Configuration object.
        """
        return self.config

    def get_driver_options(self, headless=True):
        """
        Retrieve Selenium WebDriver options.

        :param headless: Whether to run in headless mode.
        :return: ChromeOptions object.
        """
        return self._get_driver_options(headless)

    def _get_driver_options(self, headless=True) -> Options:
        """
        Internal method to configure ChromeOptions for Selenium WebDriver.

        :param headless: Whether to run the browser in headless mode.
        :return: Configured ChromeOptions.
        """
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return options

    def get_driver(self, headless=True) -> webdriver.Chrome:
        """
        Create and return a new Selenium Chrome WebDriver instance.

        :param headless: Whether to run the browser in headless mode.
        :return: Chrome WebDriver instance.
        :raises Exception: If WebDriver initialization fails.
        """
        try:
            service = self._get_driver_service()
            options = self._get_driver_options(headless=headless)
            driver = webdriver.Chrome(service=service, options=options)
            self.logger.info("Chrome WebDriver initialized successfully.")
            return driver
        except Exception as e:
            self.logger.error("Failed to initialize Chrome WebDriver: %s", e)
            raise

    def _get_driver_service(self) -> Service:
        """
        Internal method to create a Selenium Service using ChromeDriver.

        :return: Service instance.
        """
        driver_path = ChromeDriverManager().install()
        return Service(driver_path)

    def get_excluded_chats(self):
        """
        Retrieve the list of excluded chats from the ChatManager.

        :return: List of excluded chats.
        """
        return self.get_chat_manager().excluded_chats

    def get_timeout(self):
        """
        Retrieve the timeout setting from the ChatManager.

        :return: Timeout in seconds.
        """
        return self.get_chat_manager().timeout

    def get_stable_period(self):
        """
        Retrieve the stable period setting from the ChatManager.

        :return: Stable period in seconds.
        """
        return self.get_chat_manager().stable_period

    def get_poll_interval(self):
        """
        Retrieve the polling interval setting from the ChatManager.

        :return: Polling interval in seconds.
        """
        return self.get_chat_manager().poll_interval

    def get_headless(self):
        """
        Retrieve the headless mode setting from the ChatManager.

        :return: True if headless, False otherwise.
        """
        return self.get_chat_manager().headless

# ---------------------------
# Example Usage as a Standalone Script
# ---------------------------
if __name__ == "__main__":
    # Create a dummy configuration object for demonstration.
    class DummyConfig:
        default_model = "gpt-4"
        headless = True
        excluded_chats = []
        logger = logging.getLogger("DreamscapeService")
    
    logging.basicConfig(level=logging.INFO)
    config = DummyConfig()
    service = DreamscapeService(config)
    
    # Create a ChatManager instance (ensure your ChatManager implementation is available)
    try:
        service.create_chat_manager()
        # If your ChatManager has been implemented, you can interact with it here.
        # For example, send a test message:
        service.send_message("Hello, Chat!")
        response = service.get_response()
        service.logger.info("Chat response: %s", response)
    except Exception as e:
        service.logger.error("Error creating ChatManager: %s", e)
    
    # Test Selenium WebDriver helper
    try:
        driver = service.get_driver(headless=True)
        service.logger.info("Driver title: %s", driver.title)
        driver.quit()
    except Exception as e:
        service.logger.error("Error during driver test: %s", e)
