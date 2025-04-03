import os
import sys
import random
import shutil
import logging
import time
import json
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Ensure .env variables are loaded
load_dotenv()

# Absolute imports from our codebase
from utils.cookie_manager import CookieManager
from social.log_writer import get_social_logger, write_json_log
from social.social_config import social_config
from social.AIChatAgent import AIChatAgent
from social.strategies.base_platform_strategy import BasePlatformStrategy
from .strategy_config_loader import StrategyConfigLoader

logger = get_social_logger()

MAX_ATTEMPTS = 3
DEFAULT_WAIT = 10

def retry_on_failure(max_attempts=MAX_ATTEMPTS, delay=2):
    """
    Decorator to retry a function on failure with a delay between attempts.
    """
    def decorator_retry(func):
        @wraps(func)
        def wrapper_retry(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    logger.warning(f"Attempt {attempts} failed in {func.__name__} due to: {e}")
                    time.sleep(delay * attempts)
            logger.error(f"All {max_attempts} attempts failed in {func.__name__}.")
            raise Exception(f"Max retry reached for {func.__name__}")
        return wrapper_retry
    return decorator_retry

def get_random_user_agent():
    """
    Returns a random user agent string from a predefined list.
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    ]
    return random.choice(user_agents)

# -------------------------------------------------
# FacebookBot Base Class
# -------------------------------------------------
class FacebookBot:
    """
    Automates Facebook login and posting.
    This base class handles authentication and AI-powered post creation.
    """
    PLATFORM = "facebook"

    def __init__(self, driver=None, wait_range=(3, 6)):
        self.platform = self.PLATFORM
        self.driver = driver or self.get_driver()
        self.wait_min, self.wait_max = wait_range
        self.cookie_manager = CookieManager()
        self.login_url = social_config.get_platform_url(self.platform, "login")
        self.post_url = social_config.get_platform_url(self.platform, "post")
        self.settings_url = social_config.get_platform_url(self.platform, "settings")
        self.email = social_config.get_env("FACEBOOK_EMAIL")
        self.password = social_config.get_env("FACEBOOK_PASSWORD")
        self.ai_agent = AIChatAgent(model="gpt-4o", tone="Victor", provider="openai")

    def _wait(self, custom_range=None):
        wait_time = random.uniform(*(custom_range or (self.wait_min, self.wait_max)))
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)

    def get_driver(self):
        chrome_options = webdriver.ChromeOptions()
        profile_path = social_config.get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile"))
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(f"--user-data-dir={profile_path}")
        chrome_options.add_argument(f"user-agent={get_random_user_agent()}")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info(f"Chrome driver initialized with profile: {profile_path}")
        return driver

    @retry_on_failure()
    def is_logged_in(self):
        """
        Verify login by navigating to the Facebook settings page.
        """
        self.driver.get(self.settings_url)
        WebDriverWait(self.driver, DEFAULT_WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self._wait((3, 5))
        if "login" not in self.driver.current_url.lower():
            logger.info(f" {self.platform.capitalize()} login confirmed via settings.")
            return True
        logger.debug(f" {self.platform.capitalize()} login check failed.")
        return False

    @retry_on_failure()
    def login(self):
        """
        Automate the Facebook login flow.
        """
        logger.info(f" Initiating login process for {self.platform.capitalize()}.")
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
            logger.warning(f"️ No {self.platform} credentials provided.")
            write_json_log(self.platform, "failed", tags=["auto_login"], ai_output="Missing credentials.")
            return False
        try:
            email_field = WebDriverWait(self.driver, DEFAULT_WAIT).until(EC.visibility_of_element_located((By.ID, "email")))
            pass_field = WebDriverWait(self.driver, DEFAULT_WAIT).until(EC.visibility_of_element_located((By.ID, "pass")))
            email_field.clear()
            pass_field.clear()
            email_field.send_keys(self.email)
            pass_field.send_keys(self.password)
            pass_field.send_keys(Keys.RETURN)
            logger.info(f" Submitted credentials for {self.platform.capitalize()}.")
            WebDriverWait(self.driver, DEFAULT_WAIT).until(EC.url_changes(self.login_url))
            self._wait((5, 10))
        except Exception as e:
            logger.error(f" Error during {self.platform.capitalize()} auto-login: {e}")
            write_json_log(self.platform, "failed", tags=["auto_login"], ai_output=str(e))
        if not self.is_logged_in():
            logger.warning(f"️ Auto-login failed for {self.platform.capitalize()}. Awaiting manual login...")
            if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, self.platform):
                write_json_log(self.platform, "successful", tags=["manual_login"])
            else:
                msg = "Manual login failed."
                logger.error(f" {msg} for {self.platform.capitalize()}.")
                write_json_log(self.platform, "failed", tags=["manual_login"], ai_output=msg)
                return False
        self.cookie_manager.save_cookies(self.driver, self.platform)
        logger.info(f" Logged in successfully to {self.platform.capitalize()}.")
        write_json_log(self.platform, "successful", tags=["auto_login"])
        return True

    @retry_on_failure()
    def post(self, content_prompt):
        """
        Publish a Facebook post with AI-generated content.
        """
        logger.info(f" Attempting to post on {self.platform.capitalize()}.")
        if not self.is_logged_in():
            msg = "Not logged in."
            logger.warning(f"️ Cannot post to {self.platform.capitalize()}: {msg}")
            write_json_log(self.platform, "failed", tags=["post"], ai_output=msg)
            return {"platform": self.platform, "status": "failed", "details": msg}
        content = self.ai_agent.ask(
            prompt=content_prompt,
            additional_context="This post reflects my authentic, raw, and strategic voice.",
            metadata={"platform": "Facebook", "persona": "Victor"}
        ) or content_prompt
        try:
            self.driver.get(self.post_url)
            self._wait((5, 8))
            create_post_button = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Create a post']"))
            )
            create_post_button.click()
            self._wait((2, 3))
            post_box = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.visibility_of_element_located((By.XPATH, "//div[@role='textbox']"))
            )
            post_box.send_keys(content)
            self._wait((2, 3))
            post_button = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Post']"))
            )
            post_button.click()
            self._wait((5, 8))
            logger.info(f" Post published on {self.platform.capitalize()} in my authentic voice.")
            write_json_log(self.platform, "successful", tags=["post"])
            return {"platform": self.platform, "status": "success", "details": "Post published"}
        except Exception as e:
            logger.error(f" Failed to post on {self.platform.capitalize()}: {e}")
            write_json_log(self.platform, "failed", tags=["post"], ai_output=str(e))
            return {"platform": self.platform, "status": "failed", "details": str(e)}

# -------------------------------------------------
# FacebookEngagementBot Class
# -------------------------------------------------
class FacebookEngagementBot(FacebookBot):
    """
    Extends FacebookBot with essential community building functions:
      - Like posts, comment, follow/unfollow users, and viral engagement.
      - Maintains a FOLLOW_DB to track engagements.
      - Runs daily engagement sessions.
    """
    FOLLOW_DB = "social/data/friend_tracker.json"

    def like_posts(self):
        """
        Like posts on Facebook pages or groups.
        """
        trending_url = social_config.get_platform_url(self.platform, "trending")
        self.driver.get(trending_url)
        self._wait((5, 8))
        posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-pagelet='FeedUnit']")
        liked = 0
        for post in posts:
            if liked >= random.randint(3, 6):
                break
            try:
                like_button = post.find_element(By.XPATH, ".//div[contains(@aria-label, 'Like')]")
                like_button.click()
                logger.info("️ Liked a post on Facebook.")
                liked += 1
                self._wait((2, 4))
            except Exception as e:
                logger.warning(f"️ Could not like a post: {e}")

    def comment_on_posts(self, comments):
        """
        Comment on posts with AI-generated content.
        """
        trending_url = social_config.get_platform_url(self.platform, "trending")
        self.driver.get(trending_url)
        self._wait((5, 8))
        posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-pagelet='FeedUnit']")
        commented = 0
        for post in posts:
            if commented >= random.randint(2, 4):
                break
            try:
                comment_box = post.find_element(By.XPATH, ".//div[contains(@aria-label, 'Write a comment')]")
                comment = random.choice(comments)
                comment_box.click()
                comment_box.send_keys(comment)
                comment_box.send_keys(Keys.RETURN)
                logger.info(f" Commented: '{comment}' on a post.")
                commented += 1
                self._wait((4, 6))
            except Exception as e:
                logger.warning(f"️ Could not comment on a post: {e}")

    def follow_users(self):
        """
        Follow users by sending friend requests based on post interactions.
        """
        trending_url = social_config.get_platform_url(self.platform, "trending")
        self.driver.get(trending_url)
        self._wait((5, 8))
        posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-pagelet='FeedUnit']")
        followed = 0
        followed_users = []
        for post in posts:
            if followed >= random.randint(2, 5):
                break
            try:
                profile_link = post.find_element(By.XPATH, ".//a[contains(@href, 'profile.php') or contains(@href, '/')]")
                profile_url = profile_link.get_attribute("href")
                self.driver.get(profile_url)
                self._wait((3, 6))
                follow_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Add Friend') or contains(text(), 'Follow')]")
                follow_button.click()
                logger.info(f" Sent friend request to: {profile_url}")
                write_json_log(self.platform, "successful", tags=["follow"], ai_output=profile_url)
                followed += 1
                followed_users.append(profile_url)
                self._wait((10, 15))
            except Exception as e:
                logger.error(f" Error following user from post: {e}")
        return followed_users

    def unfollow_non_returners(self, days_threshold=3):
        """
        Unfollow users who haven't reciprocated the connection after a threshold.
        """
        if not os.path.exists(self.FOLLOW_DB):
            logger.warning("️ No friend tracker data found.")
            return
        with open(self.FOLLOW_DB, "r") as f:
            follow_data = json.load(f)
        now = datetime.utcnow()
        unfollowed = []
        for user, data in follow_data.items():
            followed_at = datetime.fromisoformat(data["followed_at"])
            if (now - followed_at).days >= days_threshold and data.get("status") == "followed":
                try:
                    self.driver.get(user)
                    self._wait((3, 6))
                    unfollow_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Friends') or contains(text(), 'Following')]")
                    unfollow_button.click()
                    self._wait((1, 3))
                    confirm_button = self.driver.find_element(By.XPATH, "//button[text()='Unfriend']")
                    confirm_button.click()
                    logger.info(f" Unfriended: {user}")
                    follow_data[user]["status"] = "unfriended"
                    unfollowed.append(user)
                except Exception as e:
                    logger.error(f" Error unfriending {user}: {e}")
        with open(self.FOLLOW_DB, "w") as f:
            json.dump(follow_data, f, indent=4)
        logger.info(f" Unfriended {len(unfollowed)} users.")

    def _log_followed_users(self, users):
        """
        Log new friend requests in a tracker for future follow-up.
        """
        if not users:
            return
        if os.path.exists(self.FOLLOW_DB):
            with open(self.FOLLOW_DB, "r") as f:
                follow_data = json.load(f)
        else:
            follow_data = {}
        for user in users:
            follow_data[user] = {"followed_at": datetime.utcnow().isoformat(), "status": "followed"}
        with open(self.FOLLOW_DB, "w") as f:
            json.dump(follow_data, f, indent=4)
        logger.info(f" Logged {len(users)} new friend requests.")

    def go_viral(self):
        """
        Engage with trending posts by liking and commenting with AI-generated viral content.
        """
        viral_prompt = (
            "Compose a brief, authentic comment that is energetic, engaging, and invites discussion "
            "about market trends and system convergence."
        )
        trending_url = social_config.get_platform_url(self.platform, "trending")
        self.driver.get(trending_url)
        self._wait((3, 5))
        posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-pagelet='FeedUnit']")
        if not posts:
            logger.warning("️ No trending posts found for viral engagement.")
            return
        random.shuffle(posts)
        for post in posts[:3]:
            try:
                like_button = post.find_element(By.XPATH, ".//div[contains(@aria-label, 'Like')]")
                like_button.click()
                logger.info("⬆️ Viral mode: Liked a trending post.")
                self._wait((1, 2))
                post_content = post.text
                comment = self.ai_agent.ask(
                    prompt=viral_prompt,
                    additional_context=f"Post content: {post_content}",
                    metadata={"platform": "Facebook", "persona": "Victor", "engagement": "viral"}
                )
                comment_box = post.find_element(By.XPATH, ".//div[contains(@aria-label, 'Write a comment')]")
                comment_box.click()
                comment_box.send_keys(comment)
                comment_box.send_keys(Keys.RETURN)
                logger.info(f" Viral mode: Commented: {comment}")
                self._wait((2, 3))
            except Exception as e:
                logger.warning(f"️ Viral engagement error on a trending post: {e}")
                continue

    def run_daily_session(self):
        """
        Run a full daily engagement session:
          - Log in (if needed)
          - Like posts, comment, follow users, unfollow non-returners, and go viral.
        """
        logger.info(" Starting Facebook Daily Engagement Session")
        if not self.login():
            logger.error(" Facebook login failed. Ending session.")
            return
        # Generate AI-powered comments for engagement
        comments = []
        for tag in ["systemconvergence", "strategicgrowth", "automation"]:
            prompt = (
                f"You are Victor. Write a raw, authentic comment on a post about #{tag}. "
                "Inspire deep community discussion."
            )
            response = self.ai_agent.ask(prompt)
            comments.append(response.strip())
        self.like_posts()
        self.comment_on_posts(comments)
        followed = self.follow_users()
        if followed:
            self._log_followed_users(followed)
        self.unfollow_non_returners()
        self.go_viral()
        logger.info(" Facebook Daily Engagement Session Complete.")

# -------------------------------------------------
# FacebookStrategy Class (Extending BasePlatformStrategy)
# -------------------------------------------------
class FacebookStrategy(BasePlatformStrategy):
    """
    Centralized strategy class for Facebook automation, community building,
    and dynamic feedback loops, leveraging StrategyConfigLoader.
    Extends BasePlatformStrategy with specific Facebook logic and integrates
    feedback mechanisms.
    """
    PLATFORM = "facebook"
    FEEDBACK_DB = "social/data/facebook_feedback_tracker.json"
    REWARD_DB = "social/data/facebook_reward_tracker.json"

    def __init__(self, driver=None):
        super().__init__(self.PLATFORM, driver)
        self.config_loader = StrategyConfigLoader(platform=self.PLATFORM)
        self.ai_agent = AIChatAgent(
            model=self.config_loader.get_parameter("ai_model", "gpt-4o"),
            tone=self.config_loader.get_parameter("ai_comment_tone", "Victor"),
            provider=self.config_loader.get_parameter("ai_provider", "openai")
        )
        self.cookie_manager = CookieManager()
        self.feedback_data = self._load_feedback_data()
        self.email = None
        self.password = None

    def initialize(self, credentials: Dict[str, str]) -> bool:
        logger.info(f"Initializing FacebookStrategy...")
        self.email = credentials.get("email")
        self.password = credentials.get("password")
        if not self.email or not self.password:
            logger.error("Facebook credentials (email, password) not provided for initialization.")
            return False
        if not self.driver:
            self.driver = self._get_driver()
        return self.login()

    def cleanup(self) -> bool:
        logger.info("Cleaning up FacebookStrategy resources...")
        return super().cleanup()

    def get_community_metrics(self) -> Dict[str, Any]:
        logger.info("Retrieving Facebook community metrics...")
        target_keywords = self.config_loader.get_parameter("targeting_keywords", default=[])
        metrics = {
            "platform": self.PLATFORM,
            "engagement_rate_estimate": self.config_loader.get_parameter("estimated_engagement_rate", default=1.2),
            "target_keywords": target_keywords,
            "current_post_frequency": self.config_loader.get_parameter("post_frequency_per_day", default=1),
            "active_members_estimate": random.randint(50, 200),
            "sentiment_score": self.feedback_data.get("overall_sentiment", 0.7)
        }
        logger.debug(f"Facebook Metrics: {metrics}")
        return metrics

    def get_top_members(self) -> List[Dict[str, Any]]:
        logger.info("Identifying top Facebook members (placeholder)...")
        top_members = [
            {"member_id": "user123", "engagement_score": 95, "last_interaction": "2024-07-28"},
            {"member_id": "user456", "engagement_score": 88, "last_interaction": "2024-07-27"},
        ]
        return top_members

    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        logger.info(f"Tracking Facebook interaction: Member={member_id}, Type={interaction_type}")
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "member_id": member_id,
            "interaction_type": interaction_type,
            "metadata": metadata or {}
        }
        interactions = self.feedback_data.setdefault("interactions", [])
        interactions.append(log_entry)
        self._save_feedback_data()
        logger.debug(f"Interaction logged: {log_entry}")
        return True

    def _get_driver(self):
        if not self.driver:
            logger.info("FacebookStrategy: No driver found, attempting initialization via BasePlatformStrategy.")
            self.driver = super()._get_driver()
        return self.driver

    @staticmethod
    def get_random_user_agent():
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        ]
        return random.choice(user_agents)

    def _wait(self, custom_range=None):
        wait_range = custom_range or self.config_loader.get_parameter("wait_range_seconds", default=(2, 5))
        wait_time = random.uniform(*wait_range)
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)

    def login(self) -> bool:
        logger.info(f"Initiating login process for {self.PLATFORM}.")
        if not self._get_driver():
            logger.error("Cannot login: WebDriver is not initialized.")
            return False
        if not self.email or not self.password:
            logger.error("Cannot login: Email or password not set during initialization.")
            return False

        login_url = self.config_loader.get_platform_url("login")
        settings_url = self.config_loader.get_platform_url("settings")
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=10)

        try:
            self.driver.get(login_url)
            self._wait()
            self.cookie_manager.load_cookies(self.driver, self.PLATFORM)
            self.driver.refresh()
            self._wait()

            self.driver.get(settings_url)
            WebDriverWait(self.driver, default_wait).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            if "login" not in self.driver.current_url.lower():
                logger.info(f"Logged into {self.PLATFORM} via cookies or existing session.")
                write_json_log(self.PLATFORM, "successful", tags=["cookie_login"])
                return True

            logger.info("Cookie/Session login failed. Attempting credential login.")
            self.driver.get(login_url)
            self._wait()

            email_field = WebDriverWait(self.driver, default_wait).until(EC.visibility_of_element_located((By.ID, "email")))
            pass_field = WebDriverWait(self.driver, default_wait).until(EC.visibility_of_element_located((By.ID, "pass")))
            email_field.clear()
            pass_field.clear()
            email_field.send_keys(self.email)
            pass_field.send_keys(self.password)
            pass_field.send_keys(Keys.RETURN)
            logger.info(f"Submitted credentials for {self.PLATFORM}.")
            self._wait((5, 10))

            self.driver.get(settings_url)
            WebDriverWait(self.driver, default_wait).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            if "login" not in self.driver.current_url.lower():
                logger.info(f"Logged in successfully to {self.PLATFORM} using credentials.")
                self.cookie_manager.save_cookies(self.driver, self.PLATFORM)
                write_json_log(self.PLATFORM, "successful", tags=["credential_login"])
                return True
            else:
                logger.error(f"Credential login failed for {self.PLATFORM}.")
                write_json_log(self.PLATFORM, "failed", tags=["credential_login"], ai_output="Login page still detected after credential submission.")
            return False

        except Exception as e:
            logger.error(f"Error during {self.PLATFORM} login: {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["login_error"], ai_output=str(e))
            return False

    def is_logged_in(self) -> bool:
        if not self.driver:
            return False
        settings_url = self.config_loader.get_platform_url("settings")
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=5)
        try:
            current_url = self.driver.current_url
            if "facebook.com" in current_url and "login" not in current_url and "checkpoint" not in current_url:
                pass
            else:
                self.driver.get(settings_url)
                WebDriverWait(self.driver, default_wait).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                self._wait((1, 2))

            if "login" not in self.driver.current_url.lower() and "checkpoint" not in self.driver.current_url.lower():
                logger.debug(f"{self.PLATFORM} login confirmed via URL check ({self.driver.current_url}).")
                return True
            logger.debug(f"{self.PLATFORM} login check failed (URL: {self.driver.current_url}).")
            return False
        except Exception as e:
            logger.warning(f"Error during {self.PLATFORM} login check: {e}")
            return False

    def post_content(self, content: str) -> bool:
        logger.info(f"Attempting to post on {self.PLATFORM}.")
        if not self.is_logged_in():
            logger.warning(f"Cannot post to {self.PLATFORM}: Not logged in.")
            if not self.login():
                write_json_log(self.PLATFORM, "failed", tags=["post", "login_required"], ai_output="Login failed before posting.")
                return False

        post_url = self.config_loader.get_platform_url("post")
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=10)

        try:
            self.driver.get(self.driver.current_url if "facebook.com" in self.driver.current_url else post_url)
            self._wait((3, 5))

            composer_trigger_xpath = "//div[@role='button' and contains(@aria-label, 'mind')]"
            try:
                create_post_button = WebDriverWait(self.driver, default_wait).until(
                    EC.element_to_be_clickable((By.XPATH, composer_trigger_xpath))
                )
                create_post_button.click()
                logger.debug("Clicked main composer trigger.")
            except TimeoutException:
                logger.debug("Main composer trigger not found or clicked, checking for direct textbox.")
                pass

            self._wait((2, 4))

            post_box_xpath = "//div[@aria-label=\"What's on your mind?\"] | //div[@role='textbox']"
            post_box = WebDriverWait(self.driver, default_wait).until(
                EC.visibility_of_element_located((By.XPATH, post_box_xpath))
            )
            post_box.send_keys(content)
            logger.debug("Entered content into post box.")
            self._wait((2, 3))

            post_button_xpath = "//div[@aria-label='Post' and @role='button']"
            post_button = WebDriverWait(self.driver, default_wait).until(
                EC.element_to_be_clickable((By.XPATH, post_button_xpath))
            )
            post_button.click()
            logger.info(f"Post submitted on {self.PLATFORM}.")
            self._wait((5, 10))

            logger.info(f"Content posted successfully on {self.PLATFORM}.")
            write_json_log(self.PLATFORM, "successful", tags=["post"])
            return True

        except Exception as e:
            logger.error(f"Failed to post on {self.PLATFORM}: {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["post", "error"], ai_output=str(e))
            return False

    def run_daily_strategy_session(self):
        logger.info(f"===== Starting Daily Facebook Strategy Session =====")
        if not self.config_loader.is_enabled():
            logger.warning(f"{self.PLATFORM.capitalize()} strategy is disabled in configuration. Session aborted.")
            return

        if not self.is_logged_in():
            logger.warning("Not logged in at start of session. Attempting login...")
            if not self.login():
                logger.error("Session failed: Could not log in.")
                return

        post_freq = self.config_loader.get_parameter("post_frequency_per_day", default=1)
        keywords = self.config_loader.get_parameter("targeting_keywords", default=["AI", "startups", "community building"])
        content_mix = self.config_loader.get_parameter("content_mix", default={"text_post": 1.0})

        logger.info(f"Session Config: Post Freq={post_freq}, Keywords={keywords}, Content Mix={content_mix}")

        for i in range(post_freq):
            logger.info(f"--- Preparing Post {i+1}/{post_freq} ---")
            chosen_type = random.choices(list(content_mix.keys()), weights=list(content_mix.values()), k=1)[0] if content_mix else "text_post"
            logger.debug(f"Selected content type: {chosen_type}")

            topic = random.choice(keywords) if keywords else "general update"
            content_prompt = f"Generate a concise, engaging {chosen_type} for Facebook about '{topic}'. Focus on sparking discussion or sharing a unique insight. Persona: Victor."

            ai_content = self.ai_agent.ask(content_prompt)

            if ai_content:
                logger.info(f"Posting content about '{topic}'...")
                if not self.post_content(ai_content):
                    logger.error(f"Failed to post content piece {i+1}.")
            else:
                logger.warning(f"AI failed to generate content for prompt: {content_prompt}")
            self._wait()

        if self.config_loader.get_parameter("enable_engagement", default=True):
            logger.info("--- Starting Community Engagement Phase ---")
            num_likes = self.config_loader.get_parameter("engagement_likes_per_run", default=3)
            num_comments = self.config_loader.get_parameter("engagement_comments_per_run", default=2)
            ai_tone = self.config_loader.get_parameter("ai_comment_tone", default="Victor")
            self.ai_agent.tone = ai_tone

            if num_likes > 0:
                logger.info(f"Attempting to like up to {num_likes} posts...")
                logger.warning("like_posts functionality needs implementation/integration.")

            if num_comments > 0 and keywords:
                logger.info(f"Attempting to comment on up to {num_comments} posts...")
                logger.warning("comment_on_posts functionality needs implementation/integration.")
            elif num_comments > 0:
                logger.warning("No keywords defined for targeted commenting.")

            logger.warning("Follow/Unfollow logic needs implementation/integration.")

        else:
            logger.info("Community engagement is disabled in configuration.")

        if self.config_loader.get_parameter("enable_feedback_loop", default=True):
            logger.info("--- Running Feedback Loop ---")
            self.run_feedback_loop()
        else:
            logger.info("Feedback loop is disabled in configuration.")

        logger.info(f"===== Daily Facebook Strategy Session Complete =====")

    def _load_feedback_data(self):
        feedback_db_path = self.config_loader.get_data_path(self.FEEDBACK_DB)
        logger.debug(f"Loading feedback data from: {feedback_db_path}")
        if os.path.exists(feedback_db_path):
            try:
                with open(feedback_db_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON from {feedback_db_path}. Starting with empty data.")
                return {}
            except Exception as e:
                logger.error(f"Error loading feedback data: {e}")
                return {}
        return {}

    def _save_feedback_data(self):
        feedback_db_path = self.config_loader.get_data_path(self.FEEDBACK_DB)
        logger.debug(f"Saving feedback data to: {feedback_db_path}")
        try:
            os.makedirs(os.path.dirname(feedback_db_path), exist_ok=True)
            with open(feedback_db_path, "w") as f:
                json.dump(self.feedback_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving feedback data: {e}")

    def analyze_engagement_metrics(self):
        logger.info("Analyzing Facebook engagement metrics (placeholder)...")
        posts = self.feedback_data.get("posts", [])
        total_likes = sum(p.get("likes", 0) for p in posts)
        total_comments = sum(p.get("comments", 0) for p in posts)
        avg_likes = total_likes / len(posts) if posts else 0
        avg_comments = total_comments / len(posts) if posts else 0

        self.feedback_data["avg_likes_per_post"] = avg_likes
        self.feedback_data["avg_comments_per_post"] = avg_comments
        self.feedback_data["overall_sentiment"] = self.feedback_data.get("overall_sentiment", 0.7) * 0.9 + random.uniform(-0.1, 0.1) * 0.1

        logger.info(f"Updated Metrics - Avg Likes: {avg_likes:.2f}, Avg Comments: {avg_comments:.2f}, Sentiment: {self.feedback_data['overall_sentiment']:.2f}")
        self._save_feedback_data()

    def adaptive_posting_strategy(self):
        logger.info("Adapting Facebook posting strategy based on feedback (placeholder)...")
        avg_likes = self.feedback_data.get("avg_likes_per_post", 0)
        sentiment = self.feedback_data.get("overall_sentiment", 0.5)

        if avg_likes > self.config_loader.get_parameter("engagement_high_threshold_likes", 50) and sentiment > 0.6:
            logger.info("Feedback positive: Consider increasing post frequency or using more engaging content types.")
        elif avg_likes < self.config_loader.get_parameter("engagement_low_threshold_likes", 10) or sentiment < 0.4:
            logger.warning("Feedback indicates low engagement: Review content strategy, keywords, or posting times.")

    def analyze_comment_sentiment(self, comment: str) -> str:
        logger.debug(f"Analyzing sentiment for comment: {comment[:50]}...")
        sentiment_prompt = f"Analyze the sentiment of this Facebook comment: '{comment}'. Respond with only 'positive', 'neutral', or 'negative'."
        sentiment = self.ai_agent.ask(prompt=sentiment_prompt, metadata={"platform": self.PLATFORM, "task": "sentiment_analysis"})
        sentiment = sentiment.strip().lower() if sentiment else "neutral"
        if sentiment not in ["positive", "neutral", "negative"]:
            logger.warning(f"Unexpected sentiment analysis result: '{sentiment}'. Defaulting to neutral.")
            sentiment = "neutral"
        logger.info(f"Comment sentiment classified as: {sentiment}")
        return sentiment

    def reinforce_engagement(self, comment: str, comment_author_id: str):
        sentiment = self.analyze_comment_sentiment(comment)
        if sentiment == "positive":
            logger.info(f"Positive comment detected from {comment_author_id}. Generating reinforcement...")
            reinforcement_prompt = f"As Victor, write a brief, appreciative, and engaging reply to this positive Facebook comment: '{comment}'"
            reply = self.ai_agent.ask(prompt=reinforcement_prompt, metadata={"platform": self.PLATFORM, "persona": "Victor", "task": "reinforce_engagement"})

            if reply:
                logger.info(f"Generated reinforcement reply: {reply}")
                self.track_member_interaction(comment_author_id, "positive_comment_received", {"comment": comment, "intended_reply": reply})
                return reply
            else:
                logger.warning("AI failed to generate reinforcement reply.")
        else:
            logger.debug(f"Comment sentiment ({sentiment}) does not warrant reinforcement.")

        return None

    def reward_top_followers(self):
        logger.info("Evaluating top Facebook followers for rewards (placeholder)...")
        reward_db_path = self.config_loader.get_data_path(self.REWARD_DB)
        reward_data = {}
        if os.path.exists(reward_db_path):
            try:
                with open(reward_db_path, "r") as f:
                    reward_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading reward data from {reward_db_path}: {e}")

        top_members = self.get_top_members()
        if top_members:
            potential_rewardee = top_members[0]
            member_id = potential_rewardee["member_id"]

            if member_id not in reward_data or (datetime.utcnow() - datetime.fromisoformat(reward_data[member_id]["rewarded_at"])).days > 30:
                logger.info(f"Identified potential top engager: {member_id}")
                reward_message = f"Huge thanks to {member_id} for being a standout member of our Facebook community! Your engagement is truly appreciated. ✨"
                logger.warning(f"Actual reward action for {member_id} not implemented. Logging intent.")

                reward_data[member_id] = {
                    "rewarded_at": datetime.utcnow().isoformat(),
                    "type": "shoutout_placeholder",
                    "message_logged": reward_message
                }
                try:
                    os.makedirs(os.path.dirname(reward_db_path), exist_ok=True)
                    with open(reward_db_path, "w") as f:
                        json.dump(reward_data, f, indent=4)
                    logger.info(f"Reward logged for {member_id}.")
                    write_json_log(self.PLATFORM, "success", tags=["reward"], ai_output=f"Logged reward intent for {member_id}")
                except Exception as e:
                    logger.error(f"Failed to save reward data: {e}")
            else:
                logger.info(f"Top member {member_id} already rewarded recently.")
        else:
            logger.info("No top members identified for rewards in this cycle.")

    def cross_platform_feedback_loop(self):
        logger.info("Merging cross-platform feedback loops (placeholder)...")
        unified_metrics = {
            "facebook": self.feedback_data.get("avg_likes_per_post", 0),
        }
        logger.info(f"Unified Metrics (Placeholder): {unified_metrics}")

    def run_feedback_loop(self):
        logger.info("--- Running Facebook Feedback Analysis ---")
        self.analyze_engagement_metrics()
        logger.info("--- Running Facebook Adaptive Strategy ---")
        self.adaptive_posting_strategy()

# ------------------------------------------------------
# Scheduler Setup for Facebook Strategy Engagement
# ------------------------------------------------------
def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    bot = FacebookStrategy(driver=driver)
    scheduler = BackgroundScheduler()

    for _ in range(3):
        hour = random.randint(8, 22)
        minute = random.randint(0, 59)
        scheduler.add_job(bot.run_daily_strategy_session, 'cron', hour=hour, minute=minute)

    scheduler.start()
    logger.info(" Scheduler started for Facebook strategy engagement.")

# ------------------------------------------------------
# Functional Wrapper for Quick Facebook Posting
# ------------------------------------------------------
def post_to_facebook(driver, content, env):
    fb_bot = FacebookBot(driver=driver)
    return fb_bot.post(content)

# ------------------------------------------------------
# Main Entry Point for Autonomous Execution
# ------------------------------------------------------
if __name__ == "__main__":
    print("Running FacebookStrategy directly for testing...")
    strategy = FacebookStrategy()
    creds = {
        "email": social_config.get_env("FACEBOOK_EMAIL"),
        "password": social_config.get_env("FACEBOOK_PASSWORD")
    }
    if strategy.initialize(creds):
        print("Strategy initialized.")
        if strategy.is_logged_in() or strategy.login():
            print("Login successful or already logged in.")
            strategy.run_daily_strategy_session()
        else:
            print("Login failed. Aborting test.")
    else:
        print("Strategy initialization failed.")

    strategy.cleanup()
    print("FacebookStrategy direct test finished.")
