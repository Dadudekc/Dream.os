import os
import time
import json
import random
from datetime import datetime
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
from utils.SentimentAnalyzer import SentimentAnalyzer
from .strategy_config_loader import StrategyConfigLoader

logger = get_social_logger()

# Define constants
PLATFORM = "tiktok"
FEEDBACK_DB = "social/data/tiktok_feedback_tracker.json"
REWARD_DB = "social/data/tiktok_reward_tracker.json"
FOLLOW_DB = "social/data/tiktok_follow_tracker.json"

class TikTokStrategy(BasePlatformStrategy):
    """
    Centralized strategy class for TikTok automation and community building,
    leveraging StrategyConfigLoader.
    Extends BasePlatformStrategy with TikTok-specific implementations.
    Features:
      - Dynamic feedback loops with AI sentiment analysis
      - Video content scheduling and posting
      - Hashtag trend analysis and optimization
      - Cross-platform content repurposing (stubbed)
      - Engagement analytics and community growth tracking
    """
    
    PLATFORM = PLATFORM

    def __init__(self, driver=None):
        """Initialize TikTok strategy using StrategyConfigLoader."""
        super().__init__(platform_id=self.PLATFORM, driver=driver)
        self.config_loader = StrategyConfigLoader(platform=self.PLATFORM)
        self.ai_agent = AIChatAgent(
            model=self.config_loader.get_parameter("ai_model", "gpt-4o"),
            tone=self.config_loader.get_parameter("ai_comment_tone", "Victor_TikTok"),
            provider=self.config_loader.get_parameter("ai_provider", "openai")
        )
        self.cookie_manager = CookieManager()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.feedback_data = self._load_feedback_data()
        self.username = None
        self.password = None
        self.trending_hashtags = []
        self.video_templates = self.config_loader.get_parameter("video_templates", default=[
            "educational_short", "behind_the_scenes", "quick_tips", "trend_participation"
        ])
        self.follow_db_path = self.config_loader.get_data_path(FOLLOW_DB)
    
    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize TikTok strategy with credentials."""
        logger.info(f"Initializing {self.PLATFORM.capitalize()}Strategy...")
        self.username = credentials.get("username") # Assuming username login is preferred/supported
        self.password = credentials.get("password")
        if not self.username or not self.password:
            logger.error(f"{self.PLATFORM.capitalize()} credentials not provided.")
            return False
        try:
            if not self.driver:
                logger.info("No driver provided, initializing default driver.")
                self.driver = self._get_driver() # Use specialized getter
            if not self.driver: # Check if driver initialization failed
                 logger.error(f"Driver initialization failed for {self.PLATFORM}. Cannot initialize.")
                 return False
            return self.login() # Attempt login after initialization
        except Exception as e:
            logger.error(f"Failed to initialize {self.PLATFORM.capitalize()} strategy: {e}", exc_info=True)
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources (driver)."""
        logger.info(f"Cleaning up {self.PLATFORM.capitalize()}Strategy resources...")
        return super().cleanup() # Use BasePlatformStrategy's cleanup
    
    def get_community_metrics(self) -> Dict[str, Any]:
        """Get TikTok-specific community metrics using feedback data and config."""
        logger.info(f"Retrieving {self.PLATFORM.capitalize()} community metrics...")
        metrics = {
            "platform": self.PLATFORM,
            "engagement_rate_estimate": self.config_loader.get_parameter("estimated_engagement_rate", default=2.5), # Typically higher on TikTok
            "target_keywords": self.config_loader.get_parameter("targeting_keywords", default=[]),
            "current_post_frequency": self.config_loader.get_parameter("post_frequency_per_day", default=1), # Default changed to 1
            "active_members_estimate": 0,
            "sentiment_score": self.feedback_data.get("overall_sentiment", 0.6),
            "video_metrics": {
                "avg_views": self.feedback_data.get("avg_views_per_video", 0),
                "avg_likes": self.feedback_data.get("avg_likes_per_video", 0),
                "avg_shares": self.feedback_data.get("avg_shares_per_video", 0),
                "avg_comments": self.feedback_data.get("avg_comments_per_video", 0)
            },
            # Use the key consistent with where hashtags are stored
            "trending_hashtags_captured": self.feedback_data.get("captured_trending_hashtags", [])[:5] # Show top 5 captured
        }

        try:
            # Estimate active members based on followers/interactions
            # Requires more robust tracking than just summing feedback counts
            follower_count = self.feedback_data.get("follower_count_estimate", 0)
            # interactions = self.feedback_data.get("interactions", []) # Needs structured interaction data
            # total_unique_interactors = len(set(i['member_id'] for i in interactions))
            metrics["active_members_estimate"] = follower_count # Placeholder, needs better logic
        except Exception as e:
            logger.error(f"Error calculating {self.PLATFORM.capitalize()} active member metrics: {e}")

        logger.debug(f"{self.PLATFORM.capitalize()} Metrics: {metrics}")
        return metrics

    def get_top_members(self) -> List[Dict[str, Any]]:
        """
        Get list of top TikTok community members based on interaction tracking.
        (Placeholder - needs robust interaction tracking).
        """
        logger.info(f"Identifying top {self.PLATFORM.capitalize()} members (placeholder)...")
        top_members = []
        if os.path.exists(self.follow_db_path): # Use correct path variable
            try:
                with open(self.follow_db_path, "r", encoding='utf-8') as f:
                    follow_data = json.load(f)

                for member_id, data in follow_data.items(): # member_id is likely username
                    interactions = data.get("interactions", [])
                    # Calculate score based on interaction types and frequency (example)
                    score = 0
                    for interaction in interactions:
                         if interaction['type'] == 'comment_received': score += 2
                         elif interaction['type'] == 'video_like': score += 1
                         elif interaction['type'] == 'follow': score += 5
                    # engagement_score = len(interactions) # Simple score
                    engagement_score = score # Use calculated score

                    member = {
                        "id": member_id,
                        "platform": self.PLATFORM,
                        "engagement_score": engagement_score,
                        "type": data.get("type", "user"),
                        "last_interaction": interactions[-1]["timestamp"] if interactions else data.get("tracked_at")
                    }
                    top_members.append(member)

                top_members.sort(key=lambda x: x["engagement_score"], reverse=True)
                # Load count from config
                top_members = top_members[:self.config_loader.get_parameter("top_members_count", 20)]

            except Exception as e:
                logger.error(f"Error processing follow data from {self.follow_db_path}: {e}")
        else:
            logger.info(f"Follow tracker file not found at {self.follow_db_path}. Cannot determine top members.")

        return top_members

    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Track an interaction with a TikTok user.
        Logs interaction to the follow/interaction tracking file.
        """
        logger.info(f"Tracking {self.PLATFORM.capitalize()} interaction: User={member_id}, Type={interaction_type}")
        try:
            if os.path.exists(self.follow_db_path): # Use correct path variable
                with open(self.follow_db_path, "r", encoding='utf-8') as f:
                    follow_data = json.load(f)
            else:
                follow_data = {}

            if member_id not in follow_data:
                follow_data[member_id] = {
                    "tracked_at": datetime.utcnow().isoformat(),
                    "type": "user",
                    "status": "active", # or "followed"
                    "interactions": []
                }

            interaction = {
                "type": interaction_type,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            follow_data[member_id].setdefault("interactions", []).append(interaction)

            # Save updated data
            os.makedirs(os.path.dirname(self.follow_db_path), exist_ok=True)
            with open(self.follow_db_path, "w", encoding='utf-8') as f:
                json.dump(follow_data, f, indent=4, ensure_ascii=False)

            logger.debug(f"Interaction tracked for {member_id}.")
            return True
        except Exception as e:
            logger.error(f"Error tracking {self.PLATFORM.capitalize()} member interaction for {member_id}: {e}")
            return False

    def _get_driver(self):
        """Get configured Chrome WebDriver for TikTok, potentially with mobile emulation."""
        if not self.driver:
            logger.info(f"{self.PLATFORM.capitalize()}Strategy: Initializing driver.")
            # Fetch driver config from loader
            headless = self.config_loader.get_parameter("headless_browser", default=False)
            user_agent = self.config_loader.get_parameter("user_agent_string", default=None) # Allow specific UA override
            profile_path = self.config_loader.get_parameter("chrome_profile_path", default=None) # Allow profile override
            window_size = self.config_loader.get_parameter("window_size", default=None) # e.g., "1920,1080"

            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            if profile_path:
                options.add_argument(f"--user-data-dir={profile_path}")
            if window_size:
                 options.add_argument(f"--window-size={window_size}")
            else: # Default to maximized if not specified
                 options.add_argument("--start-maximized")

            # Mobile Emulation Check
            if self.config_loader.get_parameter("enable_mobile_emulation", default=True):
                logger.debug("Mobile emulation enabled for TikTok driver.")
                mobile_emulation = {
                    "deviceMetrics": self.config_loader.get_parameter("mobile_device_metrics", default={"width": 360, "height": 640, "pixelRatio": 3.0}),
                    "userAgent": user_agent or self.config_loader.get_parameter("mobile_user_agent", default="Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36")
                }
                options.add_experimental_option("mobileEmulation", mobile_emulation)
                # Remove start-maximized if mobile emulation is on, as it can conflict
                for i, arg in enumerate(options.arguments):
                     if arg == "--start-maximized":
                          options.arguments.pop(i)
                          break
            elif user_agent: # Use desktop UA if specified and mobile emulation is off
                options.add_argument(f"user-agent={user_agent}")

            # Common options from base class or strategy-specific
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-infobars")
            options.add_argument("--ignore-certificate-errors")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            try:
                # Use Service object for better control (path can be managed by webdriver-manager or specified)
                service = webdriver.chrome.service.Service() # Assumes webdriver-manager handles path
                self.driver = webdriver.Chrome(service=service, options=options)
                logger.info(f"{self.PLATFORM.capitalize()} driver initialized.")
                # Add implicit wait from config?
                implicit_wait = self.config_loader.get_parameter("implicit_selenium_wait", default=0)
                if implicit_wait > 0:
                     self.driver.implicitly_wait(implicit_wait)
            except Exception as e:
                logger.error(f"Failed to initialize Chrome driver for {self.PLATFORM}: {e}", exc_info=True)
                self.driver = None

        return self.driver
    
    def _wait(self, custom_range=None):
        """Waits for a random duration within the configured range."""
        wait_range = custom_range or self.config_loader.get_parameter("wait_range_seconds", default=(3, 7)) # Use config loader
        wait_time = random.uniform(*wait_range)
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)
    
    def login(self) -> bool:
        """Log in to TikTok using credentials and cookies."""
        logger.info(f"Initiating login process for {self.PLATFORM}.")
        if not self._get_driver(): # Ensure driver is initialized
            logger.error("Cannot login: WebDriver is not initialized.")
            return False
        if not self.username or not self.password:
            logger.error("Cannot login: Username or password not set.")
            return False

        login_url = self.config_loader.get_platform_url("login")
        base_url = self.config_loader.get_platform_url("base") # For login check
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=20) # TikTok UI can be slow/complex

        try:
            self.driver.get(login_url)
            self._wait((5,10)) # Longer initial wait for page load
            self.cookie_manager.load_cookies(self.driver, self.PLATFORM)
            self.driver.refresh()
            self._wait((5,10))

            if self.is_logged_in():
                 logger.info(f"Logged into {self.PLATFORM} via cookies or existing session.")
                 write_json_log(self.PLATFORM, "successful", tags=["cookie_login"])
                 return True

            logger.info("Cookie/Session login failed. Attempting credential login.")
            self.driver.get(login_url) # Ensure on login page
            self._wait((5,10))

            # --- TikTok Login Flow (Example - needs verification and adaptation) ---
            # 1. Click the main login button
            try:
                # Combined XPath for flexibility
                 login_prompt_button_xpath = "//button[contains(., 'Log in')] | //div[contains(text(),'Log in to TikTok')] | //a[contains(@href, '/login')]/button"
                 login_button = WebDriverWait(self.driver, default_wait).until(
                     EC.element_to_be_clickable((By.XPATH, login_prompt_button_xpath))
                 )
                 login_button.click()
                 logger.debug("Clicked main login prompt button.")
                 self._wait((2, 4))
            except TimeoutException:
                 logger.warning("Main login prompt button not found or clickable, attempting to find fields directly.")
                 # Sometimes the fields are directly visible

            # 2. Select 'Use phone / email / username'
            try:
                 # More robust selector
                 use_alt_login_xpath = "//p[contains(text(), 'Use phone / email / username')] | //a[contains(@href, '/login/phone-or-email')] | //div[contains(text(), 'Use phone / email / username')]"
                 alt_login_button = WebDriverWait(self.driver, default_wait).until(
                     EC.element_to_be_clickable((By.XPATH, use_alt_login_xpath))
                 )
                 alt_login_button.click()
                 logger.debug("Clicked 'Use phone / email / username'.")
                 self._wait((2, 4))
            except TimeoutException:
                 logger.debug("'Use phone / email / username' button not found, assuming fields are visible.")

            # 3. Switch to 'Log in with email or username' if necessary
            try:
                 # More specific selector
                 email_username_tab_xpath = "//div[contains(text(), 'Email / Username')]/parent::div | //a[contains(text(), 'Log in with email or username')]"
                 email_tab = WebDriverWait(self.driver, default_wait).until(
                      EC.element_to_be_clickable((By.XPATH, email_username_tab_xpath))
                 )
                 # Check if it's already selected based on visual cues or attributes if possible
                 # This is tricky without inspection, might need adjustment
                 # if "selected" not in email_tab.get_attribute("class").lower(): # Example attribute check
                 email_tab.click()
                 logger.debug("Clicked 'Email / Username' tab.")
                 self._wait((1, 3))
            except TimeoutException:
                 logger.warning("Could not find or click 'Email / Username' tab. Proceeding with field search.")

            # 4. Fill credentials
            # Use more general selectors that might cover variations
            username_input_xpath = "//input[@name='username' or @name='user-input' or @placeholder='Email or username' or contains(@aria-label, 'Email or username')]"
            password_input_xpath = "//input[@type='password' or @name='password' or @placeholder='Password' or contains(@aria-label, 'Password')]"
            # Look for submit button within the form context if possible
            login_submit_button_xpath = "//form[contains(@action, 'login')]//button[@type='submit'][contains(., 'Log in')] | //button[@type='submit'][contains(., 'Log in')]"

            username_input = WebDriverWait(self.driver, default_wait).until(
                EC.visibility_of_element_located((By.XPATH, username_input_xpath))
            )
            password_input = WebDriverWait(self.driver, default_wait).until(
                 EC.visibility_of_element_located((By.XPATH, password_input_xpath))
            )

            username_input.send_keys(self.username)
            self._wait((0.5, 1))
            password_input.send_keys(self.password)
            self._wait((0.5, 1))

            # 5. Click final login button
            login_submit_button = WebDriverWait(self.driver, default_wait).until(
                 EC.element_to_be_clickable((By.XPATH, login_submit_button_xpath))
            )
            # Try JS click as fallback
            try:
                 login_submit_button.click()
            except ElementClickInterceptedException:
                 logger.warning("Standard click intercepted, trying JavaScript click for login submit.")
                 self.driver.execute_script("arguments[0].click();", login_submit_button)

            logger.info(f"Submitted credentials for {self.PLATFORM}.")
            self._wait((10, 20)) # Wait VERY long for potential CAPTCHAs / 2FA / loading

            # Verify login
            if self.is_logged_in():
                logger.info(f"Logged in successfully to {self.PLATFORM} using credentials.")
                self.cookie_manager.save_cookies(self.driver, self.PLATFORM)
                write_json_log(self.PLATFORM, "successful", tags=["credential_login"])
                return True
            else:
                # Add screenshot here for debugging
                screenshot_path = f"logs/tiktok_login_fail_{datetime.now():%Y%m%d_%H%M%S}.png"
                try:
                     os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                     self.driver.save_screenshot(screenshot_path)
                     logger.info(f"Saved screenshot of login failure to: {screenshot_path}")
                except Exception as ss_err:
                     logger.error(f"Failed to save screenshot: {ss_err}")

                logger.error(f"Credential login failed for {self.PLATFORM}. Check screenshot. Check for CAPTCHAs or 2FA prompts.")
                write_json_log(self.PLATFORM, "failed", tags=["credential_login"], ai_output="Login verification failed. Manual intervention likely required (CAPTCHA/2FA).")
                # Add manual wait here if configured
                # manual_wait_timeout = self.config_loader.get_parameter("manual_login_wait_timeout", 0)
                # if manual_wait_timeout > 0:
                #    logger.info(f"Waiting up to {manual_wait_timeout}s for manual login completion...")
                #    if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, self.PLATFORM, timeout=manual_wait_timeout):
                #         return True
                return False

        except Exception as e:
            logger.error(f"Error during {self.PLATFORM} login: {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["login_error"], ai_output=str(e))
            # self.driver.save_screenshot(f"error_login_{self.PLATFORM}.png")
            return False

    def is_logged_in(self) -> bool:
        """Check if logged into TikTok reliably."""
        if not self.driver:
            return False
        base_url = self.config_loader.get_platform_url("base")
        upload_url = self.config_loader.get_platform_url("upload") # Upload URL can sometimes indicate login
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=10)
        try:
            current_url = self.driver.current_url
            # If on login page, definitely not logged in
            if "login" in current_url or "signup" in current_url:
                 logger.debug(f"{self.PLATFORM} login check failed (on login/signup page: {current_url}).")
                 return False

            # Try navigating to a page requiring login (like upload) if not obviously logged in
            if "tiktok.com" not in current_url:
                 self.driver.get(base_url)
                 self._wait((3,5))
                 current_url = self.driver.current_url # Update after navigation
                 if "login" in current_url:
                      logger.debug(f"{self.PLATFORM} login check failed (redirected to login from base URL).")
                      return False

            # Look for profile icon, upload button, or other indicators
            # Combine multiple potential indicators for robustness
            profile_indicator_xpath = (
                "//a[contains(@href, '/profile')] | "                 # Profile link
                "//header//a[contains(@href, '/profile')] | "         # Profile link in header
                "//span[contains(text(), 'Upload')] | "             # Upload text/button
                "//a[contains(@href, '/upload')] | "             # Upload link
                "//img[contains(@src, 'avatar')] | "                 # User avatar image
                "//span[contains(., 'For You')] | "                  # Presence of 'For You' feed element
                "//*[@data-e2e='upload-icon']"                     # Data attribute for upload icon
            )
            WebDriverWait(self.driver, default_wait).until(
                EC.presence_of_element_located((By.XPATH, profile_indicator_xpath))
            )
            logger.debug(f"{self.PLATFORM} login confirmed via UI indicator. Current URL: {self.driver.current_url}")
            return True
        except TimeoutException:
            # Take screenshot on timeout for debugging
            screenshot_path = f"logs/tiktok_login_check_fail_{datetime.now():%Y%m%d_%H%M%S}.png"
            try:
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Saved screenshot of login check failure to: {screenshot_path}")
            except Exception as ss_err:
                logger.error(f"Failed to save screenshot: {ss_err}")
            logger.debug(f"{self.PLATFORM} login check failed (UI indicator not found). Current URL: {self.driver.current_url}")
            return False
        except Exception as e:
            logger.warning(f"Error during {self.PLATFORM} login check: {e}")
            return False
    
    def post_video(self, video_path: str, caption: str, hashtags: List[str] = None) -> bool:
        """
        Uploads a video file to TikTok with caption and hashtags.
        NOTE: TikTok web upload UI changes frequently and is prone to breaking.
              Consider API-based solutions for robust uploads if available.
        """
        logger.info(f"Attempting to upload video '{os.path.basename(video_path)}' to {self.PLATFORM}.")
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False
        # Ensure absolute path for Selenium
        abs_video_path = os.path.abspath(video_path)
        logger.debug(f"Absolute video path: {abs_video_path}")

        if not self.is_logged_in():
            logger.warning("Not logged in. Attempting login before uploading...")
            if not self.login():
                write_json_log(self.PLATFORM, "failed", tags=["post_video", "login_required"], ai_output="Login failed before uploading.")
                return False

        upload_url = self.config_loader.get_platform_url("upload")
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=25) # Upload page can be very slow
        upload_timeout = self.config_loader.get_parameter("video_upload_timeout_seconds", default=300) # Timeout for video processing

        try:
            logger.debug(f"Navigating to upload URL: {upload_url}")
            self.driver.get(upload_url)
            self._wait((5, 10))

            # --- TikTok Upload Flow (Example V3 - Highly Unstable) ---
            # 1. Handle potential initial overlays/popups (e.g., cookie banners, app prompts)
            #    (Add specific logic here if needed based on observed popups)
            #    Example: close_popup_if_present(xpath="//button[contains(@aria-label, 'close')]")

            # 2. Find the iframe for the uploader (if it exists)
            iframe_xpath = "//iframe[contains(@src, 'upload')] | //iframe[contains(@data-tt, 'upload')]" # More flexible selector
            in_iframe = False
            try:
                upload_iframe = WebDriverWait(self.driver, default_wait).until(
                    EC.presence_of_element_located((By.XPATH, iframe_xpath))
                )
                self.driver.switch_to.frame(upload_iframe)
                in_iframe = True
                logger.debug("Switched to upload iframe.")
            except TimeoutException:
                logger.debug("No upload iframe detected, assuming direct elements.")
                self.driver.switch_to.default_content() # Ensure back to default content if no iframe

            # 3. Find the file input element and send the video path
            # Combined XPath for various possible file input elements
            file_input_xpath = (
                "//input[@type='file'] | "
                "//button[contains(., 'Select file')]/preceding-sibling::input[@type='file'] | "
                "//div[contains(@class, 'upload-btn')]/input[@type='file'] | "
                "//div[contains(text(), 'Select video to upload')]/ancestor::button/input[@type='file'] |"
                 "//*[@data-e2e='upload-card']//input[@type='file']"
            )
            file_input = WebDriverWait(self.driver, default_wait).until(
                EC.presence_of_element_located((By.XPATH, file_input_xpath))
            )
            logger.debug(f"Found file input element using XPath: {file_input_xpath}")
            # Use JS to ensure visibility/interaction if needed, but try direct send_keys first
            try:
                 file_input.send_keys(abs_video_path)
            except Exception as send_keys_err:
                 logger.warning(f"Direct send_keys failed ({send_keys_err}), attempting JS value set.")
                 self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible'; arguments[0].value = arguments[1];", file_input, abs_video_path)
                 # May need to trigger change event manually after JS set
                 # self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", file_input)

            logger.info(f"Sent video file path: {abs_video_path}")

            # 4. Wait for upload to process and caption field to appear
            logger.info(f"Waiting up to {upload_timeout}s for video upload to process...")
            # More robust selector for caption area (often a div acting like a textbox)
            caption_indicator_xpath = (
                "//div[contains(@class, 'DraftEditor-root')]//div[@contenteditable='true'] | "
                "//div[@aria-label='Caption']//div[@role='textbox'] | "
                "//div[@data-contents='true'] | "
                "//*[@data-placeholder='Add caption']"
            )
            caption_input = WebDriverWait(self.driver, timeout=upload_timeout, poll_frequency=5).until(
                EC.visibility_of_element_located((By.XPATH, caption_indicator_xpath))
            )
            logger.info("Video upload processed, caption field visible.")
            self._wait((2, 4))

            # 5. Enter caption and hashtags
            full_caption = caption
            if hashtags:
                # Append hashtags intelligently
                full_caption += " \n" + " ".join([f"#{h.strip().replace(' ','')}" for h in hashtags]) # Ensure no spaces in hashtags

            # Use JS for input if direct send_keys is flaky
            try:
                 caption_input.click() # Focus first
                 # Clear existing content if any? Might delete placeholders unintentionally.
                 # caption_input.clear() # Use with caution
                 caption_input.send_keys(full_caption)
            except Exception as caption_err:
                 logger.warning(f"Direct send_keys for caption failed ({caption_err}), trying JS.")
                 # Focus and set value via JS
                 self.driver.execute_script("arguments[0].focus(); arguments[0].textContent = arguments[1];", caption_input, full_caption)
                 # Trigger input/change events if necessary
                 # self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", caption_input)

            logger.debug("Entered caption and hashtags.")
            self._wait((2, 4))

            # 6. Click the Post/Upload button
            # More robust selector for the final post button
            post_button_xpath = (
                 "//button[@type='button'][contains(., 'Post')] | "
                 "//button[contains(@class, 'btn-post')] | "
                 "//div[contains(@class,'btn-post')]/button |"
                 "//*[@data-e2e='upload-button']"
                 )
            post_button = WebDriverWait(self.driver, default_wait).until(
                EC.element_to_be_clickable((By.XPATH, post_button_xpath))
            )
            # Scroll into view if needed
            self.driver.execute_script("arguments[0].scrollIntoViewIfNeeded(true);", post_button)
            self._wait((0.5, 1))
            # Try JS click as fallback
            try:
                 post_button.click()
            except ElementClickInterceptedException:
                 logger.warning("Standard click intercepted, trying JavaScript click for Post button.")
                 self.driver.execute_script("arguments[0].click();", post_button)

            logger.info("Clicked final Post/Upload button.")
            self._wait((10, 25)) # Wait longer for post-processing/redirect

            # 7. Confirmation Check (Very difficult, prone to false positives/negatives)
            # Option 1: Check if redirected away from /upload URL
            # Option 2: Check for a success message popup (selectors change)
            # Option 3: Navigate to profile and check for the video (most reliable but slow)
            current_url = self.driver.current_url
            if "upload" not in current_url.lower():
                 logger.info("Redirected away from upload page, assuming success.")
            else:
                 # Check for success message (highly UI dependent)
                 try:
                      success_msg_xpath = "//span[contains(text(), 'Your video is uploading')] | //div[contains(text(), 'Successfully posted')]"
                      WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, success_msg_xpath)))
                      logger.info("Found success message element.")
                 except TimeoutException:
                      logger.warning("Did not redirect from upload page and no clear success message found. Post status uncertain.")
                      # Could attempt profile check here as a final verification

            logger.info(f"Video '{os.path.basename(video_path)}' likely uploaded to {self.PLATFORM}.")
            write_json_log(self.PLATFORM, "successful", tags=["post_video"], details=caption[:50])
            # Track successful post action
            self.track_member_interaction(self.username or 'unknown_user', "video_posted", {"caption": caption, "hashtags": hashtags, "video_path": abs_video_path})
            if in_iframe:
                 self.driver.switch_to.default_content() # Switch back from iframe if used
            return True

        except Exception as e:
            logger.error(f"Failed to upload video to {self.PLATFORM}: {e}", exc_info=True)
            screenshot_path = f"logs/tiktok_upload_fail_{datetime.now():%Y%m%d_%H%M%S}.png"
            try:
                 os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                 self.driver.save_screenshot(screenshot_path)
                 logger.info(f"Saved screenshot of upload failure to: {screenshot_path}")
            except Exception as ss_err:
                 logger.error(f"Failed to save screenshot: {ss_err}")
            write_json_log(self.PLATFORM, "failed", tags=["post_video", "error"], ai_output=str(e))
            try: # Ensure switch back from iframe on error
                if in_iframe:
                    self.driver.switch_to.default_content()
            except Exception as switch_err:
                 logger.error(f"Error switching back from iframe: {switch_err}")
            return False

    def run_daily_strategy_session(self):
        """
        Executes the full daily strategy for TikTok, focusing on video content.
        """
        logger.info(f"===== Starting Daily {self.PLATFORM.capitalize()} Strategy Session =====")
        if not self.config_loader.is_enabled():
            logger.warning(f"{self.PLATFORM.capitalize()} strategy is disabled. Session aborted.")
            return

        if not self.is_logged_in():
            logger.warning("Not logged in. Attempting login...")
            if not self.login():
                logger.error("Session failed: Could not log in.")
                return

        # --- Hashtag Update ---
        if self.config_loader.get_parameter("enable_hashtag_analysis", default=True):
            logger.info("--- Updating Trending Hashtags ---")
            self.update_trending_hashtags()
        else:
            logger.info("Hashtag analysis disabled in configuration.")

        # --- Content Posting (Video) ---
        post_freq = self.config_loader.get_parameter("post_frequency_per_day", default=1)
        keywords = self.config_loader.get_parameter("targeting_keywords", default=["AI tools", "automation tips", "system trading insights"])
        # Use get_data_path for potentially relative paths in config
        video_dir_config = self.config_loader.get_parameter("video_source_directory", default="social/assets/videos/tiktok")
        video_dir = self.config_loader.get_data_path(video_dir_config) # Resolve path relative to workspace/config

        logger.info(f"Session Config: Post Freq={post_freq}, Video Dir={video_dir}, Keywords={keywords}")

        # Find available video files
        available_videos = []
        if os.path.isdir(video_dir):
            try:
                # Filter for common video extensions
                video_extensions = self.config_loader.get_parameter("video_file_extensions", default=['.mp4', '.mov', '.avi'])
                available_videos = [
                    os.path.join(video_dir, f)
                    for f in os.listdir(video_dir)
                    if os.path.isfile(os.path.join(video_dir, f)) and os.path.splitext(f)[1].lower() in video_extensions
                ]
                logger.info(f"Found {len(available_videos)} video files in {video_dir}.")
            except Exception as e:
                 logger.error(f"Error listing video files in {video_dir}: {e}")
        else:
            logger.warning(f"Video source directory not found or not a directory: {video_dir}")

        if not available_videos:
            logger.error(f"No suitable video files found in directory: {video_dir}. Cannot post.")
            # Optionally, implement AI video generation/sourcing here
            # Consider skipping post loop instead of aborting entire session?
            # return # Abort if no videos
            post_freq = 0 # Skip posting loop if no videos

        for i in range(post_freq):
            logger.info(f"--- Preparing Video Post {i+1}/{post_freq} ---")
            if not available_videos: # Should not happen if post_freq was set to 0, but double-check
                 logger.error("No videos available to post.")
                 break
            video_path = random.choice(available_videos)
            topic = random.choice(keywords) if keywords else "an interesting topic"
            template = random.choice(self.video_templates)

            # Generate caption using AI
            caption_prompt = f"Generate a short, punchy TikTok caption for a '{template}' video about '{topic}'. Include a call to action (like, follow, comment). Persona: {self.ai_agent.tone}."
            ai_caption = self.ai_agent.ask(caption_prompt)
            if not ai_caption:
                logger.warning("AI failed to generate caption, using default.")
                default_hashtag = random.choice(self.trending_hashtags) if self.trending_hashtags else 'Tech'
                ai_caption = f"Check out this update on {topic}! What do you think? #AI #Automation #{default_hashtag}"

            # Select relevant hashtags
            num_hashtags = self.config_loader.get_parameter("hashtags_per_post", default=5)
            post_hashtags = []
            if self.trending_hashtags:
                 post_hashtags = random.sample(self.trending_hashtags, min(num_hashtags, len(self.trending_hashtags)))

            # Add keyword-based hashtags if needed
            keyword_hashtags = [kw.lower().replace(' ','') for kw in topic.split() if kw]
            remaining_slots = num_hashtags - len(post_hashtags)
            if remaining_slots > 0:
                 needed_kw_tags = min(remaining_slots, len(keyword_hashtags))
                 post_hashtags.extend(random.sample(keyword_hashtags, needed_kw_tags))

            post_hashtags = list(set(post_hashtags)) # Ensure unique

            logger.info(f"Posting video: {os.path.basename(video_path)} with caption: {ai_caption[:50]}... and hashtags: {post_hashtags}")
            if not self.post_video(video_path, ai_caption, post_hashtags):
                logger.error(f"Failed to post video {i+1}.")
                # Decide whether to continue or abort
            else:
                # Optional: Move or archive posted video
                # archive_dir = os.path.join(video_dir, "posted")
                # os.makedirs(archive_dir, exist_ok=True)
                # shutil.move(video_path, os.path.join(archive_dir, os.path.basename(video_path)))
                # available_videos.remove(video_path) # Remove from list if moved
                pass
            # Use configured wait time between posts
            post_interval_range = self.config_loader.get_parameter("post_interval_wait_range", default=(60, 180))
            self._wait(post_interval_range)

        # --- Community Engagement (Placeholder) ---
        if self.config_loader.get_parameter("enable_engagement", default=False):
            logger.info("--- Starting Community Engagement Phase (Placeholder) ---")
            num_likes = self.config_loader.get_parameter("engagement_likes_per_run", default=10)
            num_follows = self.config_loader.get_parameter("engagement_follows_per_run", default=5)
            # TODO: Implement TikTok engagement (liking comments, following users based on interactions)
            logger.warning(f"{self.PLATFORM.capitalize()} engagement actions (like, follow) are not fully implemented.")
        else:
            logger.info("TikTok engagement is disabled in configuration.")

        # --- Feedback Loop ---
        if self.config_loader.get_parameter("enable_feedback_loop", default=True):
            logger.info("--- Running Feedback Loop ---")
            self.run_feedback_loop()
        else:
            logger.info("Feedback loop is disabled in configuration.")

        logger.info(f"===== Daily {self.PLATFORM.capitalize()} Strategy Session Complete =====")

    def _load_feedback_data(self):
        """Loads feedback data from the JSON file using config path."""
        feedback_db_path = self.config_loader.get_data_path(FEEDBACK_DB)
        logger.debug(f"Loading feedback data from: {feedback_db_path}")
        if os.path.exists(feedback_db_path):
            try:
                with open(feedback_db_path, "r", encoding='utf-8') as f: # Specify encoding
                    return json.load(f)
            except json.JSONDecodeError as json_err:
                 logger.error(f"Error decoding JSON from {feedback_db_path}: {json_err}")
                 return {} # Return empty dict on decode error
            except Exception as e:
                logger.error(f"Error loading feedback data from {feedback_db_path}: {e}")
                return {}
        logger.info(f"Feedback data file not found at {feedback_db_path}, starting fresh.")
        return {}

    def _save_feedback_data(self):
        """Saves feedback data to the JSON file using config path."""
        feedback_db_path = self.config_loader.get_data_path(FEEDBACK_DB)
        logger.debug(f"Saving feedback data to: {feedback_db_path}")
        try:
            os.makedirs(os.path.dirname(feedback_db_path), exist_ok=True)
            with open(feedback_db_path, "w", encoding='utf-8') as f: # Specify encoding
                json.dump(self.feedback_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving feedback data to {feedback_db_path}: {e}")

    def analyze_engagement_metrics(self):
        """
        Analyzes TikTok engagement metrics stored in feedback_data.
        (Placeholder - requires actual data scraping or API/Interaction tracking).
        """
        logger.info(f"Analyzing {self.PLATFORM.capitalize()} engagement metrics (placeholder)...")
        interactions = self.feedback_data.get("interactions", [])
        # Filter interactions related to video feedback if tracked that way
        video_feedback_interactions = [i for i in interactions if i['type'] == 'video_feedback'] # Assumes a specific type for feedback
        num_videos_with_feedback = len(video_feedback_interactions)

        if num_videos_with_feedback > 0:
            # Use specific keys if feedback includes them
            total_views = sum(i['metadata'].get('views', 0) for i in video_feedback_interactions)
            total_likes = sum(i['metadata'].get('likes', 0) for i in video_feedback_interactions)
            total_shares = sum(i['metadata'].get('shares', 0) for i in video_feedback_interactions)
            total_comments = sum(i['metadata'].get('comments', 0) for i in video_feedback_interactions)

            self.feedback_data["avg_views_per_video"] = total_views / num_videos_with_feedback
            self.feedback_data["avg_likes_per_video"] = total_likes / num_videos_with_feedback
            self.feedback_data["avg_shares_per_video"] = total_shares / num_videos_with_feedback
            self.feedback_data["avg_comments_per_video"] = total_comments / num_videos_with_feedback
            # Store totals as well?
            self.feedback_data["total_tracked_views"] = total_views
            self.feedback_data["total_tracked_likes"] = total_likes
            self.feedback_data["total_tracked_shares"] = total_shares
            self.feedback_data["total_tracked_comments"] = total_comments
        else:
             # Reset averages if no feedback data is available for this cycle?
             # Or keep old values? Keeping old for now.
             logger.warning("No video feedback interactions found to update average metrics.")
             pass

        # Update overall sentiment based on comment interactions
        comment_interactions = [i for i in interactions if i['type'] == 'comment_received']
        sentiments = [i['metadata'].get('sentiment') for i in comment_interactions if 'sentiment' in i.get('metadata', {})]
        if sentiments:
            positive_rate = sentiments.count('positive') / len(sentiments)
            negative_rate = sentiments.count('negative') / len(sentiments)
            self.feedback_data["overall_sentiment"] = positive_rate - negative_rate # Simple score range -1 to 1
        else:
             # Keep existing sentiment or default to neutral?
             self.feedback_data.setdefault("overall_sentiment", 0.0)

        logger.info(f"Updated Metrics - Avg Views: {self.feedback_data.get('avg_views_per_video'):.0f}, Avg Likes: {self.feedback_data.get('avg_likes_per_video'):.0f}, Sentiment: {self.feedback_data.get('overall_sentiment'):.2f}")
        self._save_feedback_data()

    def adaptive_posting_strategy(self):
        """
        Adjusts posting strategy based on analyzed feedback (hashtags, templates).
        """
        logger.info(f"Adapting {self.PLATFORM.capitalize()} posting strategy (placeholder)...")
        avg_views = self.feedback_data.get("avg_views_per_video", 0)
        avg_likes = self.feedback_data.get("avg_likes_per_video", 0)
        sentiment = self.feedback_data.get("overall_sentiment", 0.0)

        # Use thresholds from config loader
        high_views_threshold = self.config_loader.get_parameter("engagement_high_threshold_views", 10000)
        low_views_threshold = self.config_loader.get_parameter("engagement_low_threshold_views", 500)
        positive_sentiment_threshold = self.config_loader.get_parameter("positive_sentiment_threshold", 0.1)
        negative_sentiment_threshold = self.config_loader.get_parameter("negative_sentiment_threshold", -0.1)

        if avg_views > high_views_threshold and sentiment > positive_sentiment_threshold:
            logger.info("Feedback positive: High views & good sentiment! Analyze successful video templates and hashtags. Consider increasing frequency.")
            # TODO: Add logic to identify successful templates/hashtags from interaction metadata
        elif avg_views < low_views_threshold or sentiment < negative_sentiment_threshold:
            logger.warning("Feedback indicates low engagement or negative sentiment: Review video quality, templates, hashtag strategy, or posting times.")
            # Example: Suggest trying different video templates or focusing on trending sounds/hashtags
        else:
            logger.info("Engagement metrics are moderate. Maintaining current strategy.")
        # Adapt self.video_templates or suggest hashtag changes based on analysis
        # This requires tracking performance per template/hashtag

    def update_trending_hashtags(self):
        """
        Scrapes or uses an API to find currently trending hashtags on TikTok.
        (Placeholder - requires actual scraping/API logic).
        """
        logger.info(f"Updating trending hashtags for {self.PLATFORM} (placeholder)...")
        # TODO: Implement robust scraping or API call to get trending hashtags
        # Example placeholder logic:
        potential_trends = ["#AIChallenge", "#TechTok", "#AutomationHacks", "#TradingStrategy", "#DevLife", "#FinTech", "#AlgoTrading", "#SystemDesign"]
        num_to_fetch = self.config_loader.get_parameter("trending_hashtags_to_fetch", default=10)
        if potential_trends:
             self.trending_hashtags = random.sample(potential_trends, min(num_to_fetch, len(potential_trends)))
        else:
             self.trending_hashtags = []
        logger.info(f"Captured trending hashtags: {self.trending_hashtags}")
        # Store in feedback data for persistence across runs?
        self.feedback_data["last_hashtag_update"] = datetime.utcnow().isoformat()
        self.feedback_data["captured_trending_hashtags"] = self.trending_hashtags
        self._save_feedback_data()

    def reward_top_creators(self):
        logger.info(f"Evaluating top {self.PLATFORM.capitalize()} creators for rewards (placeholder)...")
        reward_db_path = self.config_loader.get_data_path(REWARD_DB) # Use config loader for path
        # ... logic similar to other platforms using follow_db_path/reward_db_path ...
        # Reward might involve commenting on their video, duet/stitch (complex), or just logging.
        logger.warning(f"Reward logic for {self.PLATFORM} is not implemented.")

    def cross_platform_feedback_loop(self):
        logger.info("Merging cross-platform feedback loops (placeholder)...")
        # TODO: Implement actual merging logic using config loader for paths/params
        # Example: Fetch data from other platform feedback files/DBs
        # twitter_feedback_path = self.config_loader.get_data_path("../twitter/twitter_feedback_tracker.json", platform="twitter")
        # ...

    def run_feedback_loop(self):
        """Runs the analysis and adaptation steps of the feedback loop."""
        logger.info(f"--- Running {self.PLATFORM.capitalize()} Feedback Analysis ---")
        self.analyze_engagement_metrics() # Call updated analysis
        logger.info(f"--- Running {self.PLATFORM.capitalize()} Adaptive Strategy ---")
        self.adaptive_posting_strategy() # Call updated adaptation
        # Add reward logic call here if implemented and enabled in config
        # if self.config_loader.get_parameter("enable_rewards", default=False):
        #    self.reward_top_creators()
        # Add cross-platform call if implemented and enabled
        # if self.config_loader.get_parameter("enable_cross_platform_analysis", default=False):
        #    self.cross_platform_feedback_loop()

# --- Main Execution / Scheduling --- (Optional)
# ... (Main execution block remains the same) ... 
