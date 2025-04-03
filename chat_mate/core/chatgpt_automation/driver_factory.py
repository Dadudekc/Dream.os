"""
Factory class for creating and managing ChatGPT drivers.
"""

import logging
from chat_mate.core.openai import OpenAIClient
from .local_llm_engine import LocalLLMEngine
from core.chatgpt_automation.config import PROFILE_DIR, CHATGPT_HEADLESS, CHROMEDRIVER_PATH
from typing import Optional

class DriverFactory:
    """Factory class for creating and managing ChatGPT drivers."""

    def __init__(
        self,
        use_local_llm: bool = False,
        model_name: str = 'mistral',
        profile_dir: str = PROFILE_DIR,
        headless: bool = CHATGPT_HEADLESS,
        driver_path: Optional[str] = CHROMEDRIVER_PATH
    ):
        """Initialize the driver factory.

        Args:
            use_local_llm (bool): Whether to use local LLM instead of OpenAI API.
            model_name (str): The name of the model to use for local LLM.
            profile_dir (str): Chrome profile directory path for ChatGPT automation.
            headless (bool): Whether to launch the browser in headless mode.
            driver_path (Optional[str]): Path to the ChromeDriver binary.
        """
        self.logger = logging.getLogger(__name__)
        self.use_local_llm = use_local_llm
        self.model_name = model_name
        self.profile_dir = profile_dir
        self.headless = headless
        self.driver_path = driver_path
        self.driver = None

    def create_driver(self):
        """Create a new ChatGPT driver instance.

        Returns:
            OpenAIClient | LocalLLMEngine: The created driver instance.
        """
        if self.use_local_llm:
            self.logger.info(f"Creating LocalLLMEngine with model: {self.model_name}")
            try:
                self.driver = LocalLLMEngine(model=self.model_name)
                self.logger.info("✅ Local LLM engine created successfully.")
                return self.driver
            except Exception as e:
                self.logger.error(f"❌ Failed to create LocalLLMEngine: {e}")
                raise
        else:
            self.logger.info("Creating OpenAIClient driver")
            try:
                self.driver = OpenAIClient(
                    profile_dir=self.profile_dir,
                    headless=self.headless,
                    driver_path=self.driver_path
                )
                self.logger.info("✅ OpenAIClient driver created successfully.")
                return self.driver
            except Exception as e:
                self.logger.error(f"❌ Failed to create OpenAIClient: {e}")
                raise

    def get_driver(self):
        """Get the current driver instance or create a new one.

        Returns:
            OpenAIClient | LocalLLMEngine: The current or newly created driver instance.
        """
        if not self.driver:
            self.driver = self.create_driver()

        if not self.driver:
            raise RuntimeError("Driver creation failed. No driver instance available.")

        return self.driver

    def close_driver(self):
        """Close the current driver instance."""
        if self.driver:
            self.driver.close()
            self.driver = None
