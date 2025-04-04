import os
import random
import time
import json
from datetime import datetime
from abc import ABC, abstractmethod
from functools import wraps
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from utils.cookie_manager import CookieManager
from social.social_config import social_config
from social.log_writer import logger, write_json_log
from social.AIChatAgent import AIChatAgent
from social.strategies.base_platform_strategy import BasePlatformStrategy

# Load environment variables
load_dotenv()

DEFAULT_WAIT = 10
MAX_ATTEMPTS = 3

def retry_on_failure(max_attempts=MAX_ATTEMPTS, delay=2):
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

# -------------------------------
# Base Engagement Bot (Abstract)
# -------------------------------
class BaseEngagementBot(ABC):
    """
    A universal base class for social media engagement bots.
    Provides core community building functions:
      - Login (with cookie & credential fallback)
      - Post content (AI-generated if needed)
      - Like, comment, follow, unfollow, viral engagement, and DM functionalities
      - Daily session orchestration
    """
    def __init__(self, platform, driver=None, wait_range=(3, 6), follow_db_path=None):
        self.platform = platform.lower()
        self.driver = driver or self._get_driver()
        self.wait_min, self.wait_max = wait_range
        self.cookie_manager = CookieManager()
        self.email = social_config.get_env(f"{self.platform.upper()}_EMAIL")
        self.password = social_config.get_env(f"{self.platform.upper()}_PASSWORD")
        self.login_url = social_config.get_platform_url(self.platform, "login")
        self.settings_url = social_config.get_platform_url(self.platform, "settings")
        self.trending_url = social_config.get_platform_url(self.platform, "trending")
        self.ai_agent = AIChatAgent(model="gpt-4o", tone="Victor", provider="openai")
        self.follow_db = follow_db_path or f"social/data/{self.platform}_follow_tracker.json"

    def _get_driver(self):
        options = webdriver.ChromeOptions()
        profile_path = social_config.get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile"))
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument("--start-maximized")
        options.add_argument(f"user-agent={self.get_random_user_agent()}")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logger.info(f"Chrome driver initialized with profile: {profile_path}")
        return driver

    @staticmethod
    def get_random_user_agent():
        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/113.0.0.0 Safari/537.36"
        ])

    def _wait(self, custom_range=None):
        wait_time = random.uniform(*(custom_range or (self.wait_min, self.wait_max)))
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)

    # -- Core Login and Session Management --
    @retry_on_failure()
    def login(self):
        logger.info(f"🌐 Initiating login for {self.platform.capitalize()}.")
        self.driver.get(self.login_url)
        self._wait()
        self.cookie_manager.load_cookies(self.driver, self.platform)
        self.driver.refresh()
        self._wait()
        if self.is_logged_in():
            logger.info(f"✅ Logged into {self.platform.capitalize()} via cookies.")
            write_json_log(self.platform, "success", tags=["cookie_login"])
            return True
        if not self.email or not self.password:
            logger.error(f"❌ Missing credentials for {self.platform.capitalize()}.")
            return False
        self._login_with_credentials()
        if not self.is_logged_in():
            logger.warning(f"⚠️ Auto-login failed for {self.platform.capitalize()}. Awaiting manual login.")
            if not self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, self.platform):
                logger.error(f"❌ Manual login failed for {self.platform.capitalize()}.")
                return False
        self.cookie_manager.save_cookies(self.driver, self.platform)
        logger.info(f"✅ Logged into {self.platform.capitalize()} successfully.")
        return True

    @abstractmethod
    def is_logged_in(self):
        """Platform-specific login check."""
        pass

    @abstractmethod
    def _login_with_credentials(self):
        """Platform-specific auto-login implementation."""
        pass

    # -- Posting Content --
    @abstractmethod
    def post(self, content_prompt):
        """Post content to the platform (can use AI-generated content)."""
        pass

    # -- Engagement Actions --
    def like_posts(self):
        logger.info(f"❤️ Liking posts on {self.platform.capitalize()}...")
        self.driver.get(self.trending_url)
        self._wait((5, 8))
        posts = self._find_posts()
        for post in posts[:random.randint(3, 6)]:
            try:
                like_button = self._find_like_button(post)
                like_button.click()
                logger.info("❤️ Liked a post.")
                self._wait((2, 4))
            except Exception as e:
                logger.warning(f"⚠️ Could not like a post: {e}")

    def comment_on_posts(self, comments):
        logger.info(f"💬 Commenting on posts on {self.platform.capitalize()}...")
        self.driver.get(self.trending_url)
        self._wait((5, 8))
        posts = self._find_posts()
        for post, comment in zip(posts, comments):
            try:
                comment_box = self._find_comment_box(post)
                comment_box.click()
                comment_box.send_keys(comment)
                comment_box.send_keys(Keys.RETURN)
                logger.info(f"💬 Commented: {comment}")
                self._wait((4, 6))
            except Exception as e:
                logger.warning(f"⚠️ Could not comment on a post: {e}")

    def follow_users(self):
        logger.info(f"➕ Following users on {self.platform.capitalize()}...")
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
                logger.info(f"➕ Followed: {profile_url}")
                self._wait((10, 15))
            except Exception as e:
                logger.warning(f"⚠️ Could not follow user: {e}")
        if users_followed:
            self._log_followed_users(users_followed)
        return users_followed

    def unfollow_non_returners(self, days_threshold=3):
        logger.info(f"➖ Unfollowing non-returners on {self.platform.capitalize()}...")
        if not os.path.exists(self.follow_db):
            logger.warning("⚠️ No follow database found.")
            return
        with open(self.follow_db, "r") as f:
            follow_data = json.load(f)
        now = datetime.utcnow()
        unfollowed = []
        for user, data in follow_data.items():
            followed_at = datetime.fromisoformat(data["followed_at"])
            if (now - followed_at).days >= days_threshold and data["status"] == "followed":
                try:
                    self.driver.get(user)
                    self._wait((3, 6))
                    unfollow_button = self._find_unfollow_button()
                    unfollow_button.click()
                    follow_data[user]["status"] = "unfollowed"
                    unfollowed.append(user)
                except Exception as e:
                    logger.warning(f"⚠️ Could not unfollow {user}: {e}")
        with open(self.follow_db, "w") as f:
            json.dump(follow_data, f, indent=4)
        logger.info(f"➖ Unfollowed {len(unfollowed)} users on {self.platform.capitalize()}.")

    def go_viral(self):
        logger.info(f"🔥 Activating viral mode on {self.platform.capitalize()}...")
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
                comment = self.ai_agent.ask(prompt=viral_prompt)
                comment_box = self._find_comment_box(post)
                comment_box.click()
                comment_box.send_keys(comment)
                comment_box.send_keys(Keys.RETURN)
                logger.info(f"💬 Viral comment posted: {comment}")
                self._wait((2, 3))
            except Exception as e:
                logger.warning(f"⚠️ Viral action failed: {e}")

    def _log_followed_users(self, users):
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
        logger.info(f"💾 Logged {len(users)} new follows.")

    # -- Abstract Helpers (platform-specific implementations) --
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

    # -- Daily Session Runner --
    def run_daily_session(self):
        logger.info(f"🚀 Running daily session for {self.platform.capitalize()}...")
        if not self.login():
            logger.error(f"❌ Login failed for {self.platform.capitalize()}. Ending session.")
            return
        hashtags = ["automation", "systemconvergence", "strategicgrowth"]
        comments = []
        for tag in hashtags:
            prompt = f"You are Victor. Write a raw, authentic comment about #{tag}."
            comments.append(self.ai_agent.ask(prompt).strip())
        self.like_posts()
        self.comment_on_posts(comments)
        self.follow_users()
        self.unfollow_non_returners()
        self.go_viral()
        logger.info(f"✅ {self.platform.capitalize()} session complete.")

