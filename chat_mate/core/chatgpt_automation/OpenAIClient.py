import os
import time
import json
import pickle
import logging
import shutil
import platform
from pathlib import Path
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ensure correct import of setup_logging; if this fails in module mode, adjust sys.path accordingly.
from core.chatgpt_automation.setup_logging import setup_logging

# Initialize logger with a fallback log directory.
LOG_DIR = os.path.join(os.getcwd(), "logs", "social")
os.makedirs(LOG_DIR, exist_ok=True)
logger = setup_logging("openai_login", log_dir=LOG_DIR)

class OpenAIClient:
    def __init__(self, profile_dir, headless=False, driver_path=None):
        """
        Initialize the OpenAIClient.

        Args:
            profile_dir (str): Path to the Chrome user data directory.
            headless (bool): Whether to run Chrome in headless mode.
            driver_path (str): Optional custom path to a ChromeDriver binary.
        """
        self.profile_dir = str(Path(profile_dir))
        self.headless = headless
        self.driver_path = driver_path

        # Configuration
        self.CHATGPT_URL = "https://chat.openai.com/"
        self.COOKIE_DIR = str(Path(os.getcwd()) / "cookies")
        self.COOKIE_FILE = str(Path(self.COOKIE_DIR) / "openai.pkl")

        # Go up 3 directories from the current file (assuming you're inside core/chatgpt_automation/controllers)
        self.CONFIG_FILE = str(Path(__file__).resolve().parents[3] / "config" / "command_config.json")

        # Load configuration
        self.config = self._load_config()

        # Initialize driver
        self.driver = self.get_openai_driver()

    def _load_config(self):
        """Load configuration from command_config.json"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            logger.warning(f"⚠️ No config file found at {self.CONFIG_FILE}. Using defaults.")
            return {
                "default_model": "gpt-4",
                "auto_commit": True,
                "auto_test": True,
                "debug_mode": False,
                "chrome_driver": {
                    "auto_detect": True,
                    "fallback_paths": []
                }
            }
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            return {}

    def get_openai_driver(self):
        """
        Returns a stealth Chrome driver using undetected_chromedriver.
        Cross-platform compatible implementation.
        """
        logger.info("🔧 Initializing undetected_chromedriver for OpenAIClient...")

        try:
            options = uc.ChromeOptions()
            options.add_argument("--start-maximized")
            if self.profile_dir:
                options.add_argument(f"--user-data-dir={self.profile_dir}")
            if self.headless:
                options.add_argument("--headless=new")

            # Custom driver path handling
            if self.driver_path and os.path.exists(self.driver_path):
                logger.info(f"🔎 Using custom ChromeDriver: {self.driver_path}")
                driver = uc.Chrome(
                    options=options,
                    driver_executable_path=self.driver_path
                )
            else:
                # Let undetected_chromedriver handle driver management
                logger.info("🔄 Using undetected_chromedriver's internal driver manager.")
                driver = uc.Chrome(options=options)

            logger.info("✅ Undetected Chrome driver initialized for OpenAI.")
            return driver

        except Exception as e:
            error_msg = f"❌ Failed to initialize Chrome driver: {e}"
            logger.error(error_msg)
            
            # Attempt fallback paths from config
            if self.config.get("chrome_driver", {}).get("fallback_paths"):
                for path in self.config["chrome_driver"]["fallback_paths"]:
                    try:
                        fallback_path = str(Path(path))
                        if platform.system() == "Windows":
                            fallback_path += ".exe"
                        
                        if os.path.exists(fallback_path):
                            logger.info(f"🔄 Attempting fallback ChromeDriver: {fallback_path}")
                            return uc.Chrome(
                                options=options,
                                driver_executable_path=fallback_path
                            )
                    except Exception as fallback_e:
                        logger.warning(f"⚠️ Fallback path failed: {fallback_e}")
                        continue
            
            raise Exception(f"Failed to initialize Chrome driver: {e}")

    def save_openai_cookies(self):
        """
        Save OpenAI cookies to a pickle file.
        """
        os.makedirs(self.COOKIE_DIR, exist_ok=True)
        try:
            cookies = self.driver.get_cookies()
            with open(self.COOKIE_FILE, "wb") as f:
                pickle.dump(cookies, f)
            logger.info(f"✅ Saved OpenAI cookies to {self.COOKIE_FILE}")
        except Exception as e:
            logger.error(f"❌ Failed to save cookies: {e}")

    def load_openai_cookies(self):
        """
        Load OpenAI cookies from file and refresh session.
        """
        if not os.path.exists(self.COOKIE_FILE):
            logger.warning("⚠️ No OpenAI cookie file found. Manual login may be required.")
            return False

        self.driver.get(self.CHATGPT_URL)
        time.sleep(2)

        try:
            with open(self.COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                cookie.pop("sameSite", None)
                self.driver.add_cookie(cookie)
            self.driver.refresh()
            time.sleep(5)
            logger.info("✅ OpenAI cookies loaded and session refreshed.")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load cookies: {e}")
            return False

    def is_logged_in(self):
        """
        Checks if the user is logged in to ChatGPT by navigating to a tactic generator URL.
        """
        TARGET_URL = "https://chatgpt.com/g/g-67a4c53f01648191bdf31ab8591e84e7-tbow-tactic-generator"
        self.driver.get(TARGET_URL)
        time.sleep(3)
        current_url = self.driver.current_url

        if current_url.startswith("https://chatgpt.com/g/"):
            logger.info("✅ Tactic generator page reached; user is logged in.")
            self.driver.get(self.CHATGPT_URL)
            time.sleep(3)
            return True
        else:
            logger.warning("⚠️ Unable to reach tactic generator page; login may be required.")
            return False

    def login_openai(self):
        """
        Login handler for OpenAI/ChatGPT.
        Checks if session is active; if not, tries to load cookies or falls back to manual login.
        """
        logger.info("🔐 Starting OpenAI login process...")

        if self.is_logged_in():
            logger.info("✅ Already logged in; starting work immediately.")
            return True

        if self.load_openai_cookies() and self.is_logged_in():
            logger.info("✅ OpenAI auto-login successful with cookies.")
            return True

        logger.warning("⚠️ Manual login required. Navigating to login page...")
        self.driver.get("https://chat.openai.com/auth/login")
        time.sleep(5)

        input("👉 Please manually complete the login + verification and press ENTER here...")

        if self.is_logged_in():
            self.save_openai_cookies()
            logger.info("✅ Manual OpenAI login successful. Cookies saved.")
            return True
        else:
            logger.error("❌ Manual OpenAI login failed. Try again.")
            return False

    def send_prompt_smoothly(self, element, prompt, delay=0.05):
        """
        Sends the prompt text one character at a time for a more human-like interaction.
        """
        for char in prompt:
            element.send_keys(char)
            time.sleep(delay)

    def get_chatgpt_response(self, prompt, timeout=120, model_url=None):
        """
        Sends a prompt to ChatGPT and retrieves the full response by interacting with the ProseMirror element.
        """
        logger.info("✉️ Sending prompt to ChatGPT...")

        try:
            target_url = model_url if model_url else self.CHATGPT_URL
            self.driver.get(target_url)

            wait = WebDriverWait(self.driver, 15)

            # Wait for the ProseMirror contenteditable div to be present and clickable.
            input_div = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']")
            ))
            logger.info("✅ Found ProseMirror input.")

            input_div.click()

            # Type the prompt slowly for human-like behavior.
            self.send_prompt_smoothly(input_div, prompt, delay=0.03)

            # Submit the prompt
            input_div.send_keys(Keys.RETURN)
            logger.info("✅ Prompt submitted, waiting for response...")

            return self.get_full_response(timeout=timeout)

        except Exception as e:
            logger.error(f"❌ Error in get_chatgpt_response: {e}")
            return ""

    def get_full_response(self, timeout=120):
        """
        Waits for the full response from ChatGPT, clicking "Continue generating" if necessary.
        """
        logger.info("🔄 Waiting for full response...")
        start_time = time.time()
        full_response = ""

        while True:
            if time.time() - start_time > timeout:
                logger.warning("⚠️ Timeout reached while waiting for ChatGPT response.")
                break

            time.sleep(3)
            try:
                messages = self.driver.find_elements(By.CSS_SELECTOR, ".markdown.prose.w-full.break-words")
                if messages:
                    latest_message = messages[-1].text
                    if latest_message != full_response:
                        full_response = latest_message
                    else:
                        logger.info("✅ Response appears complete.")
                        break

                continue_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Continue generating')]")
                if continue_buttons:
                    logger.info("🔘 Clicking 'Continue generating'...")
                    continue_buttons[0].click()
            except Exception as e:
                logger.error(f"❌ Error during response fetch: {e}")
                continue

        return full_response

    def process_prompt(self, prompt, timeout=120, model_url=None):
        """
        A convenience method for asynchronous workers.
        Ensures the session is valid and returns the ChatGPT response for a given prompt.
        """
        if not self.is_logged_in():
            logger.info("Session expired. Attempting to log in again...")
            if not self.login_openai():
                logger.error("❌ Unable to re-login; cannot process prompt.")
                return ""
        response = self.get_chatgpt_response(prompt, timeout=timeout, model_url=model_url)
        return response

    def get_full_response_for_debug(self, timeout=120):
        """
        For debugging purposes: returns the full response without sending a prompt.
        """
        return self.get_full_response(timeout=timeout)

    def shutdown(self):
        """
        Shut down the driver gracefully and clean up resources.
        """
        logger.info("🛑 Shutting down OpenAIClient driver...")
        try:
            if hasattr(self, 'driver') and self.driver:
                # Save cookies before shutting down
                try:
                    self.save_openai_cookies()
                except Exception as cookie_e:
                    logger.warning(f"⚠️ Could not save cookies during shutdown: {cookie_e}")
                
                # Close all windows
                try:
                    self.driver.close()
                except Exception as close_e:
                    logger.warning(f"⚠️ Error closing browser window: {close_e}")
                    
                # Quit the driver
                try:
                    self.driver.quit()
                except Exception as quit_e:
                    logger.warning(f"⚠️ Error quitting driver: {quit_e}")
                    # Force kill any remaining ChromeDriver processes if driver.quit() fails
                    self._force_kill_chromedriver()
                
                self.driver = None
                logger.info("✅ Driver shut down successfully.")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
            # Even if an exception occurs, try to kill chromedriver processes
            self._force_kill_chromedriver()
        finally:
            # Clean up any temporary files or resources
            try:
                if hasattr(self, 'profile_dir') and os.path.exists(self.profile_dir):
                    for root, dirs, files in os.walk(self.profile_dir):
                        for name in files:
                            if name.endswith('.lock'):
                                try:
                                    os.remove(os.path.join(root, name))
                                except Exception:
                                    pass
            except Exception as cleanup_e:
                logger.warning(f"⚠️ Error during cleanup: {cleanup_e}")
            
            logger.info("✅ OpenAIClient shutdown complete.")
    
    def _force_kill_chromedriver(self):
        """
        Force kill any remaining ChromeDriver processes.
        Last resort for when driver.quit() fails to fully terminate the process.
        """
        try:
            import subprocess
            import platform
            
            logger.info("🔄 Attempting to force kill ChromeDriver processes...")
            
            # Platform-specific commands to list and kill processes
            if platform.system() == "Windows":
                # Find chromedriver processes
                subprocess.run("taskkill /f /im chromedriver.exe", shell=True, capture_output=True)
                subprocess.run("taskkill /f /im chrome.exe", shell=True, capture_output=True)
            elif platform.system() == "Linux":
                subprocess.run("pkill -f chromedriver", shell=True, capture_output=True)
                subprocess.run("pkill -f chrome", shell=True, capture_output=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run("pkill -f chromedriver", shell=True, capture_output=True)
                subprocess.run("pkill -f Chrome", shell=True, capture_output=True)
            
            logger.info("✅ Forced termination of ChromeDriver processes completed.")
        except Exception as e:
            logger.error(f"❌ Error during force kill: {e}")


# --------------------
# Test Run (Optional)
# --------------------
if __name__ == "__main__":
    PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile", "openai")
    client = OpenAIClient(profile_dir=PROFILE_DIR, headless=False, driver_path=None)

    if client.login_openai():
        logger.info("🎉 OpenAI Login Complete!")
    else:
        logger.error("❌ OpenAI Login Failed.")

    prompt = "Tell me a joke about AI."
    response = client.process_prompt(prompt)
    logger.info(f"Received response: {response}")

    time.sleep(10)
    client.shutdown()
