import logging
from core.chatgpt_automation.local_llm_engine import LocalLLMEngine
from core.chatgpt_automation.OpenAIClient import OpenAIClient
from core.chatgpt_automation.config import PROFILE_DIR, CHATGPT_HEADLESS, CHROMEDRIVER_PATH

class DriverFactory:
    def __init__(self, use_local_llm=True, model_name='mistral'):
        self.logger = logging.getLogger(__name__)
        self.use_local_llm = use_local_llm
        self.model_name = model_name

    def create_driver(self):
        if self.use_local_llm:
            self.logger.info(f"Creating LocalLLMEngine with model: {self.model_name}")
            try:
                driver = LocalLLMEngine(model=self.model_name)
                self.logger.info("✅ Local LLM engine created successfully.")
                return driver
            except Exception as e:
                self.logger.error(f"❌ Failed to create LocalLLMEngine: {e}")
                raise
        else:
            self.logger.info("Creating OpenAIClient driver")
            try:
                # Create client without auto-login
                openai_client = OpenAIClient(
                    profile_dir=PROFILE_DIR,
                    headless=CHATGPT_HEADLESS,
                    driver_path=CHROMEDRIVER_PATH
                )
                self.logger.info("✅ OpenAIClient driver created successfully.")
                return openai_client.driver
            except Exception as e:
                self.logger.error(f"❌ Failed to create OpenAIClient: {e}")
                raise
