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
from selenium.common.exceptions import TimeoutException

# Ensure .env variables are loaded
load_dotenv()

# Unified project imports
from utils.cookie_manager import CookieManager
from social.log_writer import get_social_logger, write_json_log
from social.social_config import social_config
from social.AIChatAgent import AIChatAgent
from social.strategies.base_platform_strategy import BasePlatformStrategy
from social.strategies.strategy_config_loader import StrategyConfigLoader

logger = get_social_logger()

# Constants
DEFAULT_WAIT = 10
MAX_ATTEMPTS = 3

# Define constants
PLATFORM = "instagram"
FEEDBACK_DB = "social/data/instagram_feedback_tracker.json"
REWARD_DB = "social/data/instagram_reward_tracker.json"
FOLLOW_DB = "social/data/instagram_follow_tracker.json"

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

    @retry_on_failure()
    def post_content(self, caption: str, image_path: str) -> bool:
         """Post an image with a caption to Instagram using the mobile UI flow."""
         logger.info(f"Attempting to post content to {self.PLATFORM.capitalize()}...")
         if not self._get_driver(): return False
         if not os.path.exists(image_path):
              logger.error(f"Image file not found at: {image_path}. Cannot post.")
              write_json_log(self.PLATFORM, "failed", tags=["post_content", "file_not_found"], ai_output=image_path)
              return False

         if not self.is_logged_in():
              logger.warning("Not logged in. Attempting login before posting.")
              if not self.login():
                   logger.error("Login failed. Cannot post content.")
                   write_json_log(self.PLATFORM, "failed", tags=["post_content", "login_required"], ai_output="Login failed")
                   return False

         base_url = self.config_loader.get_platform_url("base")
         post_url = self.config_loader.get_platform_url("post") # Often same as base for mobile flow
         default_wait = self.config_loader.get_parameter("default_selenium_wait", default=15)

         try:
              # Ensure we are on the main feed page
              current_url = self.driver.current_url
              if base_url not in current_url:
                  logger.debug(f"Navigating to {base_url} before starting post flow.")
                  self.driver.get(base_url)
                  self._wait((3, 5))

              # Dismiss any initial popups (e.g., add to home screen)
              self.handle_common_popups()

              # Click the "+" (Create Post) button - Mobile UI
              # Common XPaths for the create button (may vary based on updates)
              create_button_xpaths = [
                   "//div[@role='menuitem'][@tabindex='0']", # Often the middle item
                   "//span[@aria-label='New post']/ancestor::a",
                   "//a[@aria-label='New post']",
                   "//*[@aria-label='New post']",
                   "//div[@role='button'][contains(.,'New post') or @aria-label='New post']"
              ]
              create_button = self.find_element_sequentially(create_button_xpaths, default_wait)
              if not create_button:
                    logger.error("Could not find the 'Create Post' (+) button.")
                    self.save_screenshot(f"logs/{self.PLATFORM}_create_button_fail.png")
                    write_json_log(self.PLATFORM, "failed", tags=["post_content", "create_button_not_found"], ai_output="Failed to find create button")
                    return False

              create_button.click()
              logger.info("Clicked the 'Create Post' button.")
              self._wait()

              # Locate and upload the image file
              # The input might be hidden, find the right one
              file_input_xpaths = [
                   "//input[@type='file'][@accept='image/jpeg,image/png,image/heic,image/heif,video/mp4,video/quicktime']",
                   "//input[@type='file'][@accept='image/*,video/*']",
                   "//input[@type='file']",
              ]
              file_input = self.find_element_sequentially(file_input_xpaths, default_wait, visible_only=False)
              if not file_input:
                  logger.error("Could not find the file input element for upload.")
                  self.save_screenshot(f"logs/{self.PLATFORM}_file_input_fail.png")
                  write_json_log(self.PLATFORM, "failed", tags=["post_content", "file_input_not_found"], ai_output="Failed to find file input")
                  return False

              # Make the input visible if needed (common trick)
              self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';", file_input)
              self._wait((0.5, 1))
              file_input.send_keys(image_path)
              logger.info(f"Image file selected: {image_path}")
              self._wait((3, 5)) # Allow time for preview to load

              # Click "Next" button (usually appears after upload)
              next_button_xpath = "//button[contains(text(), 'Next')] | //div[@role='button'][contains(text(), 'Next')]"
              try:
                  # Instagram sometimes has two "Next" screens (filter/edit, then caption)
                  for i in range(1, 3): # Try up to two times
                      logger.debug(f"Looking for 'Next' button (attempt {i})...")
                      next_button = WebDriverWait(self.driver, default_wait).until(
                          EC.element_to_be_clickable((By.XPATH, next_button_xpath))
                      )
                      next_button.click()
                      logger.info(f"Clicked 'Next' button ({i}).")
                      self._wait((2, 4))
              except TimeoutException:
                  # If the second 'Next' isn't found, maybe it went straight to caption? Or failed?
                  logger.warning("Could not find 'Next' button after one click, proceeding to caption stage. This might indicate an issue.")
              except Exception as e:
                  logger.error(f"Error clicking 'Next' button: {e}", exc_info=True)
                  self.save_screenshot(f"logs/{self.PLATFORM}_next_button_fail.png")
                  write_json_log(self.PLATFORM, "failed", tags=["post_content", "next_button_error"], ai_output=str(e))
                  return False

              # Enter caption
              caption_area_xpath = "//textarea[@aria-label='Write a caption...'] | //div[@aria-label='Write a caption...']"
              try:
                   caption_box = WebDriverWait(self.driver, default_wait).until(
                        EC.visibility_of_element_located((By.XPATH, caption_area_xpath))
                   )
                   # Using JS click and send_keys can be more reliable sometimes
                   self.driver.execute_script("arguments[0].click();", caption_box)
                   self._wait((0.5, 1))
                   caption_box.clear()
                   caption_box.send_keys(caption)
                   logger.info(f"Caption entered: {caption[:50]}...")
                   self._wait((1, 2))
              except Exception as e:
                   logger.error(f"Error entering caption: {e}", exc_info=True)
                   self.save_screenshot(f"logs/{self.PLATFORM}_caption_fail.png")
                   write_json_log(self.PLATFORM, "failed", tags=["post_content", "caption_error"], ai_output=str(e))
                   return False

              # Click "Share" button
              share_button_xpath = "//button[contains(text(), 'Share')] | //div[@role='button'][contains(text(), 'Share')]"
              try:
                   share_button = WebDriverWait(self.driver, default_wait).until(
                        EC.element_to_be_clickable((By.XPATH, share_button_xpath))
                   )
                   share_button.click()
                   logger.info("Clicked 'Share' button. Waiting for post confirmation...")
                   self._wait((8, 15)) # Wait longer for post processing
              except Exception as e:
                   logger.error(f"Error clicking 'Share' button: {e}", exc_info=True)
                   self.save_screenshot(f"logs/{self.PLATFORM}_share_button_fail.png")
                   write_json_log(self.PLATFORM, "failed", tags=["post_content", "share_button_error"], ai_output=str(e))
                   return False

              # Basic check: Did it redirect or show a success message (hard to verify robustly)?
              # Check if we are back on the main feed or if URL changed significantly.
              final_url = self.driver.current_url
              if "upload" not in final_url and "create" not in final_url:
                   logger.info(f"{self.PLATFORM.capitalize()} post shared successfully (based on URL change). Final URL: {final_url}")
                   write_json_log(self.PLATFORM, "successful", tags=["post_content"], ai_output=f"Caption: {caption[:50]}... Image: {os.path.basename(image_path)}")
                   return True
              else:
                   # It might still be processing, or failed silently
                   logger.warning(f"Post may not have completed successfully. URL still contains 'upload' or 'create': {final_url}")
                   # Check for common failure indicators if possible
                   try:
                        error_msg = self.driver.find_element(By.XPATH, "//*[contains(text(), 'failed') or contains(text(), 'error')]")
                        logger.error(f"Found potential error message on page: {error_msg.text}")
                        write_json_log(self.PLATFORM, "failed", tags=["post_content", "post_failed_message"], ai_output=error_msg.text)
                        return False
                   except:
                        logger.info("No explicit error message found, but confirmation unclear.")
                        write_json_log(self.PLATFORM, "uncertain", tags=["post_content", "confirmation_unclear"], ai_output=f"URL remained: {final_url}")
                        # Consider it successful for now, but log uncertainty
                        return True # Or False depending on desired strictness

         except Exception as e:
              logger.error(f"Unexpected error during Instagram post_content: {e}", exc_info=True)
              self.save_screenshot(f"logs/{self.PLATFORM}_post_content_error.png")
              write_json_log(self.PLATFORM, "failed", tags=["post_content", "unexpected_error"], ai_output=str(e))
              return False

    # Placeholder for find_element_sequentially helper (if not already in Base)
    def find_element_sequentially(self, xpaths: list, wait_time: int, visible_only=True):
        """Tries multiple XPaths sequentially to find an element."""
        last_exception = None
        for xpath in xpaths:
            try:
                if visible_only:
                     element = WebDriverWait(self.driver, wait_time).until(
                         EC.visibility_of_element_located((By.XPATH, xpath))
                     )
                else:
                     element = WebDriverWait(self.driver, wait_time).until(
                         EC.presence_of_element_located((By.XPATH, xpath))
                     )
                logger.debug(f"Element found using XPath: {xpath}")
                return element
            except TimeoutException:
                last_exception = TimeoutException(f"Element not found with XPath: {xpath}")
                continue # Try next xpath
            except Exception as e:
                 last_exception = e
                 logger.warning(f"Error checking XPath {xpath}: {e}")
                 continue
        logger.warning(f"Element not found using any provided XPaths. Last error: {last_exception}")
        return None

    def like_posts_by_hashtag(self, hashtag: str, max_likes: int) -> int:
         # Placeholder - Will be implemented next
