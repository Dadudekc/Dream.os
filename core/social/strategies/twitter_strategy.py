import time
import json
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, ElementClickInterceptedException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.cookie_manager import CookieManager
from social.social_config import social_config
from social.log_writer import write_json_log, get_social_logger
from social.AIChatAgent import AIChatAgent
from social.strategies.base_platform_strategy import BasePlatformStrategy
from .strategy_config_loader import StrategyConfigLoader

logger = get_social_logger()

# Define constants
PLATFORM = "twitter"
FEEDBACK_DB = "social/data/twitter_feedback_tracker.json"
REWARD_DB = "social/data/twitter_reward_tracker.json"
FOLLOW_DB = "social/data/twitter_follow_tracker.json"

class TwitterStrategy(BasePlatformStrategy):
    """
    Centralized strategy class for Twitter automation and community building,
    leveraging StrategyConfigLoader.
    Extends BasePlatformStrategy with Twitter-specific implementations.
    Features:
      - Posting tweets and threads
      - Community engagement (like, comment, follow/unfollow)
      - Dynamic feedback loops with AI sentiment analysis
      - Reinforcement loops
      - Reward system for top engagers
      - Cross-platform feedback integration (stubbed)
    """
    PLATFORM = PLATFORM

    def __init__(self, driver=None):
        """Initialize Twitter strategy using StrategyConfigLoader."""
        super().__init__(platform_id=self.PLATFORM, driver=driver)
        self.config_loader = StrategyConfigLoader(platform=self.PLATFORM)
        self.ai_agent = AIChatAgent(
            model=self.config_loader.get_parameter("ai_model", "gpt-4o"),
            tone=self.config_loader.get_parameter("ai_comment_tone", "Victor_Twitter"), # Twitter specific tone?
            provider=self.config_loader.get_parameter("ai_provider", "openai")
        )
        self.cookie_manager = CookieManager()
        self.feedback_data = self._load_feedback_data() # Load feedback data using method
        # Credentials handled by initialize
        self.email = None # Twitter often uses email/username/phone
        self.username = None # Store if needed for login/checks
        self.password = None
        # Load relevant paths from config
        self.follow_db_path = self.config_loader.get_data_path(FOLLOW_DB)
        self.feedback_db_path = self.config_loader.get_data_path(FEEDBACK_DB)
        self.reward_db_path = self.config_loader.get_data_path(REWARD_DB)

    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize Twitter strategy with credentials."""
        logger.info(f"Initializing {self.PLATFORM.capitalize()}Strategy...")
        # Adapt based on expected keys (e.g., 'email', 'username', 'phone')
        self.email = credentials.get("email")
        self.username = credentials.get("username")
        self.password = credentials.get("password")
        if not (self.email or self.username) or not self.password:
            logger.error(f"{self.PLATFORM.capitalize()} credentials (email/username, password) not provided.")
            return False
        try:
            if not self.driver:
                logger.info("No driver provided, initializing default driver.")
                self.driver = self._get_driver()
            if not self.driver:
                 logger.error(f"Driver initialization failed for {self.PLATFORM}. Cannot initialize.")
                 return False
            return self.login() # Attempt login after initialization
        except Exception as e:
            logger.error(f"Failed to initialize {self.PLATFORM.capitalize()} strategy: {e}", exc_info=True)
            return False

    def cleanup(self) -> bool:
        """Clean up resources (driver)."""
        logger.info(f"Cleaning up {self.PLATFORM.capitalize()}Strategy resources...")
        return super().cleanup()

    def _get_driver(self):
         """Gets or initializes the Selenium WebDriver using BasePlatformStrategy config."""
         if not self.driver:
              logger.info(f"{self.PLATFORM.capitalize()}Strategy: No driver found, using BasePlatformStrategy._get_driver().")
              headless_pref = self.config_loader.get_parameter("headless_browser", default=False)
              self.driver = super()._get_driver(headless=headless_pref)
         return self.driver

    def _wait(self, custom_range=None):
        """Waits for a random duration within the configured range."""
        wait_range = custom_range or self.config_loader.get_parameter("wait_range_seconds", default=(2, 5))
        wait_time = random.uniform(*wait_range)
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)

    def login(self) -> bool:
        """Logs into Twitter using configured credentials and cookies."""
        logger.info(f"Initiating login process for {self.PLATFORM}.")
        if not self._get_driver(): # Ensure driver is available
            logger.error("Cannot login: WebDriver is not initialized.")
            return False
        # Use self.email or self.username based on what's provided
        login_identifier = self.username or self.email
        if not login_identifier or not self.password:
            logger.error("Cannot login: Email/Username or password not set.")
            return False

        login_url = self.config_loader.get_platform_url("login")
        base_url = self.config_loader.get_platform_url("base") # For login check
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=15)

        try:
            self.driver.get(login_url)
            self._wait((3, 5))
            self.cookie_manager.load_cookies(self.driver, self.PLATFORM)
            self.driver.refresh()
            self._wait((3, 5))

            if self.is_logged_in():
                logger.info(f"Logged into {self.PLATFORM} via cookies or existing session.")
                write_json_log(self.PLATFORM, "successful", tags=["cookie_login"])
                return True

            logger.info("Cookie/Session login failed. Attempting credential login.")
            self.driver.get(login_url) # Go back to login page if needed
            self._wait((2, 4))

            # --- Twitter Login Flow ---
            # Step 1: Enter username/email/phone
            try:
                # Combined selector for the first input field
                identifier_input_xpath = "//input[@autocomplete='username' or @name='text' or contains(@aria-label, 'Phone, email, or username')]"
                identifier_input = WebDriverWait(self.driver, default_wait).until(
                    EC.visibility_of_element_located((By.XPATH, identifier_input_xpath))
                )
                identifier_input.send_keys(login_identifier)
                identifier_input.send_keys(Keys.RETURN) # Or find 'Next' button
                logger.info(f"Entered identifier: {login_identifier}")
                self._wait((2, 4))
            except TimeoutException:
                logger.error("Could not find the username/email input field.")
                # self.driver.save_screenshot(f"logs/twitter_login_fail_step1_{datetime.now():%Y%m%d_%H%M%S}.png")
                return False

            # Step 2: Handle potential "Enter your phone number or username" prompt (if email was used)
            # This step might appear if Twitter needs to disambiguate or verify
            try:
                 # Look for a field specifically asking for username if the initial identifier might have been email
                 username_prompt_input_xpath = "//input[@name='text' and contains(@aria-label, 'username')]"
                 username_prompt_input = WebDriverWait(self.driver, 5).until( # Shorter wait, may not appear
                      EC.visibility_of_element_located((By.XPATH, username_prompt_input_xpath))
                 )
                 if self.username: # Only fill if we have a separate username stored
                      username_prompt_input.send_keys(self.username)
                      username_prompt_input.send_keys(Keys.RETURN)
                      logger.info(f"Entered username ({self.username}) at secondary prompt.")
                      self._wait((2, 4))
                 else:
                      logger.warning("Twitter asked for username, but none specifically configured.")
                      # Might need to handle this case differently, maybe abort?
                      return False # Abort if username required but not available
            except TimeoutException:
                 logger.debug("Secondary username prompt not detected.")
                 pass # Input field didn't appear, continue

            # Step 3: Enter password
            try:
                password_input_xpath = "//input[@autocomplete='current-password' or @name='password']"
                password_input = WebDriverWait(self.driver, default_wait).until(
                    EC.visibility_of_element_located((By.XPATH, password_input_xpath))
                )
                password_input.send_keys(self.password)
                password_input.send_keys(Keys.RETURN) # Or find 'Log in' button
                logger.info("Entered password and submitted.")
                self._wait((4, 7)) # Wait longer for login processing
            except TimeoutException:
                logger.error("Could not find the password input field.")
                # self.driver.save_screenshot(f"logs/twitter_login_fail_step3_{datetime.now():%Y%m%d_%H%M%S}.png")
                return False

            # Step 4: Verify Login
            if self.is_logged_in():
                logger.info(f"Logged in successfully to {self.PLATFORM} using credentials.")
                self.cookie_manager.save_cookies(self.driver, self.PLATFORM)
                write_json_log(self.PLATFORM, "successful", tags=["credential_login"])
                return True
            else:
                logger.error(f"Credential login failed for {self.PLATFORM}. Check for verification steps or incorrect credentials.")
                screenshot_path = f"logs/twitter_login_verify_fail_{datetime.now():%Y%m%d_%H%M%S}.png"
                try:
                     os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                     self.driver.save_screenshot(screenshot_path)
                     logger.info(f"Saved screenshot of login verify failure to: {screenshot_path}")
                except Exception as ss_err:
                     logger.error(f"Failed to save screenshot: {ss_err}")
                write_json_log(self.PLATFORM, "failed", tags=["credential_login"], ai_output="Login verification failed after credential submission.")
                return False

        except Exception as e:
            logger.error(f"Error during {self.PLATFORM} login process: {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["login_error"], ai_output=str(e))
            return False

    def is_logged_in(self) -> bool:
        """Checks if the user is logged into Twitter more reliably."""
        if not self.driver:
            return False
        base_url = self.config_loader.get_platform_url("base")
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=5) # Shorter wait for check
        try:
            current_url = self.driver.current_url
            # If on a known logged-out or interstitial page, fail fast
            if "/login" in current_url or "/i/flow/login" in current_url or "/logout" in current_url:
                 logger.debug(f"{self.PLATFORM} login check failed (on known logged-out URL: {current_url}).")
                 return False

            # Navigate to home/base URL if not recognizably logged in
            if "twitter.com" not in current_url or "/home" not in current_url:
                 logger.debug(f"Current URL {current_url} not '/home', navigating to base URL for login check.")
                 self.driver.get(base_url + "/home") # Go directly to home feed
                 self._wait((2,4))
                 current_url = self.driver.current_url
                 if "/login" in current_url or "/i/flow/login" in current_url: # Check again after navigation
                      logger.debug(f"{self.PLATFORM} login check failed (redirected to login from /home).")
                      return False

            # Look for elements indicating a logged-in state on the home feed
            # Combine multiple selectors for robustness
            logged_in_indicator_xpath = (
                "//a[@data-testid='AppTabBar_Home_Link' and @aria-selected='true'] | " # Home tab selected
                "//div[@data-testid='SideNav_AccountSwitcher_Button'] | " # Account switcher button
                "//aside[@aria-label='Primary navigation']//a[@aria-label='Profile'] | " # Profile link in nav
                "//div[@data-testid='primaryColumn']//div[@data-testid='tweetTextarea_0']" # Tweet composer box
            )
            WebDriverWait(self.driver, default_wait).until(
                EC.presence_of_element_located((By.XPATH, logged_in_indicator_xpath))
            )
            logger.debug(f"{self.PLATFORM} login confirmed via UI indicator. Current URL: {self.driver.current_url}")
            return True
        except TimeoutException:
            screenshot_path = f"logs/twitter_login_check_fail_{datetime.now():%Y%m%d_%H%M%S}.png"
            try:
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Saved screenshot of login check failure to: {screenshot_path}")
            except Exception as ss_err:
                logger.error(f"Failed to save screenshot: {ss_err}")
            logger.debug(f"{self.PLATFORM} login check failed (UI indicator not found). Current URL: {self.driver.current_url}")
            return False
        except Exception as e:
            logger.warning(f"Error during {self.PLATFORM} login check: {e}", exc_info=True)
            return False

    def post_tweet(self, text: str) -> bool:
        """Posts a single tweet."""
        logger.info(f"Attempting to post tweet: {text[:50]}...")
        if not self.is_logged_in():
            logger.warning("Not logged in. Attempting login before posting tweet...")
            if not self.login():
                write_json_log(self.PLATFORM, "failed", tags=["post_tweet", "login_required"])
                return False

        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=10)
        try:
            # Ensure on home page or similar where composer is available
            if "/home" not in self.driver.current_url:
                 self.driver.get(self.config_loader.get_platform_url("base") + "/home")
                 self._wait((2,4))

            # Use a robust selector for the tweet input area
            tweet_input_xpath = "//div[@data-testid='tweetTextarea_0']//div[@contenteditable='true']"
            tweet_input = WebDriverWait(self.driver, default_wait).until(
                EC.element_to_be_clickable((By.XPATH, tweet_input_xpath))
            )
            tweet_input.click() # Focus
            tweet_input.send_keys(text)
            self._wait((1, 2))

            # Use a robust selector for the post button
            post_button_xpath = "//button[@data-testid='tweetButtonInline' or @data-testid='tweetButton']"
            post_button = WebDriverWait(self.driver, default_wait).until(
                EC.element_to_be_clickable((By.XPATH, post_button_xpath))
            )
             # Check if button is enabled (sometimes disabled briefly or if text is empty)
            if not post_button.is_enabled():
                 logger.warning("Post button is not enabled. Waiting briefly...")
                 self._wait((1,2)) # Short extra wait
                 post_button = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, post_button_xpath))) # Re-fetch

            post_button.click()
            self._wait((3, 6)) # Wait for tweet submission

            # Add confirmation check (e.g., look for "Your Tweet was sent" message or check profile)
            logger.info("Tweet posted successfully.")
            write_json_log(self.PLATFORM, "successful", tags=["post_tweet"], details=text[:50])
            # Track interaction
            # self.track_member_interaction(self.username or 'self', "tweet_posted", {"text": text})
            return True

        except (NoSuchElementException, TimeoutException, ElementClickInterceptedException) as e:
            logger.error(f"Error posting tweet: {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["post_tweet", "error"], ai_output=str(e))
            # self.driver.save_screenshot(f"logs/twitter_post_fail_{datetime.now():%Y%m%d_%H%M%S}.png")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during tweet posting: {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["post_tweet", "unexpected_error"], ai_output=str(e))
            return False

    def post_thread(self, texts: List[str]) -> bool:
        """Posts a sequence of tweets as a thread."""
        if not texts:
            logger.warning("Cannot post empty thread.")
            return False
        logger.info(f"Attempting to post thread with {len(texts)} parts...")

        if not self.is_logged_in():
            logger.warning("Not logged in. Attempting login before posting thread...")
            if not self.login():
                write_json_log(self.PLATFORM, "failed", tags=["post_thread", "login_required"])
                return False

        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=10)
        try:
            # Ensure on home page or similar
            if "/home" not in self.driver.current_url:
                 self.driver.get(self.config_loader.get_platform_url("base") + "/home")
                 self._wait((2,4))

            # Start first tweet
            tweet_input_xpath = "//div[@data-testid='tweetTextarea_0']//div[@contenteditable='true']"
            tweet_input = WebDriverWait(self.driver, default_wait).until(
                EC.element_to_be_clickable((By.XPATH, tweet_input_xpath))
            )
            tweet_input.click()
            tweet_input.send_keys(texts[0])
            self._wait((1, 2))

            # Add subsequent tweets
            for i, text in enumerate(texts[1:], start=1):
                # Find and click the "Add tweet" button
                add_tweet_button_xpath = "//button[@aria-label='Add Tweet' or @data-testid='addButton']" # Adjust selectors
                add_tweet_button = WebDriverWait(self.driver, default_wait).until(
                    EC.element_to_be_clickable((By.XPATH, add_tweet_button_xpath))
                )
                add_tweet_button.click()
                self._wait((0.5, 1.5))

                # Find the input for the next tweet in the thread
                next_tweet_input_xpath = f"//div[@data-testid='tweetTextarea_{i}']//div[@contenteditable='true']"
                next_tweet_input = WebDriverWait(self.driver, default_wait).until(
                    EC.element_to_be_clickable((By.XPATH, next_tweet_input_xpath))
                )
                next_tweet_input.click()
                next_tweet_input.send_keys(text)
                logger.debug(f"Added part {i+1} to thread.")
                self._wait((1, 2))

            # Find and click the "Post all" / "Tweet all" button
            post_all_button_xpath = "//button[@data-testid='tweetButton']//span[contains(text(), 'Post all') or contains(text(), 'Tweet all')]/ancestor::button[@data-testid='tweetButton']"
            post_all_button = WebDriverWait(self.driver, default_wait).until(
                EC.element_to_be_clickable((By.XPATH, post_all_button_xpath))
            )
            post_all_button.click()
            logger.info("Clicked 'Post all' button.")
            self._wait((5, 10)) # Longer wait for thread submission

            # Add confirmation check
            logger.info("Thread posted successfully.")
            write_json_log(self.PLATFORM, "successful", tags=["post_thread"], details=f"{len(texts)} parts, start: {texts[0][:30]}...")
            # self.track_member_interaction(self.username or 'self', "thread_posted", {"parts": len(texts), "text_start": texts[0][:50]})
            return True

        except (NoSuchElementException, TimeoutException, ElementClickInterceptedException) as e:
            logger.error(f"Error posting thread: {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["post_thread", "error"], ai_output=str(e))
            # self.driver.save_screenshot(f"logs/twitter_thread_fail_{datetime.now():%Y%m%d_%H%M%S}.png")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during thread posting: {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["post_thread", "unexpected_error"], ai_output=str(e))
            return False

    def engage_community(self, query: str, num_to_engage: int, like: bool = True, comment: bool = True, follow: bool = False):
        """Engages with tweets based on a search query."""
        logger.info(f"Starting community engagement for query: '{query}', engaging up to {num_to_engage} posts.")
        if not self.is_logged_in():
            logger.warning("Not logged in. Attempting login before engaging...")
            if not self.login():
                write_json_log(self.PLATFORM, "failed", tags=["engage", "login_required"])
                return

        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=10)
        search_url = f"{self.config_loader.get_platform_url('base')}/search?q={query}&src=typed_query&f=live" # Use base URL + search path

        try:
            self.driver.get(search_url)
            self._wait((4, 7))

            engaged_count = 0
            # Use a robust selector for tweet articles
            tweet_article_xpath = "//article[@data-testid='tweet']"
            # Wait for at least one tweet to appear
            WebDriverWait(self.driver, default_wait).until(
                 EC.presence_of_element_located((By.XPATH, tweet_article_xpath))
            )
            articles = self.driver.find_elements(By.XPATH, tweet_article_xpath)
            logger.info(f"Found {len(articles)} potential tweets on search results page for query '{query}'.")

            # Get AI tone from config for comments
            ai_tone = self.config_loader.get_parameter("ai_comment_tone", default="Victor_Twitter")
            self.ai_agent.tone = ai_tone

            for article in articles:
                if engaged_count >= num_to_engage:
                    logger.info(f"Engagement limit ({num_to_engage}) reached.")
                    break
                try:
                    # Scroll tweet into view
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center');", article)
                    self._wait((0.5, 1.0))

                    # Extract user handle and tweet text if needed for logging/AI prompt
                    user_handle = "unknown_user"
                    tweet_text = ""
                    try:
                         user_handle_element = article.find_element(By.XPATH, ".//div[@data-testid='User-Name']//span[contains(text(), '@')]")
                         user_handle = user_handle_element.text.strip()
                    except NoSuchElementException:
                         logger.debug("Could not extract user handle from tweet.")
                    try:
                         tweet_text_element = article.find_element(By.XPATH, ".//div[@data-testid='tweetText']")
                         tweet_text = tweet_text_element.text
                    except NoSuchElementException:
                         logger.debug("Could not extract tweet text.")

                    logger.debug(f"Processing tweet from {user_handle}: {tweet_text[:60]}...")

                    # --- Like Action ---
                    if like:
                        try:
                            # Robust selector for like button (might be liked already)
                            like_button_xpath = ".//div[@data-testid='like' or @data-testid='unlike']"
                            like_button = WebDriverWait(article, 5).until( # Wait within the article context
                                EC.element_to_be_clickable((By.XPATH, like_button_xpath))
                            )
                            # Check if already liked (optional, based on data-testid)
                            if like_button.get_attribute("data-testid") == "like":
                                 like_button.click()
                                 logger.info(f"Liked tweet from {user_handle}.")
                                 self.track_member_interaction(user_handle, "liked_tweet", {"tweet_text_preview": tweet_text[:50]})
                                 self._wait((1, 3))
                            else:
                                 logger.debug(f"Tweet from {user_handle} already liked.")
                        except Exception as like_e:
                            logger.warning(f"Could not like tweet from {user_handle}: {like_e}")

                    # --- Comment Action ---
                    if comment and tweet_text:
                        try:
                            comment_prompt = f"Generate a brief, engaging, and relevant reply to this tweet (max 270 chars):\n---\n{tweet_text}\n---\nReply:\""
                            ai_comment = self.ai_agent.ask(comment_prompt, metadata={"platform": self.PLATFORM, "task": "engage_comment"})

                            if ai_comment:
                                # Find and click reply button within the tweet article
                                reply_button_xpath = ".//div[@data-testid='reply']"
                                reply_button = WebDriverWait(article, 5).until(
                                    EC.element_to_be_clickable((By.XPATH, reply_button_xpath))
                                )
                                reply_button.click()
                                logger.debug("Clicked reply button.")
                                self._wait((1.5, 3))

                                # The reply composer appears as a modal or inline area
                                # Use a general selector for the reply text area
                                comment_box_xpath = "//div[@data-testid='tweetTextarea_0']//div[@contenteditable='true']"
                                comment_box = WebDriverWait(self.driver, default_wait).until(
                                    EC.visibility_of_element_located((By.XPATH, comment_box_xpath))
                                )
                                comment_box.click()
                                comment_box.send_keys(ai_comment)
                                self._wait((1, 2))

                                # Find and click the final "Reply" button in the composer
                                tweet_reply_button_xpath = "//button[@data-testid='tweetButton']//span[text()='Reply']/ancestor::button[@data-testid='tweetButton']"
                                tweet_reply_button = WebDriverWait(self.driver, default_wait).until(
                                    EC.element_to_be_clickable((By.XPATH, tweet_reply_button_xpath))
                                )
                                tweet_reply_button.click()
                                logger.info(f"Commented on tweet from {user_handle}: {ai_comment[:30]}...")
                                self.track_member_interaction(user_handle, "commented_on_tweet", {"comment_text": ai_comment, "original_tweet": tweet_text[:50]})
                                self._wait((3, 5))
                            else:
                                logger.warning(f"AI agent did not generate a comment for tweet from {user_handle}.")
                        except Exception as comment_e:
                            logger.warning(f"Could not comment on tweet from {user_handle}: {comment_e}", exc_info=True)
                            # Close the composer if it's stuck open?
                            # try: self.driver.find_element(By.XPATH, "//div[@aria-label='Close']").click()
                            # except: pass

                    # --- Follow Action ---
                    if follow:
                        try:
                            # Follow button selector within the tweet article
                            follow_button_xpath = ".//div[@data-testid='placementTracking']//span[contains(text(), 'Follow')]/ancestor::div[@role='button'] | .//div[@data-testid='userFollowButton']"
                            follow_button = WebDriverWait(article, 5).until(
                                 EC.element_to_be_clickable((By.XPATH, follow_button_xpath))
                                 )
                            # Check if already following (button text might be 'Following') - needs more robust check
                            follow_button.click()
                            logger.info(f"Followed user: {user_handle}.")
                            self._log_follow(user_handle) # Log the follow action
                            self._wait((1, 3))
                        except (TimeoutException, NoSuchElementException):
                             logger.debug(f"Follow button not found or user {user_handle} already followed.")
                        except Exception as follow_e:
                            logger.warning(f"Could not follow user {user_handle} from tweet: {follow_e}")

                    engaged_count += 1
                    logger.info(f"Engagement {engaged_count}/{num_to_engage} processed for tweet by {user_handle}.")
                    # Add a small wait between processing tweets
                    self._wait((1,2))

                except Exception as engage_err:
                    logger.warning(f"Error processing a specific tweet: {engage_err}", exc_info=True)
                    continue # Move to the next tweet

            logger.info(f"Community engagement phase complete for query '{query}'. Engaged with {engaged_count} tweets.")

        except Exception as e:
            logger.error(f"An error occurred during community engagement for query '{query}': {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["engage", "error"], ai_output=str(e))

    def _log_follow(self, username: str):
        """Logs a follow action to the tracking file."""
        logger.debug(f"Logging follow action for user: {username}")
        try:
            if os.path.exists(self.follow_db_path):
                with open(self.follow_db_path, "r", encoding='utf-8') as f:
                    follow_data = json.load(f)
            else:
                follow_data = {}

            now_iso = datetime.utcnow().isoformat()
            if username not in follow_data or follow_data[username].get("status") != "followed":
                follow_data[username] = {
                    "followed_at": now_iso,
                    "status": "followed",
                    "source": "engagement", # Add source if needed
                    "interactions": [] # Initialize interactions list
                }
                logger.info(f"Logged new follow for user: {username}")
            else:
                # Update last seen or status if already present but unfollowed?
                follow_data[username]["status"] = "followed" # Ensure status is correct
                follow_data[username]["last_followed_at"] = now_iso # Add/update last follow time
                logger.debug(f"User {username} already in tracker, updated status/timestamp.")

            # Add interaction record for the follow itself
            interaction = {
                 "type": "followed_user",
                 "timestamp": now_iso,
                 "metadata": {}
            }
            follow_data[username].setdefault("interactions", []).append(interaction)

            # Save updated data
            os.makedirs(os.path.dirname(self.follow_db_path), exist_ok=True)
            with open(self.follow_db_path, "w", encoding='utf-8') as f:
                json.dump(follow_data, f, indent=4, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error logging follow for {username}: {e}", exc_info=True)
        # Also call the generic interaction tracker
        self.track_member_interaction(username, "followed_user", {"source": "engagement"})

    def unfollow_non_returners(self):
        """Unfollows users who haven't followed back after a configured threshold."""
        logger.info("Starting unfollow process...")
        unfollow_enabled = self.config_loader.get_parameter("enable_unfollow", default=True)
        if not unfollow_enabled:
             logger.info("Unfollow feature is disabled in configuration.")
             return

        if not self.is_logged_in():
            logger.warning("Not logged in. Attempting login before unfollowing...")
            if not self.login():
                write_json_log(self.PLATFORM, "failed", tags=["unfollow", "login_required"])
                return

        unfollow_days = self.config_loader.get_parameter("unfollow_threshold_days", default=7)
        max_unfollows = self.config_loader.get_parameter("max_unfollows_per_run", default=15)
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=10)

        logger.info(f"Checking for users to unfollow (followed > {unfollow_days} days ago, limit {max_unfollows} per run)...")
        if not os.path.exists(self.follow_db_path):
            logger.info("Follow tracker file not found. No users to check for unfollowing.")
            return

        try:
            with open(self.follow_db_path, "r", encoding='utf-8') as f:
                follow_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading follow tracker file {self.follow_db_path}: {e}")
            return

        now = datetime.utcnow()
        users_to_unfollow = []
        for username, data in follow_data.items():
            if data.get("status") == "followed":
                try:
                    followed_at_str = data.get("followed_at") or data.get("last_followed_at") # Check both keys
                    if not followed_at_str: continue
                    # Handle potential timezone info ('Z' or +00:00)
                    if followed_at_str.endswith('Z'):
                         followed_at = datetime.fromisoformat(followed_at_str[:-1] + '+00:00')
                    else:
                         followed_at = datetime.fromisoformat(followed_at_str)

                    # Ensure followed_at is timezone-aware (UTC) for comparison
                    if followed_at.tzinfo is None:
                         followed_at = followed_at.replace(tzinfo=timezone.utc)
                    now_aware = now.replace(tzinfo=timezone.utc)

                    # TODO: Implement check if user followed back (requires scraping follower list - complex!)
                    # For now, just unfollow based on time threshold
                    followed_back = False # Assume not followed back for now

                    if not followed_back and (now_aware - followed_at).days >= unfollow_days:
                        users_to_unfollow.append(username)
                except (ValueError, KeyError, TypeError) as date_err:
                    logger.warning(f"Could not parse followed_at date for {username}: {date_err}")
                except Exception as parse_err:
                     logger.error(f"Error processing follow data for {username}: {parse_err}")

        if not users_to_unfollow:
            logger.info("No users met the criteria for unfollowing in this run.")
            return

        logger.info(f"Identified {len(users_to_unfollow)} users to potentially unfollow. Processing up to {max_unfollows}...")
        random.shuffle(users_to_unfollow) # Randomize to avoid hitting API limits in patterns
        unfollowed_count = 0

        for username in users_to_unfollow[:max_unfollows]:
            profile_url = f"{self.config_loader.get_platform_url('base')}/{username.lstrip('@')}"
            try:
                logger.debug(f"Navigating to profile: {profile_url}")
                self.driver.get(profile_url)
                self._wait((3, 6))

                # Find the "Following" button
                following_button_xpath = "//button[@data-testid='userFollowButton']//span[contains(text(), 'Following')]/ancestor::button[@data-testid='userFollowButton'] | //div[@data-testid='placementTracking']//span[contains(text(), 'Following')]/ancestor::div[@role='button']"
                unfollow_button = WebDriverWait(self.driver, default_wait).until(
                    EC.element_to_be_clickable((By.XPATH, following_button_xpath))
                )
                unfollow_button.click()
                logger.debug(f"Clicked 'Following' button for {username}.")
                self._wait((1, 2))

                # Find and click the confirmation button
                confirm_unfollow_xpath = "//button[@data-testid='confirmationSheetConfirm']//span[contains(text(), 'Unfollow')]/ancestor::button[@data-testid='confirmationSheetConfirm']"
                confirm_unfollow = WebDriverWait(self.driver, default_wait).until(
                    EC.element_to_be_clickable((By.XPATH, confirm_unfollow_xpath))
                )
                confirm_unfollow.click()
                logger.info(f"Successfully unfollowed {username}.")
                unfollowed_count += 1

                # Update status in tracker
                follow_data[username]["status"] = "unfollowed"
                follow_data[username]["unfollowed_at"] = datetime.utcnow().isoformat()
                # Add interaction record
                interaction = {"type": "unfollowed_user", "timestamp": datetime.utcnow().isoformat(), "metadata": {"reason": "time_threshold"}}
                follow_data[username].setdefault("interactions", []).append(interaction)
                self.track_member_interaction(username, "unfollowed_user", {"reason": "time_threshold"})

                self._wait((2, 5)) # Wait after unfollowing

                # Save progress periodically
                if unfollowed_count % 5 == 0:
                    try:
                        with open(self.follow_db_path, "w", encoding='utf-8') as f:
                            json.dump(follow_data, f, indent=4, ensure_ascii=False)
                        logger.debug(f"Saved follow tracker progress after {unfollowed_count} unfollows.")
                    except Exception as save_err:
                        logger.error(f"Error saving follow tracker during unfollow process: {save_err}")

            except (NoSuchElementException, TimeoutException, ElementClickInterceptedException) as unfollow_err:
                logger.warning(f"Could not unfollow {username} (button not found or interaction failed): {unfollow_err}")
                # Maybe the user already unfollowed us or changed their name?
                # Consider marking as 'unfollow_failed' or removing?
                follow_data[username]["status"] = "unfollow_failed"
            except Exception as e:
                logger.error(f"Unexpected error unfollowing {username}: {e}", exc_info=True)

        # Final save
        try:
            with open(self.follow_db_path, "w", encoding='utf-8') as f:
                json.dump(follow_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Unfollow process complete. Attempted {len(users_to_unfollow[:max_unfollows])}, successfully unfollowed {unfollowed_count} users.")
        except Exception as e:
            logger.error(f"Error saving final follow tracker state after unfollowing: {e}")

    def _load_feedback_data(self):
        """Loads feedback data from the JSON file using config path."""
        logger.debug(f"Loading feedback data from: {self.feedback_db_path}")
        if os.path.exists(self.feedback_db_path):
            try:
                with open(self.feedback_db_path, "r", encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as json_err:
                 logger.error(f"Error decoding JSON from {self.feedback_db_path}: {json_err}")
                 return {}
            except Exception as e:
                logger.error(f"Error loading feedback data from {self.feedback_db_path}: {e}")
                return {}
        logger.info(f"Feedback data file not found at {self.feedback_db_path}, starting fresh.")
        return {}

    def _save_feedback_data(self):
        """Saves feedback data to the JSON file using config path."""
        logger.debug(f"Saving feedback data to: {self.feedback_db_path}")
        try:
            os.makedirs(os.path.dirname(self.feedback_db_path), exist_ok=True)
            with open(self.feedback_db_path, "w", encoding='utf-8') as f:
                json.dump(self.feedback_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving feedback data to {self.feedback_db_path}: {e}")

    def analyze_engagement_metrics(self):
        """
        Analyzes Twitter engagement metrics based on tracked interactions/feedback data.
        (Placeholder - requires actual data scraping or API usage for accurate metrics).
        """
        logger.info(f"Analyzing {self.PLATFORM.capitalize()} engagement metrics (placeholder)...")
        interactions = self.feedback_data.get("interactions", []) # Assumes feedback_data might store interactions
        # Example: Calculate stats based on interaction types logged by track_member_interaction
        likes_received = len([i for i in interactions if i['type'] == 'liked_tweet']) # Example key
        comments_received = len([i for i in interactions if i['type'] == 'commented_on_tweet'])
        follows_gained = len([i for i in interactions if i['type'] == 'followed_user' and i['metadata'].get('source') == 'organic']) # Hypothetical tracking
        posts_made = len([i for i in interactions if i['type'] == 'tweet_posted' or i['type'] == 'thread_posted'])

        # Update feedback_data with calculated/estimated metrics
        self.feedback_data["calculated_likes"] = likes_received
        self.feedback_data["calculated_comments"] = comments_received
        self.feedback_data["calculated_follows"] = follows_gained
        self.feedback_data["posts_made_last_cycle"] = posts_made

        # Update overall sentiment based on analyzed comments (requires comment tracking)
        comment_interactions = [i for i in interactions if i['type'] == 'comment_received']
        sentiments = [i['metadata'].get('sentiment') for i in comment_interactions if 'sentiment' in i.get('metadata', {})]
        if sentiments:
            positive_rate = sentiments.count('positive') / len(sentiments)
            negative_rate = sentiments.count('negative') / len(sentiments)
            self.feedback_data["overall_sentiment"] = positive_rate - negative_rate
        else:
            self.feedback_data.setdefault("overall_sentiment", 0.0)

        logger.info(f"Updated Metrics - Likes: {likes_received}, Comments: {comments_received}, Follows: {follows_gained}, Sentiment: {self.feedback_data['overall_sentiment']:.2f}")
        self._save_feedback_data()

    def adaptive_posting_strategy(self):
        """
        Adjusts posting strategy based on analyzed feedback.
        (Placeholder - requires linking metrics to strategy changes).
        """
        logger.info(f"Adapting {self.PLATFORM.capitalize()} posting strategy (placeholder)...")
        likes = self.feedback_data.get("calculated_likes", 0)
        comments = self.feedback_data.get("calculated_comments", 0)
        sentiment = self.feedback_data.get("overall_sentiment", 0.0)

        # Use thresholds from config loader
        high_likes_threshold = self.config_loader.get_parameter("engagement_high_threshold_likes", 50)
        high_comments_threshold = self.config_loader.get_parameter("engagement_high_threshold_comments", 10)
        positive_sentiment_threshold = self.config_loader.get_parameter("positive_sentiment_threshold", 0.2)
        negative_sentiment_threshold = self.config_loader.get_parameter("negative_sentiment_threshold", -0.2)

        if (likes > high_likes_threshold or comments > high_comments_threshold) and sentiment > positive_sentiment_threshold:
            logger.info("Feedback positive: High engagement! Consider increasing post frequency or focusing on similar content themes.")
            # Example: Suggest adjusting post_frequency_per_day or content_mix in config
        elif sentiment < negative_sentiment_threshold:
            logger.warning("Feedback indicates negative sentiment: Review content tone, topics, or engagement replies.")
            # Example: Suggest changing ai_comment_tone in config or reviewing keywords
        else:
            logger.info("Engagement metrics are moderate. Maintaining current strategy.")
        # TODO: Add logic to analyze performance per keyword/topic/content_type if tracked

    def analyze_comment_sentiment(self, comment: str) -> str:
        """Analyzes the sentiment of a given comment using the AI agent."""
        logger.debug(f"Analyzing sentiment for comment: {comment[:50]}...")
        sentiment_prompt = f"Analyze the sentiment of this Twitter comment: '{comment}'. Respond with only 'positive', 'neutral', or 'negative'."
        # Use a potentially different model/tone for analysis if needed via config
        analysis_model = self.config_loader.get_parameter("ai_sentiment_model", default=self.ai_agent.model)
        sentiment = self.ai_agent.ask(
             prompt=sentiment_prompt,
             model_override=analysis_model, # Allow overriding model for specific task
             metadata={"platform": self.PLATFORM, "task": "sentiment_analysis"}
         )
        sentiment = sentiment.strip().lower() if sentiment else "neutral"
        if sentiment not in ["positive", "neutral", "negative"]:
            logger.warning(f"Unexpected sentiment analysis result: '{sentiment}'. Defaulting to neutral.")
            sentiment = "neutral"
        logger.info(f"Comment sentiment classified as: {sentiment}")
        # Optionally store sentiment with interaction data immediately
        # self.track_member_interaction(comment_author_id, "comment_analyzed", {"comment": comment, "sentiment": sentiment})
        return sentiment

    def reinforce_engagement(self, comment: str, comment_author: str, tweet_id: Optional[str] = None):
        """Generates and potentially posts a reinforcing reply to a positive comment."""
        sentiment = self.analyze_comment_sentiment(comment)
        if sentiment == "positive":
            logger.info(f"Positive comment detected from {comment_author}. Generating reinforcement...")
            reinforcement_prompt = f"As Victor (on Twitter), write a brief, appreciative, and engaging reply to this positive comment: '{comment}'"
            reply = self.ai_agent.ask(prompt=reinforcement_prompt, metadata={"platform": self.PLATFORM, "persona": "Victor_Twitter", "task": "reinforce_engagement"})

            if reply:
                logger.info(f"Generated reinforcement reply: {reply}")
                # TODO: Implement logic to actually post the reply on Twitter
                # This requires finding the comment/tweet and using the reply functionality.
                # Example: self.reply_to_tweet(tweet_id, comment_id, reply)
                logger.warning("Posting reinforcement replies is not yet implemented.")
                # Log the intended action and track interaction
                interaction_meta = {"comment": comment, "intended_reply": reply, "sentiment": sentiment}
                if tweet_id: interaction_meta["original_tweet_id"] = tweet_id
                self.track_member_interaction(comment_author, "positive_comment_received", interaction_meta)
                return reply
            else:
                logger.warning("AI failed to generate reinforcement reply.")
        else:
            logger.debug(f"Comment sentiment ({sentiment}) does not warrant reinforcement.")
            # Log non-positive interaction if desired
            # interaction_meta = {"comment": comment, "sentiment": sentiment}
            # if tweet_id: interaction_meta["original_tweet_id"] = tweet_id
            # self.track_member_interaction(comment_author, f"{sentiment}_comment_received", interaction_meta)
        return None

    def reward_top_engagers(self):
        """Identifies and rewards top engagers based on interaction data."""
        logger.info(f"Evaluating top {self.PLATFORM.capitalize()} engagers for rewards...")
        if not self.config_loader.get_parameter("enable_rewards", default=True):
             logger.info("Rewards disabled in configuration.")
             return

        reward_data = {}
        if os.path.exists(self.reward_db_path):
            try:
                with open(self.reward_db_path, "r", encoding='utf-8') as f:
                    reward_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading reward data from {self.reward_db_path}: {e}")

        # --- Logic for Identifying Top Engager ---
        # Uses get_top_members which calculates scores based on follow_db interactions
        top_members = self.get_top_members()
        if top_members:
            reward_threshold_score = self.config_loader.get_parameter("reward_min_engagement_score", 10)
            reward_cooldown_days = self.config_loader.get_parameter("reward_cooldown_days", 30)
            num_rewards_per_run = self.config_loader.get_parameter("rewards_per_run", 1)
            rewarded_count = 0

            for potential_rewardee in top_members:
                if rewarded_count >= num_rewards_per_run:
                     break

                member_id = potential_rewardee["id"]
                score = potential_rewardee["engagement_score"]

                if score < reward_threshold_score:
                     logger.debug(f"Member {member_id} score ({score}) below threshold ({reward_threshold_score}).")
                     continue # Skip if score too low

                last_rewarded_str = reward_data.get(member_id, {}).get("rewarded_at")
                if last_rewarded_str:
                     try:
                          last_rewarded_dt = datetime.fromisoformat(last_rewarded_str)
                          if (datetime.utcnow().replace(tzinfo=timezone.utc) - last_rewarded_dt).days < reward_cooldown_days:
                               logger.debug(f"Member {member_id} already rewarded within cooldown period ({reward_cooldown_days} days).")
                               continue # Skip if rewarded recently
                     except ValueError:
                          logger.warning(f"Could not parse last_rewarded_at timestamp for {member_id}.")

                logger.info(f"Identified potential top engager for reward: {member_id} (Score: {score})")
                # Generate reward message/action
                reward_message_prompt = f"As Victor (on Twitter), write a brief, personalized shout-out message thanking user @{member_id.lstrip('@')} for their amazing engagement and contribution to the community."
                reward_message = self.ai_agent.ask(reward_message_prompt)

                if not reward_message:
                     reward_message = f"Huge thanks to @{member_id.lstrip('@')} for being a standout member of our Twitter community! Your engagement is truly appreciated. ✨"

                # TODO: Implement actual reward action (e.g., post shoutout tweet mentioning user)
                # Example: self.post_tweet(reward_message)
                logger.warning(f"Actual reward action (e.g., shoutout tweet) for {member_id} not implemented. Logging intent.")

                # Log reward
                now_iso = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
                reward_data[member_id] = {
                    "rewarded_at": now_iso,
                    "type": "shoutout_placeholder",
                    "engagement_score_at_reward": score,
                    "message_logged": reward_message
                }
                self.track_member_interaction(member_id, "reward_issued", {"type": "shoutout_placeholder", "score": score})
                rewarded_count += 1

            # Save updated reward data
            if rewarded_count > 0:
                 try:
                      os.makedirs(os.path.dirname(self.reward_db_path), exist_ok=True)
                      with open(self.reward_db_path, "w", encoding='utf-8') as f:
                           json.dump(reward_data, f, indent=4, ensure_ascii=False)
                      logger.info(f"Reward data saved. Issued {rewarded_count} reward(s).")
                      write_json_log(self.PLATFORM, "success", tags=["reward"], details=f"Issued {rewarded_count} reward(s)")
                 except Exception as e:
                      logger.error(f"Failed to save reward data: {e}")
            else:
                 logger.info("No new rewards issued in this cycle.")
        else:
            logger.info("No top members identified based on current tracking data.")

    def cross_platform_feedback_loop(self):
        """Merges Twitter feedback with data from other platforms (stub)."""
        if not self.config_loader.get_parameter("enable_cross_platform_analysis", default=False):
             return # Skip if disabled

        logger.info("Merging cross-platform feedback loops (placeholder)...")
        # TODO: Implement actual merging logic using config loader for paths/params
        # Example: Fetch data from other platform feedback files/DBs
        # facebook_feedback_path = self.config_loader.get_data_path(FEEDBACK_DB, platform="facebook") # Needs platform param in get_data_path
        unified_metrics = {
            "twitter": self.feedback_data.get("calculated_likes", 0), # Example metric
            # "facebook": facebook_data.get("avg_likes_per_post", 0),
            # "reddit": ...
        }
        logger.info(f"Unified Metrics (Placeholder): {unified_metrics}")
        # Could update a central dashboard or trigger broader strategy adjustments

    def run_feedback_loop(self):
        """Runs the analysis and adaptation steps of the feedback loop."""
        logger.info(f"--- Running {self.PLATFORM.capitalize()} Feedback Analysis ---")
        self.analyze_engagement_metrics()
        logger.info(f"--- Running {self.PLATFORM.capitalize()} Adaptive Strategy ---")
        self.adaptive_posting_strategy()
        logger.info(f"--- Running {self.PLATFORM.capitalize()} Reward Evaluation ---")
        self.reward_top_engagers()
        # Run cross-platform only if enabled
        self.cross_platform_feedback_loop()

    def run_daily_strategy_session(self):
        """Executes the full daily strategy for Twitter using configured parameters."""
        logger.info(f"===== Starting Daily {self.PLATFORM.capitalize()} Strategy Session =====")
        if not self.config_loader.is_enabled():
            logger.warning(f"{self.PLATFORM.capitalize()} strategy is disabled. Session aborted.")
            return

        if not self.is_logged_in():
            logger.warning("Not logged in. Attempting login...")
            if not self.login():
                logger.error("Session failed: Could not log in.")
                return

        # Load parameters from config loader
        post_freq = self.config_loader.get_parameter("post_frequency_per_day", default=1)
        content_mix = self.config_loader.get_parameter("content_mix", default={"tweet": 1.0}) # e.g., {"tweet": 0.8, "thread": 0.2}
        keywords = self.config_loader.get_parameter("targeting_keywords", default=["AI", "trading", "automation"])
        enable_engagement = self.config_loader.get_parameter("enable_engagement", default=True)
        engagement_actions = self.config_loader.get_parameter("engagement_actions_per_run", default=10)
        like_tweets = self.config_loader.get_parameter("engagement_like_tweets", default=True)
        comment_on_tweets = self.config_loader.get_parameter("engagement_comment_on_tweets", default=True)
        follow_users = self.config_loader.get_parameter("engagement_follow_users", default=False)
        enable_unfollow = self.config_loader.get_parameter("enable_unfollow", default=True)
        enable_feedback = self.config_loader.get_parameter("enable_feedback_loop", default=True)
        post_interval_range = self.config_loader.get_parameter("post_interval_wait_range", default=(60, 180))
        engage_query_count = self.config_loader.get_parameter("engagement_query_count", default=1)

        logger.info(f"Session Config: Freq={post_freq}, Mix={content_mix}, Keywords={keywords}, Engage={enable_engagement}, Actions={engagement_actions}")

        # --- Content Posting ---
        posted_count = 0
        for i in range(post_freq):
            logger.info(f"--- Preparing Post {i+1}/{post_freq} ---")
            try:
                # Choose content type based on configured mix
                if not content_mix:
                     logger.warning("Content mix not defined in config, defaulting to single tweet.")
                     chosen_type = "tweet"
                else:
                     chosen_type = random.choices(list(content_mix.keys()), weights=list(content_mix.values()), k=1)[0]

                logger.debug(f"Selected content type: {chosen_type}")
                topic = random.choice(keywords) if keywords else "current events"

                if chosen_type == "thread":
                    # Generate thread content
                    thread_prompt = f"Generate a short Twitter thread (3-5 parts) about '{topic}'. Each part should be concise and engaging. Persona: {self.ai_agent.tone}."
                    ai_thread_text = self.ai_agent.ask(thread_prompt, metadata={"platform": self.PLATFORM, "task": "generate_thread"})
                    if ai_thread_text:
                        # Split into parts (handle potential variations in AI output format)
                        parts = [p.strip() for p in ai_thread_text.split("\n\n") if p.strip()] # Basic split
                        if len(parts) < 2:
                             # Try splitting by single newline if double failed
                             parts = [p.strip() for p in ai_thread_text.split("\n") if p.strip() and len(p) > 10] # Add length check

                        if len(parts) > 1:
                            logger.info(f"Posting thread about '{topic}' ({len(parts)} parts)...")
                            if self.post_thread(parts):
                                posted_count += 1
                                self.track_member_interaction(self.username or 'self', "thread_posted", {"topic": topic, "parts": len(parts)}) # Use unified tracker
                            else:
                                logger.error("Failed to post thread.")
                        else:
                            # If still not enough parts, post as single tweet
                            logger.warning(f"AI generated insufficient parts for a thread ({len(parts)} found), posting as single tweet.")
                            if self.post_tweet(ai_thread_text):
                                posted_count += 1
                                self.track_member_interaction(self.username or 'self', "tweet_posted", {"topic": topic, "source": "thread_fallback"})
                            else:
                                logger.error("Failed to post single tweet (from thread attempt).")
                    else:
                        logger.warning(f"AI failed to generate thread content for '{topic}'.")

                else: # Default to single tweet
                    tweet_prompt = f"Generate a concise, engaging tweet about '{topic}'. Include 1-2 relevant hashtags. Persona: {self.ai_agent.tone}."
                    ai_tweet_text = self.ai_agent.ask(tweet_prompt, metadata={"platform": self.PLATFORM, "task": "generate_tweet"})
                    if ai_tweet_text:
                        logger.info(f"Posting tweet about '{topic}'...")
                        if self.post_tweet(ai_tweet_text):
                            posted_count += 1
                            self.track_member_interaction(self.username or 'self', "tweet_posted", {"topic": topic}) # Use unified tracker
                        else:
                            logger.error("Failed to post tweet.")
                    else:
                        logger.warning(f"AI failed to generate tweet content for '{topic}'.")

                # Wait between posts
                if i < post_freq - 1: # Don't wait after the last post
                    self._wait(post_interval_range)

            except Exception as post_err:
                logger.error(f"Error during posting loop iteration {i+1}: {post_err}", exc_info=True)
                continue # Continue to next post attempt

        logger.info(f"Content posting phase complete. Posted {posted_count}/{post_freq} items.")

        # --- Community Engagement ---
        if enable_engagement and keywords:
            logger.info(f"--- Starting Community Engagement (Actions per query: {engagement_actions}) ---")
            # Select queries for engagement
            selected_queries = random.sample(keywords, min(engage_query_count, len(keywords)))
            logger.info(f"Engaging with queries: {selected_queries}")
            for query in selected_queries:
                try:
                    self.engage_community(
                        query=query,
                        num_to_engage=engagement_actions,
                        like=like_tweets,
                        comment=comment_on_tweets,
                        follow=follow_users
                    )
                    self._wait(self.config_loader.get_parameter("engagement_query_interval_wait", default=(15, 45)))
                except Exception as engage_err:
                    logger.error(f"Error during engagement for query '{query}': {engage_err}", exc_info=True)
                    continue # Continue to next query
        elif enable_engagement:
            logger.warning("Engagement enabled but no keywords configured. Skipping engagement phase.")
        else:
            logger.info("Community engagement is disabled in configuration.")

        # --- Unfollow Routine ---
        if enable_unfollow:
            logger.info("--- Starting Unfollow Routine ---")
            try:
                self.unfollow_non_returners()
            except Exception as unfollow_err:
                logger.error(f"Error during unfollow routine: {unfollow_err}", exc_info=True)
        else:
            logger.info("Unfollowing is disabled in configuration.")

        # --- Feedback Loop ---
        if enable_feedback:
            logger.info("--- Running Feedback Loop ---")
            try:
                self.run_feedback_loop()
            except Exception as feedback_err:
                logger.error(f"Error during feedback loop: {feedback_err}", exc_info=True)
        else:
            logger.info("Feedback loop is disabled in configuration.")

        logger.info(f"===== Daily {self.PLATFORM.capitalize()} Strategy Session Complete =====")

    def get_community_metrics(self) -> Dict[str, Any]:
        """Retrieves community metrics specific to Twitter."""
        logger.info(f"Retrieving {self.PLATFORM.capitalize()} community metrics...")
        # Load follower count estimate if tracked (needs implementation for how to get this)
        # Example: Could scrape profile or estimate from feedback
        follower_count = self.feedback_data.get("follower_count_estimate", 0)
        # Use calculated stats from feedback data (populated by analyze_engagement_metrics)
        likes = self.feedback_data.get("calculated_likes", 0)
        comments = self.feedback_data.get("calculated_comments", 0)
        posts = self.feedback_data.get("posts_made_last_cycle", 0)
        sentiment = self.feedback_data.get("overall_sentiment", 0.0)

        # Rough engagement rate estimate (per post, needs refinement)
        engagement_rate = ((likes + comments) / follower_count) * 100 if follower_count > 0 and posts > 0 else 0

        metrics = {
            "platform": self.PLATFORM,
            "follower_count_estimate": follower_count,
            "engagement_rate_estimate": round(engagement_rate, 2), # Example: (Likes+Comments)/Followers
            "calculated_likes_last_cycle": likes,
            "calculated_comments_last_cycle": comments,
            "posts_made_last_cycle": posts,
            "sentiment_score": round(sentiment, 2),
            "target_keywords": self.config_loader.get_parameter("targeting_keywords", []),
            "current_post_frequency": self.config_loader.get_parameter("post_frequency_per_day", 0)
        }
        logger.debug(f"{self.PLATFORM.capitalize()} Metrics: {metrics}")
        return metrics

    def get_top_members(self) -> List[Dict[str, Any]]:
        """Gets list of top Twitter members based on interaction tracking file."""
        logger.info(f"Identifying top {self.PLATFORM.capitalize()} members...")
        top_members = []
        if os.path.exists(self.follow_db_path):
            try:
                with open(self.follow_db_path, "r", encoding='utf-8') as f:
                    follow_data = json.load(f)

                for member_id, data in follow_data.items():
                    interactions = data.get("interactions", [])
                    # Calculate score based on interaction types and frequency
                    score = 0
                    like_weight = self.config_loader.get_parameter("score_weight_like", 1)
                    comment_weight = self.config_loader.get_parameter("score_weight_comment", 2)
                    follow_weight = self.config_loader.get_parameter("score_weight_follow", 5) # Score for them following us? Needs tracking.
                    retweet_weight = self.config_loader.get_parameter("score_weight_retweet", 3) # Needs tracking
                    mention_weight = self.config_loader.get_parameter("score_weight_mention", 4) # Needs tracking
                    positive_comment_weight = comment_weight * self.config_loader.get_parameter("score_multiplier_positive_comment", 1.5)

                    for interaction in interactions:
                        interaction_type = interaction.get("type")
                        # --- Score based on OUR actions towards them (less valuable?) ---
                        # if interaction_type == 'liked_tweet': score += like_weight * 0.1 # Small score for us liking
                        # if interaction_type == 'commented_on_tweet': score += comment_weight * 0.2 # Small score for us commenting
                        # if interaction_type == 'followed_user': score += follow_weight * 0.1 # Small score for us following

                        # --- Score based on THEIR actions towards us (more valuable) ---
                        # These interaction types need to be logged when detected (e.g., via notifications scraping or API)
                        if interaction_type == 'received_like': score += like_weight
                        elif interaction_type == 'received_comment': score += comment_weight
                        elif interaction_type == 'positive_comment_received': score += positive_comment_weight # Higher score for positive
                        elif interaction_type == 'received_follow': score += follow_weight
                        elif interaction_type == 'received_retweet': score += retweet_weight
                        elif interaction_type == 'received_mention': score += mention_weight

                    # Add recency boost? Decay old scores? (Complex, skip for now)
                    # Apply score multiplier if they are currently following back? (Requires follow-back check)

                    member = {
                        "id": member_id,
                        "platform": self.PLATFORM,
                        "engagement_score": round(score, 2),
                        "status": data.get("status", "unknown"),
                        "followed_at": data.get("followed_at") or data.get("last_followed_at"),
                        "last_interaction": interactions[-1]["timestamp"] if interactions else data.get("tracked_at")
                    }
                    top_members.append(member)

                top_members.sort(key=lambda x: x["engagement_score"], reverse=True)
                top_members = top_members[:self.config_loader.get_parameter("top_members_count", 20)]
                logger.info(f"Identified {len(top_members)} top members.")

            except Exception as e:
                logger.error(f"Error processing follow data from {self.follow_db_path}: {e}", exc_info=True)
        else:
            logger.info(f"Follow tracker file not found at {self.follow_db_path}. Cannot determine top members.")

        return top_members

    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Tracks an interaction with a Twitter user in the follow/interaction file."""
        # Consolidate logic here, _log_follow can just call this
        logger.debug(f"Tracking interaction: Member={member_id}, Type={interaction_type}")
        if not member_id or member_id == 'unknown_user':
             logger.warning(f"Skipping tracking interaction - invalid member_id: {member_id}")
             return False

        try:
            # Ensure interaction type is valid/expected?
            # valid_types = ["followed_user", "unfollowed_user", "liked_tweet", ...]
            # if interaction_type not in valid_types: logger.warning(...) ?

            if os.path.exists(self.follow_db_path):
                try:
                     with open(self.follow_db_path, "r", encoding='utf-8') as f:
                          follow_data = json.load(f)
                except json.JSONDecodeError:
                     logger.error(f"Error decoding JSON from {self.follow_db_path}. Creating new dictionary.")
                     follow_data = {}
            else:
                follow_data = {}

            now_iso = datetime.utcnow().isoformat()
            # Standardize member_id (e.g., remove leading '@')
            standardized_member_id = member_id.lstrip('@')

            member_data = follow_data.setdefault(standardized_member_id, { # Use standardized ID
                "tracked_at": now_iso,
                "type": "user",
                "status": "active", # Initial status
                "interactions": []
            })

            # Clean up metadata (e.g., truncate long text previews)
            cleaned_metadata = metadata or {}
            for key, value in cleaned_metadata.items():
                 if isinstance(value, str) and len(value) > 200: # Truncate long strings
                      cleaned_metadata[key] = value[:197] + "..."

            interaction = {
                "type": interaction_type,
                "timestamp": now_iso,
                "metadata": cleaned_metadata
            }
            # Prepend interaction to make recent ones first? Or append?
            member_data.setdefault("interactions", []).append(interaction)

            # Limit interaction history size per member?
            max_interactions = self.config_loader.get_parameter("max_interactions_per_member", 50)
            if len(member_data["interactions"]) > max_interactions:
                 member_data["interactions"] = member_data["interactions"][-max_interactions:]

            # Update top-level status based on interaction type if needed
            if interaction_type == "followed_user":
                 member_data["status"] = "followed"
                 member_data["last_followed_at"] = now_iso
            elif interaction_type == "unfollowed_user":
                 member_data["status"] = "unfollowed"
                 member_data["unfollowed_at"] = now_iso
            elif interaction_type == "received_follow": # If we track this
                 member_data["status"] = "following_back"
                 member_data["followed_back_at"] = now_iso

            # Update last interaction timestamp
            member_data["last_interaction_at"] = now_iso

            # Save updated data
            os.makedirs(os.path.dirname(self.follow_db_path), exist_ok=True)
            with open(self.follow_db_path, "w", encoding='utf-8') as f:
                json.dump(follow_data, f, indent=4, ensure_ascii=False)

            logger.debug(f"Interaction {interaction_type} tracked for {standardized_member_id}.")
            return True
        except Exception as e:
            logger.error(f"Error tracking {self.PLATFORM.capitalize()} interaction for {member_id}: {e}", exc_info=True)
            return False

if __name__ == "__main__":
    print(f"Running {PLATFORM.capitalize()}Strategy directly for testing...")
    strategy = TwitterStrategy()
    creds = {
        "email": social_config.get_env("TWITTER_EMAIL"), # Still using social_config here for test values
        "username": social_config.get_env("TWITTER_USERNAME"),
        "password": social_config.get_env("TWITTER_PASSWORD")
    }
    if strategy.initialize(creds):
        print("Strategy initialized (login attempted). Note: Methods are placeholders.")
        # Example test call (will just log warnings)
        # strategy.run_daily_strategy_session()
        if strategy.is_logged_in():
             print("Login check returned True (using placeholder). Actual login state unknown.")
        else:
             print("Login check returned False (using placeholder). Actual login state unknown.")
    else:
        print("Strategy initialization failed.")

    strategy.cleanup()
    print(f"{PLATFORM.capitalize()}Strategy direct test finished.")