# -------------------------------------------------
# LinkedIn Engagement Bot Implementation
# -------------------------------------------------
class LinkedInEngagementBot(BaseEngagementBot):
    """
    LinkedIn-specific implementation of BaseEngagementBot.
    Implements abstract methods using LinkedIn's DOM structure.
    """
    def __init__(self, driver=None, wait_range=(3, 6), follow_db_path=None):
        super().__init__(platform="linkedin", driver=driver, wait_range=wait_range, follow_db_path=follow_db_path)
        self.login_url = "https://www.linkedin.com/login"
        self.trending_url = "https://www.linkedin.com/feed/"  # Adjust as needed

    def is_logged_in(self):
        self.driver.get("https://www.linkedin.com/feed/")
        self._wait((3, 5))
        return "feed" in self.driver.current_url.lower()

    def _login_with_credentials(self):
        try:
            email_input = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.visibility_of_element_located((By.ID, "username"))
            )
            password_input = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.visibility_of_element_located((By.ID, "password"))
            )
            email_input.clear()
            email_input.send_keys(self.email)
            self._wait((1, 2))
            password_input.clear()
            password_input.send_keys(self.password)
            self._wait((1, 2))
            password_input.send_keys(Keys.RETURN)
            self._wait((4, 6))
        except Exception as e:
            logger.error(f"❌ Auto-login error on LinkedIn: {e}")
            raise

    def post(self, content_prompt):
        logger.info("🚀 Attempting to post on LinkedIn...")
        if not self.login():
            logger.error("❌ LinkedIn login failed. Cannot post.")
            return {"platform": "linkedin", "status": "failed", "details": "Not logged in"}
        content = self.ai_agent.ask(
            prompt=content_prompt,
            additional_context="Write a raw, insightful LinkedIn post in Victor's voice.",
            metadata={"platform": "LinkedIn", "persona": "Victor"}
        ) or content_prompt
        try:
            self.driver.get("https://www.linkedin.com/feed/")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            start_post_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "share-box-feed-entry__trigger"))
            )
            start_post_btn.click()
            self._wait((2, 4))
            post_text_area = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "ql-editor"))
            )
            post_text_area.click()
            post_text_area.send_keys(content)
            self._wait((2, 3))
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Post')]"))
            )
            post_button.click()
            self._wait((4, 6))
            logger.info("✅ LinkedIn post published successfully.")
            write_json_log("linkedin", "success", message="Post dispatched successfully.")
            return {"platform": "linkedin", "status": "success", "details": "Post published"}
        except Exception as e:
            logger.error(f"🚨 LinkedIn post failed: {e}")
            write_json_log("linkedin", "error", message=f"Post failed: {e}")
            return {"platform": "linkedin", "status": "failed", "details": str(e)}

    # -- Platform-specific helper implementations --
    def _find_posts(self):
        return self.driver.find_elements(By.CSS_SELECTOR, "div.feed-shared-update-v2")

    def _find_like_button(self, post):
        return post.find_element(By.XPATH, ".//button[contains(@aria-label, 'Like')]")

    def _find_comment_box(self, post):
        return post.find_element(By.XPATH, ".//div[contains(@aria-label, 'Write a comment')]")

    def _find_profile_url(self, post):
        try:
            return post.find_element(By.XPATH, ".//a[contains(@href, '/in/')]").get_attribute("href")
        except Exception as e:
            logger.error(f"❌ Could not extract profile URL: {e}")
            raise

    def _find_follow_button(self):
        return self.driver.find_element(By.XPATH, "//button[contains(text(), 'Connect') or contains(text(), 'Follow')]")

    def _find_unfollow_button(self):
        return self.driver.find_element(By.XPATH, "//button[contains(text(), 'Following') or contains(text(), 'Connected')]")

