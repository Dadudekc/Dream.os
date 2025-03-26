import time
import logging
import threading
from typing import List, Dict, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger("PromptExecutionService")
logger.setLevel(logging.INFO)


class PromptExecutionService:
    """
    Handles sending prompts and retrieving responses.
    Supports both sequential and concurrent execution cycles.
    
    Attributes:
        driver_manager: An instance that manages the Selenium WebDriver.
        prompt_manager: An instance that provides prompt texts.
        feedback_engine: (Optional) An engine for parsing and updating feedback.
        model: The model identifier (affects wait times and processing).
        cycle_speed: Delay between prompts when executing sequentially.
        stable_wait: Maximum wait time (seconds) for a response to stabilize.
    """

    def __init__(
        self,
        driver_manager,
        prompt_manager,
        feedback_engine=None,
        model: str = "gpt-4o-mini",
        cycle_speed: int = 2,
        stable_wait: int = 10
    ):
        self.driver_manager = driver_manager
        self.prompt_manager = prompt_manager
        self.feedback_engine = feedback_engine
        self.model = model
        self.cycle_speed = cycle_speed
        self.stable_wait = stable_wait

    # ----------------------------------------
    # PROMPT MANAGEMENT
    # ----------------------------------------

    def get_prompt(self, prompt_name: str) -> str:
        """
        Retrieve a prompt text from the prompt manager.
        """
        logger.info(f"Retrieving prompt: {prompt_name}")
        return self.prompt_manager.get_prompt(prompt_name)

    # ----------------------------------------
    # MAIN EXECUTION
    # ----------------------------------------

    def execute_prompt_cycle(self, prompt_text: str) -> str:
        """
        Sends a prompt to an active chat, waits for response stabilization,
        and returns the final result.
        
        Args:
            prompt_text: The prompt text to be sent.
        
        Returns:
            The final AI response as a string.
        """
        logger.info(f"Executing prompt cycle using model '{self.model}'...")

        if not self.send_prompt(prompt_text):
            logger.error("Failed to send prompt")
            return ""

        wait_time = self._determine_wait_time()
        logger.info(f"⏳ Waiting {wait_time} seconds for response stabilization...")
        time.sleep(wait_time)

        response = self._fetch_response()

        if response and "jawbone" in self.model.lower():
            response = self._post_process_jawbone_response(response)

        if not response:
            logger.warning("No response detected after sending prompt.")
        else:
            logger.info(f"Response received. Length: {len(response)} characters.")

        if self.feedback_engine:
            memory_update = self.feedback_engine.parse_and_update_memory(response)
            if memory_update:
                logger.info(f"🧠 Memory updated: {memory_update}")

        return response

    def execute_prompts_single_chat(self, prompt_list: List[str]) -> List[Dict[str, str]]:
        """
        Executes a list of prompts sequentially on a single chat.
        
        Args:
            prompt_list: List of prompt names.
        
        Returns:
            A list of dictionaries with prompt names and corresponding responses.
        """
        logger.info(f"Starting sequential prompt execution on a single chat ({len(prompt_list)} prompts)...")
        responses = []

        for prompt_name in prompt_list:
            prompt_text = self.get_prompt(prompt_name)
            logger.info(f"Sending prompt: {prompt_name}")
            response = self.execute_prompt_cycle(prompt_text)
            responses.append({
                "prompt_name": prompt_name,
                "response": response
            })
            time.sleep(self.cycle_speed)

        logger.info("Sequential prompt cycle complete.")
        return responses

    def execute_prompts_concurrently(self, chat_link: str, prompt_list: List[str]) -> None:
        """
        Executes a list of prompts concurrently on a single chat, launching one thread per prompt.
        
        Args:
            chat_link: URL of the chat.
            prompt_list: List of prompt names.
        """
        logger.info(f"Executing {len(prompt_list)} prompts concurrently on chat: {chat_link}")
        threads = []
        driver: Optional[WebDriver] = self.driver_manager.get_driver()
        if driver:
            driver.get(chat_link)
            time.sleep(2)

        for prompt_name in prompt_list:
            thread = threading.Thread(
                target=self._execute_single_prompt_thread,
                args=(chat_link, prompt_name)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        logger.info("All prompt executions completed concurrently.")

    # ----------------------------------------
    # THREAD EXECUTION FOR SINGLE PROMPT
    # ----------------------------------------

    def _execute_single_prompt_thread(self, chat_link: str, prompt_name: str) -> None:
        """
        Executes a single prompt in its own thread.
        
        Args:
            chat_link: URL of the chat.
            prompt_name: Name of the prompt.
        """
        logger.info(f"[Thread] Executing prompt '{prompt_name}' on chat {chat_link}")
        prompt_text = self.get_prompt(prompt_name)
        response = self.execute_prompt_cycle(prompt_text)
        if not response:
            logger.warning(f"[Thread] No response for prompt '{prompt_name}' on chat {chat_link}")
            return
        if self.feedback_engine:
            memory_update = self.feedback_engine.parse_and_update_memory(response)
            if memory_update:
                logger.info(f"🧠 [Thread] Memory updated: {memory_update}")
        logger.info(f"[Thread] Completed prompt '{prompt_name}' on chat {chat_link}")

    # ----------------------------------------
    # MODEL BEHAVIOR HANDLING
    # ----------------------------------------

    def _determine_wait_time(self) -> int:
        """
        Adjust wait time dynamically based on model.
        
        Returns:
            An integer wait time in seconds.
        """
        if "mini" in self.model.lower():
            return 5
        elif "jawbone" in self.model.lower():
            return 15
        else:
            return self.stable_wait

    def _post_process_jawbone_response(self, response: str) -> str:
        """
        Post-process Jawbone model responses.
        
        Args:
            response: The raw response text.
        
        Returns:
            The cleaned response text.
        """
        logger.info("Post-processing Jawbone response...")
        return response.replace("[Start]", "").replace("[End]", "").strip()

    # ----------------------------------------
    # INTERNAL HELPERS
    # ----------------------------------------

    def send_prompt(self, prompt_text: str) -> bool:
        """
        Sends a prompt to the active chat input field.
        
        Args:
            prompt_text: The text to send.
        
        Returns:
            True if prompt is sent successfully; False otherwise.
        """
        logger.info("Locating input field to send prompt...")
        driver: Optional[WebDriver] = self.driver_manager.get_driver()
        if not driver:
            logger.error("Driver not initialized")
            return False

        try:
            input_box = driver.find_element(By.XPATH, "//textarea[@data-id='root-textarea']")
            input_box.clear()
            input_box.send_keys(prompt_text)
            time.sleep(1)
            send_button = driver.find_element(By.XPATH, "//button[@data-testid='send-button']")
            send_button.click()
            logger.info("Prompt sent successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send prompt: {e}")
            return False

    def _fetch_response(self) -> str:
        """
        Retrieves the latest AI response from the chat.
        
        Returns:
            The latest response text, or an empty string if unavailable.
        """
        logger.info("Fetching latest response...")
        driver: Optional[WebDriver] = self.driver_manager.get_driver()
        if not driver:
            logger.error("Driver not initialized")
            return ""

        try:
            time.sleep(2)
            response_blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]')
            if not response_blocks:
                logger.warning("No response blocks found.")
                return ""
            latest_response = response_blocks[-1]
            response_text = latest_response.text.strip()
            is_complete = not driver.find_elements(By.CSS_SELECTOR, '.result-streaming')
            if not is_complete:
                logger.info("Response is still streaming, waiting...")
                time.sleep(3)
                response_blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]')
                if response_blocks:
                    response_text = response_blocks[-1].text.strip()
            logger.info(f"Response fetched. Length: {len(response_text)} characters")
            return response_text
        except Exception as e:
            logger.error(f"Error fetching response: {e}")
            return ""

    def wait_for_stable_response(self, max_wait: Optional[int] = None) -> str:
        """
        Waits for the AI response to stabilize (i.e., stop changing).
        
        Args:
            max_wait: Maximum wait time in seconds (defaults to self.stable_wait).
        
        Returns:
            The final stable response text.
        """
        max_wait = max_wait or self.stable_wait
        logger.info(f"Waiting for stable response (max {max_wait}s)...")
        driver: Optional[WebDriver] = self.driver_manager.get_driver()
        if not driver:
            logger.error("Driver not initialized")
            return ""

        try:
            last_response = ""
            stable_time = 0
            start_time = time.time()

            while time.time() - start_time < max_wait:
                current_response = self._fetch_response()
                if current_response == last_response and current_response:
                    stable_time += 1
                    if stable_time >= 3:
                        logger.info("Response has stabilized.")
                        return current_response
                else:
                    stable_time = 0
                    last_response = current_response
                time.sleep(1)
            logger.warning("Max wait time exceeded, returning current response.")
            return last_response
        except Exception as e:
            logger.error(f"Error waiting for stable response: {e}")
            return ""
