import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Setup logger
logger = logging.getLogger("OpenAIPromptEngine")
logger.setLevel(logging.INFO)

# Constants for your custom GPT endpoint and selectors (adjust as needed)
CUSTOM_GPT_URL = "https://chatgpt.com/g/g-67dbbf224a6c819193a2f0938a64f7e6-openaipromptengine"
PROMPT_INPUT_SELECTOR = "textarea"  # Adjust if needed
RESPONSE_CONTAINER_SELECTOR = "div.markdown.prose.w-full.break-words"  # Adjust based on DOM
STOP_BUTTON_XPATH = "//button[contains(., 'Stop generating')]"  # Optional

class OpenAIPromptEngine:
    """
    OpenAIPromptEngine:
      - Renders prompts using Jinja2 templates.
      - Uses Selenium to scrape your custom GPT (hosted at CUSTOM_GPT_URL) to generate responses.
      - Optionally triggers voice automation.
    """

    def __init__(
        self,
        driver,
        template_dir: str = "chat_mate/templates/prompt_templates",
        tts_function: Optional[Any] = None  # Pass a TTS function if available
    ):
        self.driver = driver
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
        self.tts_function = tts_function  # Function that takes text and generates/plays audio
        logger.info("🚀 OpenAIPromptEngine initialized using custom GPT scraper.")

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
            logger.error(f"❌ Failed to load template '{template_name}': {e}")
            raise e

        context = {
            "CURRENT_MEMORY_STATE": json.dumps(memory_state, indent=2),
            "ADDITIONAL_CONTEXT": additional_context or "",
            "METADATA": metadata or {}
        }
        prompt = template.render(context)
        logger.info(f"📝 Prompt rendered from template '{template_name}'.")
        return prompt

    def send_prompt(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """
        Uses Selenium to open the custom GPT URL, send the rendered prompt, wait for generation to complete,
        and then scrape the response.
        """
        try:
            self.driver.get(CUSTOM_GPT_URL)
            logger.info(f"Navigated to custom GPT at {CUSTOM_GPT_URL}")
            time.sleep(5)  # Wait for page to load

            # Locate the prompt input box
            input_box = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, PROMPT_INPUT_SELECTOR))
            )
            input_box.clear()
            input_box.send_keys(prompt)
            input_box.send_keys(Keys.RETURN)
            logger.info("Prompt submitted to custom GPT.")

            # Optional: wait for "Stop generating" button to disappear, indicating response is ready.
            self._wait_for_response_completion(timeout)

            response_text = self._scrape_response()
            logger.info("Response scraped from custom GPT.")
            return response_text

        except Exception as e:
            logger.error(f"❌ Error sending prompt: {e}")
            return None

    def _wait_for_response_completion(self, timeout: int):
        """
        Wait until the response generation is complete.
        This example waits until the "Stop generating" button is no longer visible.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                stop_buttons = self.driver.find_elements(By.XPATH, STOP_BUTTON_XPATH)
                if not stop_buttons:
                    logger.info("Response generation complete.")
                    return
            except Exception:
                pass
            time.sleep(1)
        logger.warning("Response generation timeout reached.")

    def _scrape_response(self) -> str:
        """
        Scrape the latest response text from the custom GPT chat.
        """
        try:
            # Grab all message containers; assume the last one is the latest response.
            messages = self.driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTAINER_SELECTOR)
            if not messages:
                logger.warning("No response messages found.")
                return ""
            latest_response = messages[-1].text.strip()
            return latest_response
        except Exception as e:
            logger.error(f"Error scraping response: {e}")
            return ""

    def execute(
        self,
        template_name: str,
        memory_state: Dict[str, Any],
        additional_context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        voice_output: bool = False
    ) -> Optional[str]:
        """
        Full pipeline: render prompt, send prompt to custom GPT, scrape response, optionally generate voice.
        """
        prompt = self.render_prompt(template_name, memory_state, additional_context, metadata)
        ai_response = self.send_prompt(prompt)

        if ai_response:
            logger.info("AI response received, logging interaction...")
            # Here, you can integrate reinforcement logging if needed.
            if voice_output and self.tts_function:
                try:
                    self.tts_function(ai_response)
                    logger.info("Voice output generated successfully.")
                except Exception as e:
                    logger.error(f"Voice output failed: {e}")
            return ai_response

        return None

# ----------------------------------------
# Example Usage
# ----------------------------------------
if __name__ == "__main__":
    from utils.DriverManager import DriverManager

    # Initialize driver manager (set headless as desired)
    with DriverManager(headless=False) as driver_manager:
        driver = driver_manager.get_driver()

        # Initialize OpenAIPromptEngine with the driver
        prompt_engine = OpenAIPromptEngine(driver=driver, template_dir="chat_mate/templates/prompt_templates")

        # Example memory state (could be loaded from your persistent memory)
        memory_state = {
            "version": 1,
            "data": {
                "projects": ["ChatMate", "FreeRide Investor"],
                "skills": ["System Convergence", "Execution Velocity"]
            }
        }

        # Execute the prompt (template file must exist in template_dir)
        ai_response = prompt_engine.execute(
            template_name="devlog_prompt.j2",
            memory_state=memory_state,
            additional_context="Victor optimized his workflow automation.",
            metadata={"platform": "Discord", "action": "devlog_generation"},
            voice_output=False  # Change to True if you implement TTS
        )

        print("\nAI Response:\n", ai_response)
