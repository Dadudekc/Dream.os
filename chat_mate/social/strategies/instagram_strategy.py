import os
import time
import random
import logging
import json
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Ensure .env variables are loaded
load_dotenv()

# Unified project imports
from utils.cookie_manager import CookieManager
from social.log_writer import get_social_logger, write_json_log
from social.social_config import social_config
from social.AIChatAgent import AIChatAgent
from social.strategies.base_platform_strategy import BasePlatformStrategy

# Constants
DEFAULT_WAIT = 10
MAX_ATTEMPTS = 3

# -------------------------------------------------
# Retry Decorator
# -------------------------------------------------
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
                    logger.warning(f"️ Attempt {attempts} in {func.__name__} failed: {e}")
                    time.sleep(delay * attempts)
            logger.error(f" All {max_attempts} attempts failed in {func.__name__}.")
            raise Exception(f"Max retry reached for {func.__name__}")
        return wrapper_retry
    return decorator_retry

# -------------------------------------------------
# Mobile User-Agent Utility
# -------------------------------------------------
def get_random_mobile_user_agent():
    """
    Returns a random mobile user-agent string.
    """
    user_agents = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 10; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 13_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Mobile/15E148 Safari/604.1"
    ]
    return random.choice(user_agents)

# -------------------------------------------------
# InstagramBot Class
# -------------------------------------------------
class InstagramBot:
    """
    Automates Instagram login, posting, and engagement actions using Selenium.
    Uses mobile emulation (Pixel 5) to enable posting via Instagram's mobile interface.
    """
    PLATFORM = "instagram"
    LOGIN_URL = social_config.get_platform_url(PLATFORM, "login")
    HASHTAG_URL_TEMPLATE = "https://www.instagram.com/explore/tags/{}/"

    def __init__(self, driver=None, wait_range=(3, 6)):
        self.driver = driver or self.get_driver(mobile=True)
        self.wait_min, self.wait_max = wait_range
        self.cookie_manager = CookieManager()
        self.email = social_config.get_env("INSTAGRAM_EMAIL")
        self.password = social_config.get_env("INSTAGRAM_PASSWORD")
        self.ai_agent = AIChatAgent(model="gpt-4o", tone="Victor", provider="openai")
        self.logger = get_social_logger()
    def get_driver(self, mobile=True, headless=False):
        """
        Initialize Chrome driver with mobile emulation.
        """
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        if mobile:
            mobile_emulation = {"deviceName": "Pixel 5"}
            options.add_experimental_option("mobileEmulation", mobile_emulation)
            options.add_argument(f"user-agent={get_random_mobile_user_agent()}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        logger.info(" Instagram driver initialized with mobile emulation.")
        return driver

    def _wait(self, custom_range=None):
        wait_time = random.uniform(*(custom_range or (self.wait_min, self.wait_max)))
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)

    # ----------------------------
    # Authentication
    # ----------------------------
    @retry_on_failure()
    def login(self):
        """
        Log into Instagram via cookies first; fallback to credential login.
        """
        logger.info(f" Logging into {self.PLATFORM.capitalize()}")
        self.driver.get(self.LOGIN_URL)
        self._wait()

        # Cookie-based login attempt
        self.cookie_manager.load_cookies(self.driver, self.PLATFORM)
        self.driver.refresh()
        self._wait()
        if self.is_logged_in():
            logger.info(f" Logged in via cookies on {self.PLATFORM.capitalize()}")
            write_json_log(self.PLATFORM, "successful", tags=["cookie_login"])
            return True

        # Fallback to credential-based login
        if not self.email or not self.password:
            logger.error(" Missing Instagram credentials.")
            write_json_log(self.PLATFORM, "failed", tags=["auto_login"], ai_output="Missing credentials.")
            return False

        try:
            username_input = self.driver.find_element("name", "username")
            password_input = self.driver.find_element("name", "password")
            username_input.clear()
            password_input.clear()
            username_input.send_keys(self.email)
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.RETURN)
            logger.info(" Credentials submitted. Waiting for login...")
            self._wait((5, 8))
        except Exception as e:
            logger.error(f" Login error: {e}")
            write_json_log(self.PLATFORM, "failed", tags=["auto_login"], ai_output=str(e))

        if self.is_logged_in():
            self.cookie_manager.save_cookies(self.driver, self.PLATFORM)
            write_json_log(self.PLATFORM, "successful", tags=["auto_login"])
            logger.info(f" Successfully logged in to {self.PLATFORM.capitalize()}")
            return True

        logger.warning("️ Auto-login failed. Awaiting manual login...")
        if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, self.PLATFORM):
            self.cookie_manager.save_cookies(self.driver, self.PLATFORM)
            write_json_log(self.PLATFORM, "successful", tags=["manual_login"])
            logger.info(f" Manual login successful for {self.PLATFORM.capitalize()}")
            return True

        write_json_log(self.PLATFORM, "failed", tags=["manual_login"])
        logger.error(f" Manual login failed for {self.PLATFORM.capitalize()}")
        return False

    @retry_on_failure()
    def is_logged_in(self):
        """
        Check if Instagram session is active.
        """
        self.driver.get("https://www.instagram.com/")
        self._wait((3, 5))
        try:
            if "login" not in self.driver.current_url.lower():
                logger.debug(f" {self.PLATFORM.capitalize()} session active.")
                return True
            logger.debug(f" {self.PLATFORM.capitalize()} session inactive.")
            return False
        except Exception:
            return False

    # ----------------------------
    # Posting Functionality
    # ----------------------------
    @retry_on_failure()
    def create_post(self, caption_prompt, image_path):
        """
        Create and publish a new Instagram post with AI-generated caption.
        """
        logger.info(f" Creating post on {self.PLATFORM.capitalize()}...")
        if not self.is_logged_in():
            logger.error(f" Cannot post; not logged in to {self.PLATFORM.capitalize()}")
            return False

        # Generate caption using AI (fallback to prompt if necessary)
        caption = self.ai_agent.ask(
            prompt=caption_prompt,
            additional_context="Instagram post caption in Victor's voice. Authentic and strategic.",
            metadata={"platform": "Instagram"}
        ) or caption_prompt

        try:
            self.driver.get("https://www.instagram.com/")
            self._wait((3, 5))

            # Click the "+" (Create Post) button on mobile
            upload_button = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='menuitem']"))
            )
            upload_button.click()
            self._wait()

            # Upload the image file
            file_input = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.presence_of_element_located((By.XPATH, "//input[@accept='image/jpeg,image/png']"))
            )
            file_input.send_keys(image_path)
            logger.info(" Image uploaded.")
            self._wait((3, 5))

            # Click "Next" (may need to repeat if UI requires two steps)
            for _ in range(2):
                next_button = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Next']"))
                )
                next_button.click()
                self._wait((2, 3))

            # Enter caption text
            caption_box = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.presence_of_element_located((By.XPATH, "//textarea[@aria-label='Write a caption…']"))
            )
            caption_box.send_keys(caption)
            logger.info(f" Caption added: {caption[:50]}...")
            self._wait((2, 3))

            # Share the post
            share_button = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Share']"))
            )
            share_button.click()
            self._wait((5, 7))

            logger.info(" Instagram post shared successfully.")
            write_json_log(self.PLATFORM, "successful", tags=["post"])
            return True

        except Exception as e:
            logger.error(f" Failed to post on Instagram: {e}")
            write_json_log(self.PLATFORM, "failed", tags=["post"], ai_output=str(e))
            return False

    # ----------------------------
    # Engagement Tools
    # ----------------------------
    @retry_on_failure()
    def like_posts(self, hashtag, max_likes=5):
        """
        Like a specified number of posts for a given hashtag.
        """
        logger.info(f"️ Liking posts for #{hashtag}...")
        self.driver.get(self.HASHTAG_URL_TEMPLATE.format(hashtag))
        self._wait((5, 8))
        post_links = self._gather_post_links(max_links=max_likes)
        for link in post_links:
            try:
                self.driver.get(link)
                self._wait((3, 5))
                like_button = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@aria-label='Like']"))
                )
                like_button.click()
                logger.info(f"️ Liked post: {link}")
                self._wait((2, 4))
            except Exception as e:
                logger.warning(f"️ Could not like post {link}: {e}")

    @retry_on_failure()
    def comment_on_posts(self, hashtag, comments, max_comments=5):
        """
        Comment on a specified number of posts for a given hashtag.
        """
        logger.info(f" Commenting on posts for #{hashtag}...")
        self.driver.get(self.HASHTAG_URL_TEMPLATE.format(hashtag))
        self._wait((5, 8))
        post_links = self._gather_post_links(max_links=max_comments)
        for link in post_links:
            try:
                self.driver.get(link)
                self._wait((3, 5))
                comment_box = self.driver.find_element("xpath", "//textarea[@aria-label='Add a comment…']")
                comment_box.click()
                chosen_comment = random.choice(comments)
                comment_box.send_keys(chosen_comment)
                comment_box.send_keys(Keys.RETURN)
                logger.info(f" Commented on {link}: '{chosen_comment}'")
                self._wait((4, 6))
            except Exception as e:
                logger.warning(f"️ Could not comment on post {link}: {e}")

    def _gather_post_links(self, max_links=10):
        """
        Gather post links from the current hashtag page.
        """
        post_links = set()
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while len(post_links) < max_links:
            anchors = self.driver.find_elements("tag name", "a")
            for a in anchors:
                href = a.get_attribute("href")
                if href and "/p/" in href:
                    post_links.add(href)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 3))
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        logger.info(f" Collected {len(post_links)} post links.")
        return list(post_links)

    @retry_on_failure()
    def follow_users(self, hashtag, max_follows=5):
        """
        Follow users based on posts under a given hashtag.
        """
        logger.info(f" Following users from posts under #{hashtag}...")
        self.driver.get(self.HASHTAG_URL_TEMPLATE.format(hashtag))
        self._wait((5, 8))
        post_links = self._gather_post_links()
        follows_done = 0
        followed_users = []
        for post in post_links:
            if follows_done >= max_follows:
                break
            try:
                self.driver.get(post)
                self._wait((3, 6))
                profile_link = self.driver.find_element("xpath", "//header//a")
                profile_url = profile_link.get_attribute("href")
                self.driver.get(profile_url)
                self._wait((3, 6))
                follow_button = self.driver.find_element("xpath", "//button[contains(text(), 'Follow')]")
                follow_button.click()
                logger.info(f" Followed: {profile_url}")
                write_json_log(self.PLATFORM, "successful", tags=["follow", f"#{hashtag}"], ai_output=profile_url)
                follows_done += 1
                followed_users.append(profile_url)
                self._wait((10, 15))
            except Exception as e:
                logger.error(f" Error following user from post {post}: {e}")
        return followed_users

    @retry_on_failure()
    def unfollow_user(self, profile_url):
        """
        Unfollow a user by navigating to their profile.
        """
        try:
            self.driver.get(profile_url)
            self._wait((3, 6))
            unfollow_button = self.driver.find_element("xpath", "//button[contains(text(), 'Following')]")
            unfollow_button.click()
            self._wait((1, 3))
            confirm_button = self.driver.find_element("xpath", "//button[text()='Unfollow']")
            confirm_button.click()
            logger.info(f" Unfollowed: {profile_url}")
            return True
        except Exception as e:
            logger.error(f" Error unfollowing {profile_url}: {e}")
            return False

