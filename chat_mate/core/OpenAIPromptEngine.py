import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from jinja2 import Environment, FileSystemLoader
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from chat_mate_config import Config
from chat_mate_config import (CUSTOM_GPT_URL, PROMPT_INPUT_SELECTOR, RESPONSE_CONTAINER_SELECTOR,
                               STOP_BUTTON_XPATH, RETRY_ATTEMPTS, RETRY_DELAY_SECONDS, INTERACTION_LOG_PATH)

logger = logging.getLogger("OpenAIPromptEngine")
logger.setLevel(logging.INFO)


class OpenAIPromptEngine:
    """
    OpenAIPromptEngine:
      - Renders prompts using Jinja2 templates.
      - Uses Selenium to interact with a custom GPT endpoint.
      - Logs interactions for reinforcement learning.
      - Optionally triggers voice automation.
    """
    def __init__(
        self,
        driver,
        template_dir: str = "chat_mate/templates/prompt_templates",
        tts_function: Optional[Callable[[str], None]] = None  # TTS function, if available
    ):
        self.driver = driver
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
        self.tts_function = tts_function
        logger.info(" OpenAIPromptEngine initialized using custom GPT scraper.")

    def _is_driver_alive(self) -> bool:
        """
        Health check for the Selenium driver.
        """
        try:
            _ = self.driver.title  # simple call to ensure the driver is active
            return True
        except Exception as e:
            logger.error(f"Driver health check failed: {e}")
            return False

    def render_prompt(
        self,
        template_name: str,
        memory_state: Dict[str, Any],
        additional_context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render a prompt from a Jinja2 template.
        """
        try:
            template = self.jinja_env.get_template(template_name)
        except Exception as e:
            logger.error(f" Failed to load template '{template_name}': {e}")
            raise e

        context = {
            "CURRENT_MEMORY_STATE": json.dumps(memory_state, indent=2),
            "ADDITIONAL_CONTEXT": additional_context or "",
            "METADATA": metadata or {}
        }
        prompt = template.render(context)
        logger.info(f" Prompt rendered from template '{template_name}'.")
        return prompt

    def _retry(self, func, *args, **kwargs):
        """
        A generic retry/backoff wrapper.
        """
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Attempt {attempt} failed for {func.__name__}: {e}")
                if attempt < RETRY_ATTEMPTS:
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    raise

    def send_prompt(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """
        Uses Selenium to open the custom GPT URL, send the rendered prompt,
        wait for generation to complete, and scrape the response.
        """
        if not self._is_driver_alive():
            logger.error("Selenium driver is not alive. Aborting prompt execution.")
            return None

        try:
            self._retry(self.driver.get, CUSTOM_GPT_URL)
            logger.info(f"Navigated to custom GPT at {CUSTOM_GPT_URL}")
            # Use dynamic wait instead of fixed sleep
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, PROMPT_INPUT_SELECTOR))
            )

            input_box = self._retry(
                WebDriverWait(self.driver, 15).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, PROMPT_INPUT_SELECTOR))
            )
            input_box.clear()
            input_box.send_keys(prompt)
            input_box.send_keys(Keys.RETURN)
            logger.info("Prompt submitted to custom GPT.")

            self._wait_for_response_completion(timeout)
            response_text = self._scrape_response()
            logger.info("Response scraped from custom GPT.")
            return response_text

        except Exception as e:
            logger.error(f" Error sending prompt: {e}")
            return None

    def _wait_for_response_completion(self, timeout: int):
        """
        Wait until response generation is complete by checking for the disappearance of the stop button.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                stop_buttons = self.driver.find_elements(By.XPATH, STOP_BUTTON_XPATH)
                if not stop_buttons:
                    logger.info("Response generation complete.")
                    return
            except Exception as e:
                logger.warning(f"Error while waiting for response completion: {e}")
            time.sleep(1)
        logger.warning("Response generation timeout reached.")

    def _scrape_response(self) -> Optional[str]:
        """
        Scrape the latest response text from the custom GPT chat.
        """
        try:
            messages = self.driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTAINER_SELECTOR)
            if not messages:
                logger.warning("No response messages found.")
                return None
            latest_response = messages[-1].text.strip()
            return latest_response
        except Exception as e:
            logger.error(f"Error scraping response: {e}")
            return None

    def log_interaction(self, prompt: str, response: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Log the prompt and response for reinforcement learning purposes.
        """
        interaction = {
            "timestamp": datetime.utcnow().isoformat(),
            "prompt": prompt,
            "response": response,
            "metadata": metadata or {}
        }
        try:
            if os.path.exists(INTERACTION_LOG_PATH):
                with open(INTERACTION_LOG_PATH, "r") as f:
                    data = json.load(f)
            else:
                data = []
            data.append(interaction)
            with open(INTERACTION_LOG_PATH, "w") as f:
                json.dump(data, f, indent=2)
            logger.info("Interaction logged for reinforcement learning.")
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")

    def execute(
        self,
        template_name: str,
        memory_state: Dict[str, Any],
        additional_context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        voice_output: bool = False
    ) -> Optional[str]:
        """
        Full pipeline: render prompt, send prompt to custom GPT, scrape response, log the interaction,
        and optionally generate voice output.
        """
        prompt = self.render_prompt(template_name, memory_state, additional_context, metadata)
        ai_response = self.send_prompt(prompt)

        if ai_response:
            self.log_interaction(prompt, ai_response, metadata)
            if voice_output and self.tts_function:
                try:
                    self.tts_function(ai_response)
                    logger.info("Voice output generated successfully.")
                except Exception as e:
                    logger.error(f"Voice output failed: {e}")
            return ai_response

        return None