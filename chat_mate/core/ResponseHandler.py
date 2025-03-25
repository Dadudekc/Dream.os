import os
import time
import pickle
import logging
import sys
import shutil
import re
import json
from datetime import datetime
from typing import Optional, Tuple, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys  # <-- Added missing import
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager

from jinja2 import Template  # Jinja2 integrated for templated output
from core.logging.services.ai_output_service import log_ai_output  # Use the core logging service

# ---------------------------
# Logging Setup
# ---------------------------
def setup_logging(name: str = "dreamscape_response_handler", log_dir: Optional[str] = None) -> logging.Logger:
    log_dir = log_dir or os.path.join(os.getcwd(), "logs", "response_handler")
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, f"{name}.log")),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(name)

logger = setup_logging()

# ---------------------------
# Configuration & Constants
# ---------------------------
CHATGPT_URL = "https://chat.openai.com/"
PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile", "openai")
COOKIE_FILE = os.path.join(os.getcwd(), "cookies", "openai.pkl")
CONTENT_LOG_DIR = os.path.join(os.getcwd(), "chat_mate", "content_logs")

os.makedirs(CONTENT_LOG_DIR, exist_ok=True)

# ---------------------------
# Hybrid Response Handler Class
# ---------------------------
class HybridResponseHandler:
    """
    Parses a hybrid response that includes both narrative text and a MEMORY_UPDATE JSON block.
    Returns a tuple of (text_part, memory_update_json).
    """

    def parse_hybrid_response(self, raw_response: str) -> Tuple[str, dict]:
        logger.info("Parsing hybrid response for narrative text and MEMORY_UPDATE JSON.")
        # Regex to capture JSON block between ```json and ```
        json_pattern = r'```json(.*?)```'
        match = re.search(json_pattern, raw_response, re.DOTALL)

        if match:
            json_content = match.group(1).strip()
            try:
                memory_update = json.loads(json_content)
                logger.info("Successfully parsed MEMORY_UPDATE JSON.")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                memory_update = {}
        else:
            logger.warning("No JSON block found in the response.")
            memory_update = {}

        # Remove the JSON block from the raw response to extract pure narrative text.
        text_part = re.sub(json_pattern, '', raw_response, flags=re.DOTALL).strip()

        return text_part, memory_update