# -------------------------------------------------
# LinkedinStrategy Class (Unified Approach)
# -------------------------------------------------
class LinkedinStrategy(BasePlatformStrategy):
    """
    Centralized strategy class for LinkedIn automation and community building.
    Extends BasePlatformStrategy with LinkedIn-specific implementations.
    Features:
      - Dynamic feedback loops with AI sentiment analysis
      - Reinforcement loops using ChatGPT responses
      - Reward system for top engaging followers
      - Cross-platform feedback integration
    """
    
    def __init__(self, driver=None):
        """Initialize LinkedIn strategy with browser automation."""
        super().__init__(platform_id="linkedin", driver=driver)
        self.login_url = "https://www.linkedin.com/login"
        self.trending_url = "https://www.linkedin.com/feed/"
        self.email = social_config.get_env("LINKEDIN_EMAIL")
        self.password = social_config.get_env("LINKEDIN_PASSWORD")
        self.wait_range = (3, 6)
    
    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize LinkedIn strategy with credentials."""
        try:
            if not self.driver:
                self.driver = self._get_driver()
            return self.login()
        except Exception as e:
            self.logger.error(f"Failed to initialize LinkedIn strategy: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
            return True
        except Exception as e:
            self.logger.error(f"Error during LinkedIn cleanup: {e}")
            return False
    
    def get_community_metrics(self) -> Dict[str, Any]:
        """Get LinkedIn-specific community metrics."""
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
            self.logger.error(f"Error calculating LinkedIn metrics: {e}")
        
        return metrics
    
    def get_top_members(self) -> List[Dict[str, Any]]:
        """Get list of top LinkedIn community members."""
        top_members = []
        try:
            if os.path.exists(self.follow_db):
                with open(self.follow_db, "r") as f:
                    follow_data = json.load(f)
                
                # Convert follow data to member list
                for profile_url, data in follow_data.items():
                    if data.get("status") == "followed":
                        member = {
                            "id": profile_url,
                            "platform": "linkedin",
                            "engagement_score": random.uniform(0.5, 1.0),  # Replace with real metrics
                            "followed_at": data.get("followed_at"),
                            "recent_interactions": []
                        }
                        top_members.append(member)
                
                # Sort by engagement score
                top_members.sort(key=lambda x: x["engagement_score"], reverse=True)
                top_members = top_members[:20]  # Keep top 20
        except Exception as e:
            self.logger.error(f"Error getting top LinkedIn members: {e}")
        
        return top_members
    
    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track an interaction with a LinkedIn member."""
        try:
            if not os.path.exists(self.follow_db):
                return False
            
            with open(self.follow_db, "r") as f:
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
            with open(self.follow_db, "w") as f:
                json.dump(follow_data, f, indent=4)
            
            self.logger.info(f"Tracked {interaction_type} interaction with LinkedIn member {member_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error tracking LinkedIn member interaction: {e}")
            return False
    
    def _get_driver(self):
        """Get configured Chrome WebDriver for LinkedIn."""
        options = webdriver.ChromeOptions()
        profile_path = social_config.get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile"))
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument("--start-maximized")
        options.add_argument(f"user-agent={self.get_random_user_agent()}")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        self.logger.info(f"Chrome driver initialized with profile: {profile_path}")
        return driver
    
    @staticmethod
    def get_random_user_agent():
        """Get random user agent string."""
        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/113.0.0.0 Safari/537.36"
        ])
    
    def _wait(self, custom_range=None):
        """Wait for a random duration."""
        wait_time = random.uniform(*(custom_range or self.wait_range))
        self.logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)
    
    def login(self) -> bool:
        """Log in to LinkedIn."""
        self.logger.info("🌐 Initiating LinkedIn login...")
        try:
            self.driver.get(self.login_url)
            self._wait()
            
            # Try cookie login first
            self.cookie_manager.load_cookies(self.driver, "linkedin")
            self.driver.refresh()
            self._wait()
            
            if self.is_logged_in():
                self.logger.info("✅ Logged into LinkedIn via cookies")
                return True
            
            # Try credential login
            if self.email and self.password:
                try:
                    email_input = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "username"))
                    )
                    password_input = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "password"))
                    )
                    
                    email_input.clear()
                    email_input.send_keys(self.email)
                    self._wait((1, 2))
                    
                    password_input.clear()
                    password_input.send_keys(self.password)
                    self._wait((1, 2))
                    
                    password_input.send_keys(Keys.RETURN)
                    self._wait((4, 6))
                    
                    if self.is_logged_in():
                        self.cookie_manager.save_cookies(self.driver, "linkedin")
                        self.logger.info("✅ Logged into LinkedIn via credentials")
                        return True
                except Exception as e:
                    self.logger.error(f"LinkedIn auto-login failed: {e}")
            
            # Manual login fallback
            if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, "linkedin"):
                self.cookie_manager.save_cookies(self.driver, "linkedin")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"LinkedIn login error: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if logged into LinkedIn."""
        try:
            self.driver.get("https://www.linkedin.com/feed/")
            self._wait((3, 5))
            return "feed" in self.driver.current_url.lower()
        except Exception:
            return False
    
    def post_content(self, content: str) -> bool:
        """Post content to LinkedIn."""
        self.logger.info("🚀 Posting content to LinkedIn...")
        try:
            if not self.is_logged_in():
                if not self.login():
                    return False
            
            self.driver.get("https://www.linkedin.com/feed/")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            
            start_post_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "share-box-feed-entry__trigger"))
            )
            start_post_btn.click()
            self._wait((2, 4))
            
            post_text_area = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "ql-editor"))
            )
            post_text_area.click()
            post_text_area.send_keys(content)
            self._wait((2, 3))
            
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Post')]"))
            )
            post_button.click()
            self._wait((4, 6))
            
            self.logger.info("✅ LinkedIn post published successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error posting to LinkedIn: {e}")
            return False
    
    def run_daily_strategy_session(self):
        """Run complete daily LinkedIn strategy session."""
        self.logger.info("🚀 Starting Full LinkedIn Strategy Session")
        try:
            if not self.initialize({}):
                return
            
            # Post AI-generated content
            content_prompt = (
                "Write an insightful LinkedIn post about system convergence and "
                "community building in the digital age. Include relevant hashtags."
            )
            content = self.ai_agent.ask(
                prompt=content_prompt,
                metadata={"platform": "linkedin", "persona": "Victor"}
            )
            if content:
                self.post_content(content)
            
            # Process engagement metrics
            self.analyze_engagement_metrics()
            
            # Sample engagement reinforcement
            sample_comments = [
                "This is exactly what I needed to hear!",
                "Not sure I agree with this take.",
                "Your insights are always spot on!"
            ]
            for comment in sample_comments:
                self.reinforce_engagement(comment)
            
            # Run feedback and reward systems
            self.run_feedback_loop()
            self.reward_top_engagers()
            self.cross_platform_feedback_loop()
            
            self.cleanup()
            self.logger.info("✅ LinkedIn Strategy Session Complete")
        except Exception as e:
            self.logger.error(f"Error in LinkedIn strategy session: {e}")
            self.cleanup()

# Start the LinkedIn strategy if run directly
if __name__ == "__main__":
    strategy = LinkedinStrategy()
    strategy.run_daily_strategy_session()
