import time
import json
import logging
from datetime import datetime
from typing import Optional, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger("prompt_engine")


class PromptEngine:
    """
    Encapsulates prompt execution logic:
      - Sends a prompt via DOM injection (or simulated typing).
      - Waits for a stable AI response.
      - Logs response metrics.
    """

    def __init__(self,
                 driver: Any,
                 timeout: int = 180,
                 stable_period: int = 10,
                 poll_interval: int = 5,
                 reinforcement_engine: Optional[Any] = None,
                 simulate_typing: bool = False,
                 typing_delay: float = 0.02):
        """
        :param driver: Selenium driver instance.
        :param timeout: Maximum time (in seconds) to wait for a response.
        :param stable_period: Time period (in seconds) during which the response remains unchanged.
        :param poll_interval: How frequently (in seconds) to poll for updated response.
        :param reinforcement_engine: Optional engine for processing feedback.
        :param simulate_typing: If True, simulates typing character-by-character.
        :param typing_delay: Delay (in seconds) between keystrokes when simulating typing.
        """
        self.driver = driver
        self.timeout = timeout
        self.stable_period = stable_period
        self.poll_interval = poll_interval
        self.reinforcement_engine = reinforcement_engine
        self.simulate_typing = simulate_typing
        self.typing_delay = typing_delay

    def send_prompt(self, prompt: str) -> bool:
        """
        Sends the provided prompt to the ChatGPT input box.
        Uses DOM injection by default or simulates typing if specified.
        Returns True if successful.
        """
        try:
            wait = WebDriverWait(self.driver, 15)
            input_box = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']"))
            )
            input_box.click()
            if self.simulate_typing:
                logger.info(f"Simulating typing for prompt (length {len(prompt)} chars)...")
                for char in prompt:
                    input_box.send_keys(char)
                    time.sleep(self.typing_delay)
            else:
                # DOM injection method for speed.
                self.driver.execute_script("arguments[0].innerText = arguments[1];", input_box, prompt)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_box)
            input_box.send_keys(Keys.RETURN)
            logger.info("Prompt sent successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send prompt: {e}")
            return False

    def fetch_response(self) -> str:
        """
        Fetches the latest ChatGPT response text.
        Returns the text of the last message if available.
        """
        try:
            messages = self.driver.find_elements(By.CSS_SELECTOR, ".markdown.prose.w-full.break-words")
            if messages:
                response = messages[-1].text.strip()
                logger.debug(f"Fetched response (length {len(response)} chars)")
                return response
            return ""
        except Exception as e:
            logger.error(f"Error fetching response: {e}")
            return ""

    def wait_for_stable_response(self) -> str:
        """
        Waits until the ChatGPT response remains unchanged for 'stable_period' seconds or timeout.
        Logs AI response metrics and returns the final response.
        """
        logger.info("⏳ Waiting for stable AI response...")
        start_time = time.time()
        last_response = ""
        stable_start = None

        while (time.time() - start_time) < self.timeout:
            time.sleep(self.poll_interval)
            current_response = self.fetch_response()
            if current_response != last_response:
                logger.info("AI response updated; resetting stability timer.")
                last_response = current_response
                stable_start = time.time()
            elif stable_start and (time.time() - stable_start) >= self.stable_period:
                response_time = round(time.time() - start_time, 2)
                logger.info(f"✅ Stable AI response achieved in {response_time}s.")
                self.log_ai_response(last_response, response_time=response_time)
                return self.clean_response(last_response)

        logger.warning("⚠️ AI response stabilization timeout. Returning last available response.")
        self.log_ai_response(last_response, timeout_reached=True)
        return self.clean_response(last_response)

    def log_ai_response(self, response: str, response_time: Optional[float] = None, timeout_reached: bool = False) -> None:
        """
        Logs response metrics and optionally processes feedback via reinforcement engine.
        """
        ai_observations = {
            "response_length": len(response),
            "tokens_used": len(response.split()),
            "timeout_occurred": timeout_reached,
            "hallucination_detected": "AI hallucination" in response,
            "execution_timestamp": datetime.now().isoformat(),
        }
        if response_time:
            ai_observations["response_time"] = response_time

        logger.info(f"📊 AI Response Metrics:\n{json.dumps(ai_observations, indent=2)}")

        if self.reinforcement_engine:
            try:
                feedback_score = self.reinforcement_engine.analyze_response("N/A", response)
                logger.info(f"🎯 Reinforcement score: {feedback_score}")
            except Exception as e:
                logger.error(f"Error in reinforcement engine processing: {e}")

    @staticmethod
    def clean_response(response: str) -> str:
        """
        Clean and normalize the response text.
        """
        return response.strip()
