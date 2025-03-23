from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class DreamscapeService:
    def __init__(self, config):
        self.config = config
        self.chat_manager = None
        self.logger = config.logger

    def create_chat_manager(self, model=None, headless=None, excluded_chats=None,
                            timeout=180, stable_period=10, poll_interval=5):
        """
        Create or re-create a ChatManager instance using provided or configuration defaults.
        """
        if self.chat_manager:
            self.chat_manager.shutdown_driver()

        model = model or self.config.default_model
        headless = headless if headless is not None else self.config.headless
        excluded_chats = excluded_chats or self.config.excluded_chats

        driver_options = {
            "headless": headless,
            "window_size": (1920, 1080),
            "disable_gpu": True,
            "no_sandbox": True,
            "disable_dev_shm": True
        }

        self.chat_manager = ChatManager(
            driver_options=driver_options,
            excluded_chats=excluded_chats,
            model=model,
            timeout=timeout,
            stable_period=stable_period,
            poll_interval=poll_interval,
            headless=headless
        )

        self.logger.info(f"ChatManager created with model '{model}' and headless={headless}")

    def shutdown(self):
        if self.chat_manager:
            self.chat_manager.shutdown_driver()
            self.chat_manager = None

    def is_running(self):
        return self.chat_manager is not None

    def get_driver(self):
        return self._require_chat_manager().driver

    def get_chat_history(self):
        return self._require_chat_manager().get_chat_history()

    def send_message(self, message):
        self._require_chat_manager().send_message(message)

    def get_response(self):
        return self._require_chat_manager().get_response()

    def get_model(self):
        return self._require_chat_manager().model

    def get_config(self):
        return self.config

    def get_driver_options(self):
        return self._require_chat_manager().driver_options

    def get_excluded_chats(self):
        return self._require_chat_manager().excluded_chats

    def get_timeout(self):
        return self._require_chat_manager().timeout

    def get_stable_period(self):
        return self._require_chat_manager().stable_period

    def get_poll_interval(self):
        return self._require_chat_manager().poll_interval

    def get_headless(self):
        return self._require_chat_manager().headless

    # Chrome Driver Management Helpers
    def get_driver_manager(self):
        return ChromeDriverManager()

    def get_driver_service(self):
        return Service(ChromeDriverManager().install())

    def get_driver_options(self, headless=True):
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return options

    def get_driver(self, headless=True):
        return webdriver.Chrome(
            service=self.get_driver_service(),
            options=self.get_driver_options(headless=headless)
        )

    # Internal helper to ensure ChatManager exists
    def _require_chat_manager(self):
        if not self.chat_manager:
            raise Exception("ChatManager not initialized")
        return self.chat_manager