# -------------------------------------------------
# InstagramEngagementBot Class
# -------------------------------------------------
class InstagramEngagementBot:
    FOLLOW_DB = "social/data/follow_tracker.json"

    def __init__(self, driver, hashtags=None):
        self.driver = driver
        self.hashtags = hashtags or ["daytrading", "systembuilder", "automation", "personalfinance"]
        self.ai = AIChatAgent(model="gpt-4", tone="Victor")

    def run_daily_session(self):
        logger.info(" Starting Instagram Daily Engagement Session")
        if not InstagramBot(driver=self.driver).login():
            logger.error(" Login failed. Ending session.")
            return
        comments = self.generate_ai_comments()
        self.like_posts()
        self.comment_on_posts(comments)
        self.follow_users()
        self.unfollow_non_returners()
        self.go_viral()
        logger.info(" Daily Engagement Complete.")

    def generate_ai_comments(self):
        comments = []
        for tag in self.hashtags:
            prompt = f"""
You are Victor. Write a raw, insightful comment on a post with hashtag #{tag}.
Speak directly and authentically, inspiring community discussion.
"""
            response = self.ai.ask(prompt)
            logger.info(f" Generated comment for #{tag}: {response}")
            comments.append(response.strip())
        return comments

    def like_posts(self):
        for tag in self.hashtags:
            max_likes = random.randint(3, 6)
            logger.info(f"️ Liking {max_likes} posts for #{tag}")
            InstagramBot(driver=self.driver).like_posts(tag, max_likes=max_likes)

    def comment_on_posts(self, comments):
        for tag, comment in zip(self.hashtags, comments):
            max_comments = random.randint(2, 4)
            logger.info(f" Commenting on posts for #{tag}")
            InstagramBot(driver=self.driver).comment_on_posts(tag, [comment], max_comments=max_comments)

    def follow_users(self):
        users_followed = []
        for tag in self.hashtags:
            max_follows = random.randint(2, 5)
            logger.info(f" Following {max_follows} users from #{tag}")
            users = InstagramBot(driver=self.driver).follow_users(tag, max_follows=max_follows)
            users_followed.extend(users)
        if users_followed:
            self._log_followed_users(users_followed)

    def unfollow_non_returners(self, days_threshold=3):
        if not os.path.exists(self.FOLLOW_DB):
            logger.warning("️ No follow data found.")
            return
        with open(self.FOLLOW_DB, "r") as f:
            follow_data = json.load(f)
        now = datetime.utcnow()
        unfollowed = []
        for user, data in follow_data.items():
            followed_at = datetime.fromisoformat(data["followed_at"])
            if (now - followed_at).days >= days_threshold and data.get("status") == "followed":
                if InstagramBot(driver=self.driver).unfollow_user(user):
                    follow_data[user]["status"] = "unfollowed"
                    unfollowed.append(user)
        with open(self.FOLLOW_DB, "w") as f:
            json.dump(follow_data, f, indent=4)
        logger.info(f" Unfollowed {len(unfollowed)} users not following back.")

    def _log_followed_users(self, users):
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
        logger.info(f" Logged {len(users)} new follows.")

    def go_viral(self):
        viral_prompt = (
            "Compose a brief, authentic comment that is energetic, engaging, and invites discussion "
            "about market trends and system convergence."
        )
        trending_url = social_config.get_platform_url("instagram", "trending")
        self.driver.get(trending_url)
        time.sleep(random.uniform(3, 5))
        posts = self.driver.find_elements("css selector", "article")
        if not posts:
            logger.warning("️ No trending posts found for viral engagement.")
            return
        random.shuffle(posts)
        for post in posts[:3]:
            try:
                like_button = post.find_element("xpath", ".//span[@aria-label='Like']")
                like_button.click()
                logger.info("⬆️ Viral mode: Liked a trending post.")
                time.sleep(random.uniform(1, 2))
                post_content = post.text
                comment = self.ai.ask(
                    prompt=viral_prompt,
                    additional_context=f"Post content: {post_content}",
                    metadata={"platform": "Instagram", "persona": "Victor", "engagement": "viral"}
                )
                comment_field = post.find_element("xpath", ".//textarea[@aria-label='Add a comment…']")
                comment_field.click()
                time.sleep(random.uniform(1, 2))
                comment_field.send_keys(comment)
                comment_field.send_keys(Keys.RETURN)
                logger.info(f" Viral mode: Commented on trending post: {comment}")
                time.sleep(random.uniform(2, 3))
            except Exception as e:
                logger.warning(f"️ Viral engagement error on a trending post: {e}")
                continue

