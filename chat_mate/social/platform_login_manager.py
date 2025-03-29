"""
D:\\overnight_scripts\\chat_mate\\social\\platform_login_manager.py
Unified Platform Login + Post Automation with FULL SYNC
"""

import os
import time
import pickle
import threading
import json
import logging
from typing import List, Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException
)

# ✅ Fixed Imports
from utils.cookie_manager import CookieManager
from social.social_config_wrapper import get_social_config
from social.log_writer import write_json_log
from social.strategies import (
    twitter_strategy,
    facebook_strategy,
    instagram_strategy,
    reddit_strategy,
    stocktwits_strategy,
    linkedin_strategy
)
from core.DriverManager import DriverManager

logger = logging.getLogger(__name__)

COOKIES_DIR = os.path.join(os.getcwd(), "social", "cookies")
os.makedirs(COOKIES_DIR, exist_ok=True)

MAX_ATTEMPTS = 3

# ----------------------------------------
# Cookie Management Utilities
# ----------------------------------------
def load_cookies(driver, platform):
    cookie_file = os.path.join(COOKIES_DIR, f"{platform}.pkl")
    if not os.path.exists(cookie_file):
        logger.info(f"️ No cookies found for {platform}.")
        return
    with open(cookie_file, "rb") as f:
        cookies = pickle.load(f)
        for cookie in cookies:
            cookie.pop("sameSite", None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.error(f" Failed to load a cookie for {platform}: {e}")
    logger.info(f" Cookies loaded for {platform}")

def save_cookies(driver, platform):
    cookie_file = os.path.join(COOKIES_DIR, f"{platform}.pkl")
    with open(cookie_file, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    logger.info(f" Cookies saved for {platform}")

def wait_for_manual_login(driver, platform, validate_func, attempts=MAX_ATTEMPTS):
    attempt = 0
    while attempt < attempts:
        input(f"➡️ Manually login to {platform}. Press ENTER when done...")
        if validate_func(driver):
            logger.info(f" {platform.capitalize()} manual login successful.")
            save_cookies(driver, platform)
            write_json_log(platform, "successful", tags=["manual_login"])
            return True
        logger.warning(f" {platform.capitalize()} login validation failed.")
        attempt += 1
    logger.error(f" Maximum manual login attempts reached for {platform}.")
    return False

# ----------------------------------------
# Unified Platform Strategy Class
# ----------------------------------------
class PlatformStrategy:
    def __init__(self, strategy_module, driver):
        self.strategy = strategy_module
        self.platform = strategy_module.PLATFORM
        self.driver = driver

    def login(self):
        logger.info(f" Logging into {self.platform}...")
        try:
            self.driver.get(self.strategy.LOGIN_URL)
            time.sleep(2)
            load_cookies(self.driver, self.platform)
            self.driver.refresh()
            time.sleep(3)

            if self.strategy.is_logged_in(self.driver):
                logger.info(f" {self.platform} login restored via cookies.")
                write_json_log(self.platform, "successful", tags=["cookie_login"])
                return True

            if self.strategy.login(self.driver) and self.strategy.is_logged_in(self.driver):
                logger.info(f" {self.platform} auto-login successful.")
                save_cookies(self.driver, self.platform)
                write_json_log(self.platform, "successful", tags=["auto_login"])
                return True

            logger.warning(f"️ Auto-login failed for {self.platform}. Prompting manual login...")
            return wait_for_manual_login(self.driver, self.platform, self.strategy.is_logged_in)

        except Exception as e:
            logger.error(f" Error during {self.platform} login: {e}")
            write_json_log(self.platform, "failed", tags=["error"], ai_output=str(e))
            return False

    def post(self, content):
        logger.info(f" Posting to {self.platform}: {content}")
        try:
            post_result = self.strategy.post(self.driver, content)
            logger.info(f" Post result for {self.platform}: {post_result}")
            write_json_log(self.platform, "successful", tags=["post"])
        except Exception as e:
            logger.error(f" Failed to post on {self.platform}: {e}")
            write_json_log(self.platform, "failed", tags=["post"], ai_output=str(e))

# ----------------------------------------
# Dispatcher for All Platforms
# ----------------------------------------
class SocialPlatformDispatcher:
    def __init__(self, memory_update, headless=True):
        self.memory_update = memory_update
        self.session_ids = ["session_twitter", "session_facebook", "session_instagram",
                            "session_reddit", "session_stocktwits", "session_linkedin"]
        self.platforms = [
            twitter_strategy,
            facebook_strategy,
            instagram_strategy,
            reddit_strategy,
            stocktwits_strategy,
            linkedin_strategy
        ]
        self.driver_sessions = get_multi_driver_sessions(
            session_ids=self.session_ids,
            proxy_rotation=True,
            headless=headless
        )

    def dispatch_all(self):
        logger.info(" Starting multi-platform dispatch cycle...")
        threads = []
        for index, strategy in enumerate(self.platforms):
            driver_session = self.driver_sessions[index]
            dispatcher = PlatformStrategy(strategy_module=strategy, driver=driver_session.driver)

            # Build post content from memory_update (or use fallback)
            content = self._generate_content(strategy.PLATFORM)

            thread = threading.Thread(target=self._process_platform, args=(dispatcher, content))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        logger.info(" Dispatch cycle complete. Shutting down drivers...")
        self._shutdown_all_drivers()

    def _process_platform(self, dispatcher, content):
        if dispatcher.login():
            dispatcher.post(content)
        else:
            logger.warning(f" Skipping post for {dispatcher.platform} — login failed.")

    def _generate_content(self, platform):
        # Dynamic content generation from memory_update
        quests = self.memory_update.get("quest_completions", [])
        protocols = self.memory_update.get("newly_unlocked_protocols", [])
        loops = self.memory_update.get("feedback_loops_triggered", [])

        if platform == "linkedin":
            return f"🔗 Quest Complete: {quests[0]}\nNew Protocol: {protocols[0]}\nLoops Activated: {', '.join(loops)}"
        elif platform == "twitter":
            return f"🚀 Quest Complete: {quests[0]} - Protocols Deployed: {protocols[0]}"
        else:
            return f"📣 New Updates: {quests[0]} & Protocol {protocols[0]}"

    def _shutdown_all_drivers(self):
        for session in self.driver_sessions:
            session.shutdown_driver()
            session.cleanup_profile()

# ----------------------------------------
# Main Execution Block
# ----------------------------------------
if __name__ == "__main__":
    # Mock memory update for testing
    example_memory_update = {
        "quest_completions": ["Unified Social Authentication Rituals"],
        "newly_unlocked_protocols": ["Unified Social Logging Protocol (social_config)"],
        "feedback_loops_triggered": ["Social Media Auto-Dispatcher Loop"]
    }

    dispatcher = SocialPlatformDispatcher(memory_update=example_memory_update, headless=False)
    dispatcher.dispatch_all()