# ---------------------------
# Core Response Handler Class
# ---------------------------
class ResponseHandler:
    """
    Handles sending prompts, fetching, and stabilizing ChatGPT responses.
    Now includes hybrid response processing: it will extract narrative text and MEMORY_UPDATE JSON.
    Also hooks into the AI output logger for reinforcement training.
    """

    def __init__(self, driver: Optional[uc.Chrome] = None, timeout: int = 180, stable_period: int = 10, poll_interval: int = 5) -> None:
        self.driver = driver or self._init_driver()
        self.timeout = timeout
        self.stable_period = stable_period
        self.poll_interval = poll_interval

    # ---------------------------
    # Driver Initialization
    # ---------------------------
    def _init_driver(self) -> uc.Chrome:
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        if PROFILE_DIR:
            options.add_argument(f"--user-data-dir={PROFILE_DIR}")

        cached_driver_path = os.path.join(os.getcwd(), "drivers", "chromedriver.exe")
        
        if os.path.exists(cached_driver_path):
            driver_path = cached_driver_path
            logger.info(f"Using cached ChromeDriver: {driver_path}")
        else:
            logger.warning("No cached ChromeDriver found. Downloading latest...")
            driver_path = ChromeDriverManager().install()
            os.makedirs(os.path.dirname(cached_driver_path), exist_ok=True)
            shutil.copyfile(driver_path, cached_driver_path)
            driver_path = cached_driver_path
            logger.info(f"Cached ChromeDriver at: {driver_path}")

        driver = uc.Chrome(options=options, driver_executable_path=driver_path)
        logger.info("Undetected Chrome driver initialized.")
        return driver

    # ---------------------------
    # Authentication Helpers
    # ---------------------------
    def save_cookies(self) -> None:
        try:
            os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
            cookies = self.driver.get_cookies()
            with open(COOKIE_FILE, "wb") as f:
                pickle.dump(cookies, f)
            logger.info(f"Cookies saved: {COOKIE_FILE}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    def load_cookies(self) -> bool:
        if not os.path.exists(COOKIE_FILE):
            logger.warning("No cookie file found.")
            return False
        try:
            with open(COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                cookie.pop("sameSite", None)
                self.driver.add_cookie(cookie)
            self.driver.refresh()
            time.sleep(5)
            logger.info("Cookies loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False

    def is_logged_in(self) -> bool:
        try:
            self.driver.get(CHATGPT_URL)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'nav[aria-label="Chat history"]'))
            )
            logger.info("Detected active login session.")
            return True
        except Exception:
            logger.warning("User not logged in.")
            return False

    # ---------------------------
    # Prompt Submission
    # ---------------------------
    def send_prompt(self, prompt: str) -> bool:
        try:
            wait = WebDriverWait(self.driver, 15)
            input_box = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']"))
            )
            input_box.click()
            logger.info(f"Typing prompt (length {len(prompt)} chars)...")
            for char in prompt:
                input_box.send_keys(char)
                time.sleep(0.02)  # Simulate human typing speed
            input_box.send_keys(Keys.RETURN)
            logger.info(f"Prompt sent: {prompt[:60]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send prompt: {e}")
            return False

    # ---------------------------
    # Response Fetching and Stabilization
    # ---------------------------
    def fetch_response(self) -> str:
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
        logger.info("Waiting for stable ChatGPT response...")
        start_time = time.time()
        last_response = ""
        stable_start = None

        while time.time() - start_time < self.timeout:
            time.sleep(self.poll_interval)
            current_response = self.fetch_response()

            if current_response != last_response:
                logger.info("New response detected; monitoring for stability...")
                last_response = current_response
                stable_start = time.time()
            elif stable_start and (time.time() - stable_start) >= self.stable_period:
                logger.info("Response stabilized.")
                stable_response = self.clean_response(last_response)
                log_file_path = os.path.join(os.getcwd(), "outputs", "reinforcement_logs")
                log_ai_output(
                    context="ResponseHandler",
                    input_prompt="Sent prompt",
                    ai_output=stable_response,
                    base_log_dir=log_file_path,
                    tags=["stable_response"],
                    result="success"
                )
                return stable_response

        logger.warning("Response stabilization timeout reached; returning partial response.")
        stable_response = self.clean_response(last_response)
        log_file_path = os.path.join(os.getcwd(), "outputs", "reinforcement_logs")
        log_ai_output(
            context="ResponseHandler",
            input_prompt="Sent prompt",
            ai_output=stable_response,
            base_log_dir=log_file_path,
            tags=["stable_response", "timeout"],
            result="partial"
        )
        return stable_response

    @staticmethod
    def clean_response(response: str) -> str:
        return response.strip()

    # ---------------------------
    # Hybrid Response Processing with Jinja Template
    # ---------------------------
    def handle_hybrid_response(self, raw_response: str, prompt_manager: Any, chat_title: str = "Unknown Chat") -> None:
        """
        Parses the raw response to extract narrative text and a MEMORY_UPDATE JSON block.
        Uses Jinja2 to render a formatted archival report.
        - Archives the formatted report to a content log.
        - Passes the MEMORY_UPDATE JSON to the prompt manager for persistent memory updates.
        """
        logger.info("Handling hybrid response...")
        hybrid_handler = HybridResponseHandler()
        narrative_text, memory_update_json = hybrid_handler.parse_hybrid_response(raw_response)

        # Define a Jinja2 template for the archival report.
        archive_template_str = (
            "--- Hybrid Response Archive ---\n"
            "Timestamp: {{ timestamp }}\n"
            "Chat Title: {{ chat_title }}\n\n"
            "=== Narrative Text ===\n"
            "{{ narrative_text }}\n\n"
            "=== MEMORY_UPDATE JSON ===\n"
            "{{ memory_update_json | tojson(indent=2) }}\n"
            "-------------------------------\n"
        )
        template = Template(archive_template_str)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rendered_report = template.render(
            timestamp=timestamp,
            chat_title=chat_title,
            narrative_text=narrative_text,
            memory_update_json=memory_update_json
        )

        # Archive the rendered report to a content log file.
        archive_file = os.path.join(CONTENT_LOG_DIR, f"hybrid_response_{timestamp}.txt")
        with open(archive_file, 'w', encoding='utf-8') as f:
            f.write(rendered_report)
        logger.info(f"Archived hybrid response to: {archive_file}")

        # Update persistent memory using the MEMORY_UPDATE JSON.
        if memory_update_json:
            try:
                prompt_manager.parse_memory_updates(memory_update_json)
                logger.info("Persistent memory updated via hybrid response.")
            except Exception as e:
                logger.error(f"Failed to update persistent memory: {e}")
        else:
            logger.warning("No MEMORY_UPDATE JSON found in the response.")

    # ---------------------------
    # Single Prompt Cycle with Rate Limiting
    # ---------------------------
    def execute_prompt_cycle(self, prompt: str, rate_limit: int = 2) -> str:
        if not self.is_logged_in():
            logger.warning("Manual login required.")
            self.driver.get("https://chat.openai.com/auth/login")
            input(">> Press ENTER after completing login manually... <<")
            self.save_cookies()

        self.driver.get(CHATGPT_URL)
        time.sleep(5)

        if not self.send_prompt(prompt):
            logger.error("Prompt submission failed. Cycle aborted.")
            return ""
        
        response = self.wait_for_stable_response()
        
        time.sleep(rate_limit)
        
        return response

    # ---------------------------
    # Run Prompts on Multiple Chats with Rate Limiting
    # ---------------------------
    def execute_prompts_on_all_chats(self, prompts: list, chat_list: list, rate_limit: int = 2) -> dict:
        if not self.is_logged_in():
            logger.warning("Manual login required.")
            self.driver.get("https://chat.openai.com/auth/login")
            input(">> Press ENTER after completing login manually... <<")
            self.save_cookies()

        results = {}
        for chat_info in chat_list:
            chat_title = chat_info["title"]
            chat_url = chat_info["link"]

            logger.info(f"--- Accessing chat '{chat_title}' ---")
            self.driver.get(chat_url)
            time.sleep(3)

            chat_responses = []
            for idx, prompt_text in enumerate(prompts, start=1):
                logger.info(f"Sending prompt #{idx} to chat '{chat_title}'")
                if not self.send_prompt(prompt_text):
                    logger.error(f"Failed to send prompt #{idx} to chat '{chat_title}'.")
                    chat_responses.append("")
                    continue
                stable_resp = self.wait_for_stable_response()
                chat_responses.append(stable_resp)
                time.sleep(rate_limit)
            results[chat_title] = chat_responses

        return results

    # ---------------------------
    # Graceful Shutdown
    # ---------------------------
    def shutdown(self) -> None:
        logger.info("Shutting down browser driver.")
        self.driver.quit()