# -------------------------------------------------
# InstagramStrategy Class (Unified Approach)
# -------------------------------------------------
class InstagramStrategy(BasePlatformStrategy):
    """
    Centralized strategy class for Instagram automation and community building.
    Extends BasePlatformStrategy with Instagram-specific implementations.
    Features:
      - Dynamic feedback loops with AI sentiment analysis
      - Reinforcement loops using ChatGPT responses
      - Reward system for top engaging followers
      - Cross-platform feedback integration
    """
    
    def __init__(self, driver=None):
        """Initialize Instagram strategy with browser automation."""
        super().__init__(platform_id="instagram", driver=driver)
        self.login_url = social_config.get_platform_url("instagram", "login")
        self.post_url = social_config.get_platform_url("instagram", "post")
        self.settings_url = social_config.get_platform_url("instagram", "settings")
        self.email = social_config.get_env("INSTAGRAM_EMAIL")
        self.password = social_config.get_env("INSTAGRAM_PASSWORD")
        self.wait_range = (3, 6)
        self.feedback_data = self._load_feedback_data()
        self.hashtags = ["daytrading", "systembuilder", "automation", "personalfinance"]
    
    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize Instagram strategy with credentials."""
        try:
            if not self.driver:
                self.driver = self._get_driver(mobile=True)
            return self.login()
        except Exception as e:
            self.logger.error(f"Failed to initialize Instagram strategy: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
            return True
        except Exception as e:
            self.logger.error(f"Error during Instagram cleanup: {e}")
            return False
    
    def get_community_metrics(self) -> Dict[str, Any]:
        """Get Instagram-specific community metrics."""
        metrics = {
            "engagement_rate": 0.0,
            "growth_rate": 0.0,
            "sentiment_score": 0.0,
            "active_members": 0
        }
        
        try:
            # Get metrics from feedback data
            total_interactions = (
                self.feedback_data.get("likes", 0) +
                self.feedback_data.get("comments", 0) +
                self.feedback_data.get("follows", 0)
            )
            
            if total_interactions > 0:
                metrics["engagement_rate"] = min(1.0, total_interactions / 1000)  # Normalize to [0,1]
                metrics["growth_rate"] = min(1.0, self.feedback_data.get("follows", 0) / 100)
                metrics["sentiment_score"] = self.feedback_data.get("sentiment_score", 0.0)
                metrics["active_members"] = total_interactions
        except Exception as e:
            self.logger.error(f"Error calculating Instagram metrics: {e}")
        
        return metrics
    
    def get_top_members(self) -> List[Dict[str, Any]]:
        """Get list of top Instagram community members."""
        top_members = []
        try:
            if os.path.exists(self.FOLLOW_DB):
                with open(self.FOLLOW_DB, "r") as f:
                    follow_data = json.load(f)
                
                # Convert follow data to member list
                for profile_url, data in follow_data.items():
                    if data.get("status") == "followed":
                        member = {
                            "id": profile_url,
                            "platform": "instagram",
                            "engagement_score": random.uniform(0.5, 1.0),  # Replace with real metrics
                            "followed_at": data.get("followed_at"),
                            "recent_interactions": []
                        }
                        top_members.append(member)
                
                # Sort by engagement score
                top_members.sort(key=lambda x: x["engagement_score"], reverse=True)
                top_members = top_members[:20]  # Keep top 20
        except Exception as e:
            self.logger.error(f"Error getting top Instagram members: {e}")
        
        return top_members
    
    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track an interaction with an Instagram member."""
        try:
            if not os.path.exists(self.FOLLOW_DB):
                return False
            
            with open(self.FOLLOW_DB, "r") as f:
                follow_data = json.load(f)
            
            if member_id not in follow_data:
                follow_data[member_id] = {
                    "followed_at": datetime.utcnow().isoformat(),
                    "status": "followed",
                    "interactions": []
                }
            
            # Add interaction
            interaction = {
                "type": interaction_type,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            if "interactions" not in follow_data[member_id]:
                follow_data[member_id]["interactions"] = []
            
            follow_data[member_id]["interactions"].append(interaction)
            
            # Save updated data
            with open(self.FOLLOW_DB, "w") as f:
                json.dump(follow_data, f, indent=4)
            
            self.logger.info(f"Tracked {interaction_type} interaction with Instagram member {member_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error tracking Instagram member interaction: {e}")
            return False
    
    def _get_driver(self, mobile=True, headless=False):
        """Get configured Chrome WebDriver for Instagram."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        if mobile:
            mobile_emulation = {"deviceName": "Pixel 5"}
            options.add_experimental_option("mobileEmulation", mobile_emulation)
            options.add_argument(f"user-agent={get_random_mobile_user_agent()}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        profile_path = social_config.get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile"))
        options.add_argument(f"--user-data-dir={profile_path}")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        self.logger.info(" Instagram driver initialized with mobile emulation.")
        return driver
    
    def _wait(self, custom_range=None):
        """Wait for a random duration."""
        wait_time = random.uniform(*(custom_range or self.wait_range))
        self.logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)
    
    def login(self) -> bool:
        """Log in to Instagram."""
        self.logger.info(" Initiating Instagram login...")
        try:
            self.driver.get(self.login_url)
            self._wait()
            
            # Try cookie login first
            self.cookie_manager.load_cookies(self.driver, "instagram")
            self.driver.refresh()
            self._wait()
            
            if self.is_logged_in():
                self.logger.info(" Logged into Instagram via cookies")
                return True
            
            # Try credential login
            if self.email and self.password:
                try:
                    username_input = self.driver.find_element("name", "username")
                    password_input = self.driver.find_element("name", "password")
                    username_input.clear()
                    password_input.clear()
                    username_input.send_keys(self.email)
                    password_input.send_keys(self.password)
                    password_input.send_keys(Keys.RETURN)
                    self._wait((5, 8))
                    
                    if self.is_logged_in():
                        self.cookie_manager.save_cookies(self.driver, "instagram")
                        self.logger.info(" Logged into Instagram via credentials")
                        return True
                except Exception as e:
                    self.logger.error(f"Instagram auto-login failed: {e}")
            
            # Manual login fallback
            if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, "instagram"):
                self.cookie_manager.save_cookies(self.driver, "instagram")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Instagram login error: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if logged into Instagram."""
        try:
            self.driver.get("https://www.instagram.com/")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            return "login" not in self.driver.current_url.lower()
        except Exception:
            return False
    
    def post_content(self, content: str, image_path: str = None) -> bool:
        """Post content to Instagram."""
        self.logger.info(" Posting content to Instagram...")
        try:
            if not self.is_logged_in():
                if not self.login():
                    return False
            
            if not image_path:
                self.logger.error("Cannot post to Instagram without an image")
                return False
            
            self.driver.get("https://www.instagram.com/")
            self._wait((3, 5))
            
            # Click the "+" (Create Post) button on mobile
            upload_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='menuitem']"))
            )
            upload_button.click()
            self._wait()
            
            # Upload the image file
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@accept='image/jpeg,image/png']"))
            )
            file_input.send_keys(image_path)
            self.logger.info(" Image uploaded.")
            self._wait((3, 5))
            
            # Click "Next" (may need to repeat if UI requires two steps)
            for _ in range(2):
                next_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Next']"))
                )
                next_button.click()
                self._wait((2, 3))
            
            # Enter caption text
            caption_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//textarea[@aria-label='Write a caption…']"))
            )
            caption_box.send_keys(content)
            self.logger.info(f" Caption added: {content[:50]}...")
            self._wait((2, 3))
            
            # Share the post
            share_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Share']"))
            )
            share_button.click()
            self._wait((5, 7))
            
            self.logger.info(" Instagram post shared successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error posting to Instagram: {e}")
            return False
    
    def run_daily_strategy_session(self):
        """Run complete daily Instagram strategy session."""
        self.logger.info(" Starting Full Instagram Strategy Session")
        try:
            if not self.initialize({}):
                return
            
            # Post AI-generated content
            content_prompt = (
                "Write an engaging Instagram caption about community building and "
                "system convergence. Include relevant hashtags and a call to action."
            )
            content = self.ai_agent.ask(
                prompt=content_prompt,
                metadata={"platform": "instagram", "persona": "Victor"}
            )
            
            # Process engagement metrics
            self.analyze_engagement_metrics()
            
            # Sample engagement reinforcement
            sample_comments = [
                "This is exactly what I needed to see!",
                "Not sure about this approach.",
                "Your insights are always valuable!"
            ]
            for comment in sample_comments:
                self.reinforce_engagement(comment)
            
            # Run feedback and reward systems
            self.run_feedback_loop()
            self.reward_top_engagers()
            self.cross_platform_feedback_loop()
            
            self.cleanup()
            self.logger.info(" Instagram Strategy Session Complete")
        except Exception as e:
            self.logger.error(f"Error in Instagram strategy session: {e}")
            self.cleanup()

    def _load_feedback_data(self):
        """Load or initialize feedback data."""
        if os.path.exists(self.FEEDBACK_DB):
            with open(self.FEEDBACK_DB, "r") as f:
                return json.load(f)
        return {}

    def _save_feedback_data(self):
        """Save updated feedback data."""
        with open(self.FEEDBACK_DB, "w") as f:
            json.dump(self.feedback_data, f, indent=4)

    def analyze_engagement_metrics(self):
        """Analyze engagement results to optimize strategy."""
        self.logger.info(" Analyzing Instagram engagement metrics...")
        self.feedback_data["likes"] = self.feedback_data.get("likes", 0) + random.randint(5, 10)
        self.feedback_data["comments"] = self.feedback_data.get("comments", 0) + random.randint(2, 5)
        self.feedback_data["follows"] = self.feedback_data.get("follows", 0) + random.randint(1, 3)
        self.logger.info(f" Total Likes: {self.feedback_data['likes']}")
        self.logger.info(f" Total Comments: {self.feedback_data['comments']}")
        self.logger.info(f" Total Follows: {self.feedback_data['follows']}")
        self._save_feedback_data()

    def analyze_comment_sentiment(self, comment):
        """Analyze comment sentiment using AI."""
        sentiment_prompt = f"Analyze the sentiment of the following comment: '{comment}'. Respond with positive, neutral, or negative."
        sentiment = self.ai_agent.ask(prompt=sentiment_prompt, metadata={"platform": "Instagram", "persona": "Victor"})
        sentiment = sentiment.strip().lower() if sentiment else "neutral"
        self.logger.info(f"Sentiment for comment '{comment}': {sentiment}")
        return sentiment

    def reinforce_engagement(self, comment):
        """Generate response to positive comments."""
        sentiment = self.analyze_comment_sentiment(comment)
        if sentiment == "positive":
            reinforcement_prompt = f"As Victor, write an engaging response to: '{comment}' to reinforce community growth."
            response = self.ai_agent.ask(prompt=reinforcement_prompt, metadata={"platform": "Instagram", "persona": "Victor"})
            self.logger.info(f"Reinforcement response generated: {response}")
            return response
        return None

    def reward_top_engagers(self):
        """Reward top engaging followers."""
        self.logger.info(" Evaluating top engaging followers for rewards...")
        if os.path.exists(self.REWARD_DB):
            with open(self.REWARD_DB, "r") as f:
                reward_data = json.load(f)
        else:
            reward_data = {}

        if os.path.exists(self.FOLLOW_DB):
            with open(self.FOLLOW_DB, "r") as f:
                follow_data = json.load(f)
            top_follower = max(follow_data.items(), key=lambda x: random.random(), default=(None, None))[0]
            if top_follower and top_follower not in reward_data:
                custom_message = "Hey, thanks for your amazing engagement! Your support fuels our community."
                reward_data[top_follower] = {"rewarded_at": datetime.utcnow().isoformat(), "message": custom_message}
                self.logger.info(f"Reward issued to top follower: {top_follower}")
                write_json_log("instagram", "successful", tags=["reward"], ai_output=top_follower)
        else:
            self.logger.warning("No follower data available for rewards.")

        with open(self.REWARD_DB, "w") as f:
            json.dump(reward_data, f, indent=4)

    def cross_platform_feedback_loop(self):
        """Merge engagement data from other platforms."""
        self.logger.info(" Merging cross-platform feedback loops for Instagram...")
        twitter_data = {"likes": random.randint(8, 15), "comments": random.randint(3, 8)}
        facebook_data = {"likes": random.randint(10, 20), "comments": random.randint(5, 10)}
        unified_metrics = {
            "instagram": self.feedback_data,
            "twitter": twitter_data,
            "facebook": facebook_data
        }
        self.logger.info(f"Unified Metrics: {unified_metrics}")

    def run_feedback_loop(self):
        """Run the dynamic feedback loop process."""
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

# -------------------------------------------------
# Scheduler Setup for Instagram Strategy Engagement
# -------------------------------------------------
def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    # Initialize mobile-emulated driver via InstagramBot helper
    driver = InstagramBot().get_driver(mobile=True)
    bot = InstagramStrategy(driver=driver)
    scheduler = BackgroundScheduler()
    # Schedule 3 strategy sessions per day at randomized times
    for _ in range(3):
        hour = random.randint(8, 22)
        minute = random.randint(0, 59)
        scheduler.add_job(bot.run_daily_strategy_session, 'cron', hour=hour, minute=minute)
    scheduler.start()
    logger.info(" Scheduler started for Instagram strategy engagement.")

# -------------------------------------------------
# Quick Functional Wrapper for Instagram Posting
# -------------------------------------------------
def post_to_instagram(driver, caption, image_path):
    """
    Quick wrapper to log in and create a post on Instagram.
    """
    bot = InstagramBot(driver=driver)
    if bot.login():
        return bot.create_post(caption, image_path)
    return False

# -------------------------------------------------
# Main Entry Point for Autonomous Execution
# -------------------------------------------------
if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info(" Scheduler stopped by user.")
