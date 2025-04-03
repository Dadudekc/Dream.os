import os
import random
import json
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple, Union

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from utils.cookie_manager import CookieManager
from social.social_config_wrapper import get_social_config
from social.log_writer import get_social_logger, write_json_log
from social.AIChatAgent import AIChatAgent
from core.DriverManager import DriverManager

logger = get_social_logger()

DEFAULT_WAIT = 10
MAX_RETRIES = 3

def retry_on_failure(max_attempts=MAX_RETRIES, delay=2):
    """Decorator to retry a function on failure with a delay between attempts."""
    def decorator_retry(func):
        @wraps(func)
        def wrapper_retry(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    logger.warning(f"Attempt {attempts} in {func.__name__} failed: {e}")
                    time.sleep(delay * attempts)
            logger.error(f"All {max_attempts} attempts failed in {func.__name__}.")
            raise Exception(f"Max retry reached for {func.__name__}")
        return wrapper_retry
    return decorator_retry

class BaseEngagementBot(ABC):
    """
    Base class for all social platform engagement bots.
    Provides unified methods for:
      - Login (cookie and credential-based, with manual fallback)
      - Community engagement actions (like, comment, follow, unfollow, viral actions)
      - Daily session orchestration.
    
    Platform-specific details are provided via abstract helper methods.
    """
    def __init__(self, platform, driver=None, wait_range=(3, 6), follow_db_path=None):
        self.platform = platform.lower()
        self.driver = driver or self.get_driver()
        self.wait_min, self.wait_max = wait_range
        self.cookie_manager = CookieManager()
        self.email = get_social_config().get_env(f"{self.platform.upper()}_EMAIL")
        self.password = get_social_config().get_env(f"{self.platform.upper()}_PASSWORD")
        self.login_url = get_social_config().get_platform_url(self.platform, "login")
        self.settings_url = get_social_config().get_platform_url(self.platform, "settings")
        self.trending_url = get_social_config().get_platform_url(self.platform, "trending")
        self.ai_agent = AIChatAgent(model="gpt-4o", tone="Victor", provider="openai")
        self.follow_db = follow_db_path or f"social/data/{self.platform}_follow_tracker.json"

    @staticmethod
    def get_driver(headless=False):
        """
        Initializes and returns a Selenium WebDriver instance.
        This helper is made static so that it can be imported and reused across strategy modules.
        """
        options = webdriver.ChromeOptions()
        profile_path = get_social_config().get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile"))
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument("--start-maximized")
        user_agent = BaseEngagementBot.get_random_user_agent()
        options.add_argument(f"user-agent={user_agent}")
        if headless:
            options.add_argument("--headless")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logger.info(f"Chrome driver initialized with profile: {profile_path}")
        return driver

    @staticmethod
    def get_random_user_agent():
        """Return a random user agent string from a predefined list."""
        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/113.0.0.0 Safari/537.36"
        ])

    def _wait(self, custom_range=None):
        """Pause execution for a random duration within the specified range."""
        wait_time = random.uniform(*(custom_range or (self.wait_min, self.wait_max)))
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)

    @retry_on_failure()
    def login(self):
        """
        Handles login using cookies first; if that fails, performs credential-based auto-login.
        Falls back to manual login if needed.
        """
        logger.info(f" Initiating login for {self.platform.capitalize()}.")
        self.driver.get(self.login_url)
        self._wait()
        self.cookie_manager.load_cookies(self.driver, self.platform)
        self.driver.refresh()
        self._wait()
        if self.is_logged_in():
            logger.info(f" Logged into {self.platform.capitalize()} via cookies.")
            write_json_log(self.platform, "successful", tags=["cookie_login"])
            return True
        if not self.email or not self.password:
            logger.warning(f"️ Missing credentials for {self.platform.capitalize()}.")
            return False
        self._login_with_credentials()
        if not self.is_logged_in():
            logger.warning(f"️ Auto-login failed for {self.platform.capitalize()}. Awaiting manual login.")
            if not self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, self.platform):
                logger.error(f" Manual login failed for {self.platform.capitalize()}.")
                return False
        self.cookie_manager.save_cookies(self.driver, self.platform)
        logger.info(f" Logged into {self.platform.capitalize()} successfully.")
        return True

    @abstractmethod
    def is_logged_in(self):
        """Check if the user is logged in (platform-specific implementation)."""
        pass

    @abstractmethod
    def _login_with_credentials(self):
        """Perform auto-login using credentials (platform-specific implementation)."""
        pass

    @abstractmethod
    def post(self, content_prompt):
        """
        Post content to the platform.
        This method should implement the logic to generate and publish content.
        """
        pass

    # -------------------------------
    # Community Engagement Methods
    # -------------------------------
    def like_posts(self):
        """Like posts from the trending page."""
        logger.info(f"️ Liking posts on {self.platform.capitalize()}...")
        self.driver.get(self.trending_url)
        self._wait((5, 8))
        posts = self._find_posts()
        for post in posts[:random.randint(3, 6)]:
            try:
                like_button = self._find_like_button(post)
                like_button.click()
                logger.info("️ Liked a post.")
                self._wait((2, 4))
            except Exception as e:
                logger.warning(f"️ Could not like post: {e}")

    def comment_on_posts(self, comments):
        """Comment on posts from the trending page using provided comment texts."""
        logger.info(f" Commenting on posts for {self.platform.capitalize()}...")
        self.driver.get(self.trending_url)
        self._wait((5, 8))
        posts = self._find_posts()
        for post, comment in zip(posts, comments):
            try:
                comment_box = self._find_comment_box(post)
                comment_box.click()
                comment_box.send_keys(comment)
                comment_box.send_keys(Keys.RETURN)
                logger.info(f" Commented: {comment}")
                self._wait((4, 6))
            except Exception as e:
                logger.warning(f"️ Could not comment on post: {e}")

    def follow_users(self):
        """Follow users based on posts from the trending page."""
        logger.info(f" Following users on {self.platform.capitalize()}...")
        self.driver.get(self.trending_url)
        self._wait((5, 8))
        users_followed = []
        posts = self._find_posts()
        for post in posts[:random.randint(2, 5)]:
            try:
                profile_url = self._find_profile_url(post)
                self.driver.get(profile_url)
                self._wait((3, 6))
                follow_button = self._find_follow_button()
                follow_button.click()
                users_followed.append(profile_url)
                logger.info(f" Followed {profile_url}")
                self._wait((10, 15))
            except Exception as e:
                logger.warning(f"️ Could not follow user: {e}")
        if users_followed:
            self._log_followed_users(users_followed)

    def unfollow_non_returners(self, days_threshold=3):
        """Unfollow users who have not reciprocated after a threshold of days."""
        logger.info(f" Unfollowing non-returners on {self.platform.capitalize()}...")
        if not os.path.exists(self.follow_db):
            logger.warning("️ No follow database found.")
            return
        with open(self.follow_db, "r") as f:
            follow_data = json.load(f)
        now = datetime.utcnow()
        unfollowed = []
        for user, data in follow_data.items():
            followed_at = datetime.fromisoformat(data["followed_at"])
            if (now - followed_at).days >= days_threshold and data.get("status") == "followed":
                try:
                    self.driver.get(user)
                    self._wait((3, 6))
                    unfollow_button = self._find_unfollow_button()
                    unfollow_button.click()
                    follow_data[user]["status"] = "unfollowed"
                    unfollowed.append(user)
                except Exception as e:
                    logger.warning(f"️ Could not unfollow {user}: {e}")
        with open(self.follow_db, "w") as f:
            json.dump(follow_data, f, indent=4)
        logger.info(f" Unfollowed {len(unfollowed)} users on {self.platform.capitalize()}.")

    def go_viral(self):
        """Perform viral engagement actions by liking and commenting on top posts."""
        logger.info(f" Activating viral mode on {self.platform.capitalize()}...")
        self.driver.get(self.trending_url)
        self._wait((3, 5))
        posts = self._find_posts()
        random.shuffle(posts)
        viral_prompt = (
            f"Compose a brief, authentic comment that is energetic, engaging, and invites discussion about "
            f"{self.platform.capitalize()} trends and system convergence."
        )
        for post in posts[:3]:
            try:
                like_button = self._find_like_button(post)
                like_button.click()
                comment = self.ai_agent.ask(viral_prompt)
                comment_box = self._find_comment_box(post)
                comment_box.click()
                comment_box.send_keys(comment)
                comment_box.send_keys(Keys.RETURN)
                logger.info(f" Viral comment posted: {comment}")
                self._wait((2, 3))
            except Exception as e:
                logger.warning(f"️ Viral action failed: {e}")

    def _log_followed_users(self, users):
        """Logs new follows to a local JSON tracker."""
        if not users:
            return
        if os.path.exists(self.follow_db):
            with open(self.follow_db, "r") as f:
                follow_data = json.load(f)
        else:
            follow_data = {}
        for user in users:
            follow_data[user] = {"followed_at": datetime.utcnow().isoformat(), "status": "followed"}
        with open(self.follow_db, "w") as f:
            json.dump(follow_data, f, indent=4)
        logger.info(f" Logged {len(users)} new follows.")

    # -------------------------------
    # Abstract Helper Methods:
    # Platform-specific implementations must provide these.
    # -------------------------------
    @abstractmethod
    def _find_posts(self):
        """Return a list of post elements."""
        pass

    @abstractmethod
    def _find_like_button(self, post):
        """Return the like button element within a post."""
        pass

    @abstractmethod
    def _find_comment_box(self, post):
        """Return the comment box element within a post."""
        pass

    @abstractmethod
    def _find_profile_url(self, post):
        """Return the profile URL from a post element."""
        pass

    @abstractmethod
    def _find_follow_button(self):
        """Return the follow button element on a user's profile."""
        pass

    @abstractmethod
    def _find_unfollow_button(self):
        """Return the unfollow button element on a user's profile."""
        pass

    # -------------------------------------------
    # Daily Session Runner
    # -------------------------------------------
    def run_daily_session(self):
        """Runs a full daily engagement session for the platform."""
        logger.info(f" Running daily session for {self.platform.capitalize()}...")
        if not self.login():
            logger.error(f" Login failed for {self.platform.capitalize()}. Ending session.")
            return
        hashtags = ["automation", "systemconvergence", "strategicgrowth"]
        comments = []
        for tag in hashtags:
            prompt = f"You are Victor. Write a raw, authentic comment about #{tag}."
            comment = self.ai_agent.ask(prompt)
            comments.append(comment)
        self.like_posts()
        self.comment_on_posts(comments)
        self.follow_users()
        self.unfollow_non_returners()
        self.go_viral()
        logger.info(f" {self.platform.capitalize()} session complete.")