# ---------------------------
# Example CLI Usage
# ---------------------------
if __name__ == "__main__":
    handler = ResponseHandler(timeout=180, stable_period=10)

    # Example single prompt usage
    single_prompt = (
        "You are my devlog assistant. Summarize the recent development work with a focus on challenges overcome and what's next."
    )
    single_response = handler.execute_prompt_cycle(single_prompt, rate_limit=2)
    if single_response:
        logger.info(f"\n--- Single Prompt Response ---\n{single_response}\n")
        # If the response is hybrid, pass it to your prompt manager (assuming it's defined)
        # e.g., handler.handle_hybrid_response(single_response, prompt_manager_instance, chat_title="Devlog Chat")
    else:
        logger.warning("No stable response received for single prompt.")

    # Example multi-chat usage: define example chats
    chat_list = [
        {"title": "Chat #1", "link": "https://chatgpt.com/c/67d7521e-acf0-8009-aed6-2748b3b49249"},
        {"title": "Chat #2", "link": "https://chatgpt.com/c/67d774ad-8bfc-8009-a488-6b5392f1326f"}
    ]

    prompts_to_send = [
        "What are the main project goals?",
        "How can we improve the architecture further?"
    ]

    all_chat_results = handler.execute_prompts_on_all_chats(prompts=prompts_to_send, chat_list=chat_list, rate_limit=2)
    for chat_name, responses in all_chat_results.items():
        logger.info(f"\n--- Chat '{chat_name}' Responses ---")
        for i, resp in enumerate(responses, start=1):
            logger.info(f"Prompt #{i} response:\n{resp}\n")

    handler.shutdown()
