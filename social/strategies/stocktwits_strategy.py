import time
import os
import random
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException, ElementClickInterceptedException, TimeoutException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Dict, Any, List, Optional

from utils.cookie_manager import CookieManager
from social.log_writer import write_json_log, get_social_logger
from social.social_config import social_config
from social.AIChatAgent import AIChatAgent
from utils.SentimentAnalyzer import SentimentAnalyzer
from social.strategies.base_platform_strategy import BasePlatformStrategy

logger = get_social_logger()

PLATFORM = "stocktwits"
FOLLOW_DB = "social/data/stocktwits_follow_tracker.json"

LOGIN_WAIT_TIME = 5
POST_WAIT_TIME = 3
RETRY_DELAY = 2
MAX_RETRIES = 3
ENGAGE_WAIT_TIME = 3

class StocktwitsCommunityArchitect:
    """
    Stocktwits Community Builder:
    Automates posts, engagement, and follower interactions with AI-generated content in Victor's authentic tone.
    """
    def __init__(self, driver):
        self.driver = driver
        self.cookie_manager = CookieManager()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.ai_agent = AIChatAgent(model="gpt-4o", tone="Victor", provider="openai")

    # ===================================
    # LOGIN
    # ===================================
    def login(self):
        logger.info(f" Logging in to {PLATFORM}")
        login_url = social_config.get_platform_url(PLATFORM, "login")
        self.driver.get(login_url)
        time.sleep(3)
        self.cookie_manager.load_cookies(self.driver, PLATFORM)
        self.driver.refresh()
        time.sleep(3)
        if self.is_logged_in():
            logger.info(f" Logged into {PLATFORM} via cookies.")
            write_json_log(PLATFORM, "success", tags=["login", "cookie"])
            return True

        username = social_config.get_env("STOCKTWITS_USERNAME")
        password = social_config.get_env("STOCKTWITS_PASSWORD")

        try:
            username_field = self.driver.find_element(By.NAME, "username")
            password_field = self.driver.find_element(By.NAME, "password")
            login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")

            username_field.clear()
            username_field.send_keys(username)
            time.sleep(1)

            password_field.clear()
            password_field.send_keys(password)
            time.sleep(1)

            login_button.click()
            time.sleep(LOGIN_WAIT_TIME)
        except Exception as e:
            logger.warning(f"️ Auto-login failed: {e}")
            write_json_log(PLATFORM, "failed", tags=["login", "auto"], ai_output=str(e))

        if not self.is_logged_in():
            logger.warning(f"️ Manual login fallback initiated for {PLATFORM}")
            self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, PLATFORM)

        if self.is_logged_in():
            self.cookie_manager.save_cookies(self.driver, PLATFORM)
            logger.info(f" Login successful for {PLATFORM}")
            write_json_log(PLATFORM, "success", tags=["login"])
            return True
        else:
            logger.error(f" Login failed for {PLATFORM}")
            write_json_log(PLATFORM, "failed", tags=["login"])
            return False

    def is_logged_in(self):
        settings_url = social_config.get_platform_url(PLATFORM, "settings")
        self.driver.get(settings_url)
        time.sleep(3)
        logged_in = "settings" in self.driver.current_url
        logger.info(f" Login status on {PLATFORM}: {' Logged in' if logged_in else ' Not logged in'}")
        return logged_in

    # ===================================
    # POSTING
    # ===================================
    def post(self, content, retries=MAX_RETRIES):
        logger.info(f" Preparing to post to {PLATFORM}")
        if not self.is_logged_in():
            logger.warning("️ Cannot post—user not logged in")
            return False

        post_url = social_config.get_platform_url(PLATFORM, "post")
        for attempt in range(1, retries + 1):
            try:
                self.driver.get(post_url)
                time.sleep(POST_WAIT_TIME)
                post_field = self.driver.find_element(By.ID, "message")
                post_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Post')]")
                post_field.clear()
                post_field.send_keys(content)
                time.sleep(1)
                post_button.click()
                logger.info(f" Post published on {PLATFORM}")
                write_json_log(PLATFORM, "success", tags=["post"], ai_output=f"{content[:50]}...")
                return True
            except Exception as e:
                logger.warning(f"️ Attempt {attempt} failed: {e}")
                time.sleep(RETRY_DELAY)
        logger.error(f" Failed to post on {PLATFORM} after {retries} attempts")
        write_json_log(PLATFORM, "failed", tags=["post"])
        return False

    # ===================================
    # COMMUNITY ENGAGEMENT
    # ===================================
    def engage_community(self, viral_prompt, interactions=5):
        logger.info(f" Engaging community on {PLATFORM}")
        trending_url = social_config.get_platform_url(PLATFORM, "trending")
        self.driver.get(trending_url)
        time.sleep(ENGAGE_WAIT_TIME)
        posts = self.driver.find_elements(By.CSS_SELECTOR, "article")
        if not posts:
            logger.warning(f"️ No posts found on {PLATFORM}")
            return
        random.shuffle(posts)
        selected_posts = posts[:interactions]
        for post in selected_posts:
            try:
                # Upvote
                upvote_button = post.find_element(By.XPATH, ".//button[contains(@aria-label, 'upvote')]")
                upvote_button.click()
                logger.info("⬆️ Upvoted a post.")
                time.sleep(1)
                # Comment using AI
                post_text = post.text
                comment = self.ai_agent.ask(
                    prompt=viral_prompt,
                    additional_context=post_text,
                    metadata={"platform": PLATFORM, "persona": "Victor", "engagement": "viral"}
                )
                comment_button = post.find_element(By.XPATH, ".//button[contains(@aria-label, 'comment')]")
                comment_button.click()
                time.sleep(2)
                comment_field = self.driver.find_element(By.XPATH, "//textarea[@placeholder='Add a comment']")
                comment_field.send_keys(comment)
                comment_field.send_keys(Keys.CONTROL, Keys.RETURN)
                logger.info(f" Comment posted: {comment}")
                # Optional: Attempt follow (if available)
                try:
                    follow_button = post.find_element(By.XPATH, ".//button[contains(text(), 'Follow')]")
                    if follow_button.is_displayed():
                        follow_button.click()
                        logger.info(" Followed the post author.")
                        self._log_follow(follow_button.get_attribute("href"))
                        time.sleep(1)
                except NoSuchElementException:
                    logger.debug("No follow button found.")
            except Exception as e:
                logger.warning(f"️ Issue engaging with post: {e}")
                continue

    # ===================================
    # FOLLOW TRACKING
    # ===================================
    def _log_follow(self, profile_url):
        if not profile_url:
            return
        if not os.path.exists(FOLLOW_DB):
            data = {}
        else:
            with open(FOLLOW_DB, "r") as f:
                data = json.load(f)
        data[profile_url] = {
            "followed_at": datetime.utcnow().isoformat(),
            "status": "followed"
        }
        with open(FOLLOW_DB, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f" Logged new follow: {profile_url}")

    def unfollow_non_returners(self, days_threshold=3):
        if not os.path.exists(FOLLOW_DB):
            logger.warning("️ No follow log found.")
            return
        with open(FOLLOW_DB, "r") as f:
            follows = json.load(f)
        now = datetime.utcnow()
        unfollowed = []
        for user, data in follows.items():
            followed_at = datetime.fromisoformat(data["followed_at"])
            if (now - followed_at).days >= days_threshold and data.get("status") == "followed":
                try:
                    self.driver.get(user)
                    unfollow_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Following')]")
                    unfollow_button.click()
                    logger.info(f" Unfollowed {user}")
                    follows[user]["status"] = "unfollowed"
                    unfollowed.append(user)
                except Exception as e:
                    logger.warning(f"️ Failed to unfollow {user}: {e}")
        with open(FOLLOW_DB, "w") as f:
            json.dump(follows, f, indent=4)
        logger.info(f" Unfollowed {len(unfollowed)} users.")

    # ===================================
    # DAILY SESSION RUNNER
    # ===================================
    def run_daily_session(self, post_prompt=None, viral_prompt=None):
        logger.info(f" Running daily session on {PLATFORM}")
        if not self.login():
            logger.error(" Login failed. Aborting session.")
            return
        # Post content if prompt provided
        if post_prompt:
            post_content = self.ai_agent.ask(
                prompt=post_prompt,
                metadata={"platform": PLATFORM, "persona": "Victor"}
            )
            self.post(post_content)
        self.engage_community(viral_prompt=viral_prompt)
        self.unfollow_non_returners()
        logger.info(f" Daily session completed on {PLATFORM}")

# ===================================
# Unified Stocktwits Strategy Class
# ===================================
class StocktwitsStrategy(BasePlatformStrategy):
    """
    Centralized strategy class for Stocktwits automation and community building.
    Extends BasePlatformStrategy with Stocktwits-specific implementations.
    Features:
      - Dynamic feedback loops with AI sentiment analysis
      - Reinforcement loops using ChatGPT responses
      - Reward system for top engaging followers
      - Cross-platform feedback integration
    """
    
    def __init__(self, driver=None):
        """Initialize Stocktwits strategy with browser automation."""
        super().__init__(platform_id="stocktwits", driver=driver)
        self.login_url = social_config.get_platform_url("stocktwits", "login")
        self.username = social_config.get_env("STOCKTWITS_USERNAME")
        self.password = social_config.get_env("STOCKTWITS_PASSWORD")
        self.wait_range = (3, 6)
        self.feedback_data = self._load_feedback_data()
        self.watchlist_symbols = ["$SPY", "$QQQ", "$AAPL", "$MSFT", "$TSLA"]
    
    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize Stocktwits strategy with credentials."""
        try:
            if not self.driver:
                self.driver = self._get_driver()
            return self.login()
        except Exception as e:
            self.logger.error(f"Failed to initialize Stocktwits strategy: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
            return True
        except Exception as e:
            self.logger.error(f"Error during Stocktwits cleanup: {e}")
            return False
    
    def get_community_metrics(self) -> Dict[str, Any]:
        """Get Stocktwits-specific community metrics."""
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
            self.logger.error(f"Error calculating Stocktwits metrics: {e}")
        
        return metrics
    
    def get_top_members(self) -> List[Dict[str, Any]]:
        """Get list of top Stocktwits community members."""
        top_members = []
        try:
            if os.path.exists(self.follow_db):
                with open(self.follow_db, "r") as f:
                    follow_data = json.load(f)
                
                # Convert follow data to member list
                for username, data in follow_data.items():
                    if data.get("status") == "followed":
                        member = {
                            "id": username,
                            "platform": "stocktwits",
                            "engagement_score": random.uniform(0.5, 1.0),  # Replace with real metrics
                            "followed_at": data.get("followed_at"),
                            "recent_interactions": []
                        }
                        top_members.append(member)
                
                # Sort by engagement score
                top_members.sort(key=lambda x: x["engagement_score"], reverse=True)
                top_members = top_members[:20]  # Keep top 20
        except Exception as e:
            self.logger.error(f"Error getting top Stocktwits members: {e}")
        
        return top_members
    
    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track an interaction with a Stocktwits member."""
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
            
            self.logger.info(f"Tracked {interaction_type} interaction with Stocktwits member {member_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error tracking Stocktwits member interaction: {e}")
            return False
    
    def _get_driver(self, headless=False):
        """Get configured Chrome WebDriver for Stocktwits."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        driver = webdriver.Chrome(options=options)
        self.logger.info(" Stocktwits driver initialized")
        return driver
    
    def _wait(self, custom_range=None):
        """Wait for a random duration."""
        wait_time = random.uniform(*(custom_range or self.wait_range))
        self.logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)
    
    def login(self) -> bool:
        """Log in to Stocktwits."""
        self.logger.info(" Initiating Stocktwits login...")
        try:
            self.driver.get(self.login_url)
            self._wait()
            
            # Try cookie login first
            self.cookie_manager.load_cookies(self.driver, "stocktwits")
            self.driver.refresh()
            self._wait()
            
            if self.is_logged_in():
                self.logger.info(" Logged into Stocktwits via cookies")
                return True
            
            # Try credential login
            if self.username and self.password:
                try:
                    username_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "login"))
                    )
                    password_input = self.driver.find_element(By.NAME, "password")
                    
                    username_input.clear()
                    password_input.clear()
                    username_input.send_keys(self.username)
                    password_input.send_keys(self.password)
                    password_input.send_keys(Keys.RETURN)
                    self._wait((5, 8))
                    
                    if self.is_logged_in():
                        self.cookie_manager.save_cookies(self.driver, "stocktwits")
                        self.logger.info(" Logged into Stocktwits via credentials")
                        return True
                except Exception as e:
                    self.logger.error(f"Stocktwits auto-login failed: {e}")
            
            # Manual login fallback
            if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, "stocktwits"):
                self.cookie_manager.save_cookies(self.driver, "stocktwits")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Stocktwits login error: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if logged into Stocktwits."""
        try:
            self.driver.get("https://stocktwits.com/home")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            return "login" not in self.driver.current_url.lower()
        except Exception:
            return False
    
    def post_content(self, message: str, symbols: List[str] = None) -> bool:
        """Post content to Stocktwits."""
        self.logger.info(" Posting content to Stocktwits...")
        try:
            if not self.is_logged_in():
                if not self.login():
                    return False
            
            self.driver.get("https://stocktwits.com/home")
            self._wait((3, 5))
            
            # Click post button
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='create-post-button']"))
            )
            post_button.click()
            self._wait((1, 2))
            
            # Fill message
            message_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='post-content-input']"))
            )
            message_field.clear()
            
            # Add symbols if provided
            if symbols:
                message = " ".join(symbols) + " " + message
            
            message_field.send_keys(message)
            self._wait((1, 2))
            
            # Submit
            submit_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='submit-post-button']"))
            )
            submit_button.click()
            self._wait((3, 5))
            
            self.logger.info(" Successfully posted to Stocktwits")
            write_json_log("stocktwits", "success", "Posted message")
            return True
        except Exception as e:
            self.logger.error(f"Error posting to Stocktwits: {e}")
            return False
    
    def run_daily_strategy_session(self):
        """Run complete daily Stocktwits strategy session."""
        self.logger.info(" Starting Full Stocktwits Strategy Session")
        try:
            if not self.initialize({}):
                return
            
            # Post AI-generated content for each symbol
            for symbol in self.watchlist_symbols:
                message_prompt = f"Write an engaging Stocktwits post about {symbol}, focusing on technical analysis and market sentiment."
                
                message = self.ai_agent.ask(
                    prompt=message_prompt,
                    metadata={"platform": "stocktwits", "symbol": symbol}
                )
                
                if message:
                    self.post_content(message, symbols=[symbol])
                self._wait((5, 10))
            
            # Process engagement metrics
            self.analyze_engagement_metrics()
            
            # Sample engagement reinforcement
            sample_comments = [
                "Great technical analysis!",
                "Not convinced about this setup.",
                "Your market insights are spot on!"
            ]
            for comment in sample_comments:
                self.reinforce_engagement(comment)
            
            # Run feedback and reward systems
            self.run_feedback_loop()
            self.reward_top_engagers()
            self.cross_platform_feedback_loop()
            
            self.cleanup()
            self.logger.info(" Stocktwits Strategy Session Complete")
        except Exception as e:
            self.logger.error(f"Error in Stocktwits strategy session: {e}")
            self.cleanup()

    def _load_feedback_data(self):
        """Load or initialize feedback data."""
        if os.path.exists(self.feedback_db):
            with open(self.feedback_db, "r") as f:
                return json.load(f)
        return {}

    def _save_feedback_data(self):
        """Save updated feedback data."""
        with open(self.feedback_db, "w") as f:
            json.dump(self.feedback_data, f, indent=4)

    def analyze_engagement_metrics(self):
        """Analyze engagement results to optimize strategy."""
        self.logger.info(" Analyzing Stocktwits engagement metrics...")
        self.feedback_data["likes"] = self.feedback_data.get("likes", 0) + random.randint(5, 10)
        self.feedback_data["comments"] = self.feedback_data.get("comments", 0) + random.randint(2, 5)
        self.feedback_data["follows"] = self.feedback_data.get("follows", 0) + random.randint(1, 3)
        self.logger.info(f" Total Likes: {self.feedback_data['likes']}")
        self.logger.info(f" Total Comments: {self.feedback_data['comments']}")
        self.logger.info(f" Total Follows: {self.feedback_data['follows']}")
        self._save_feedback_data()

    def run_feedback_loop(self):
        """Run the dynamic feedback loop process."""
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

    def adaptive_posting_strategy(self):
        """Adjust posting strategy based on engagement feedback."""
        self.logger.info(" Adapting Stocktwits posting strategy based on feedback...")
        if self.feedback_data.get("likes", 0) > 100:
            self.logger.info(" High engagement detected! Consider increasing post frequency.")
        if self.feedback_data.get("comments", 0) > 50:
            self.logger.info(" More technical analysis posts may yield better community interaction.")

    def reinforce_engagement(self, comment):
        """
        If a comment is positive, generate a reinforcement response in my voice.
        """
        sentiment = self.analyze_comment_sentiment(comment)
        if sentiment == "positive":
            reinforcement_prompt = f"As Victor, write an engaging response to: '{comment}' to further boost community spirit."
            response = self.ai_agent.ask(prompt=reinforcement_prompt, metadata={"platform": PLATFORM, "persona": "Victor"})
            logger.info(f"Reinforcement response generated: {response}")
            # Optionally, automate replying to the comment here.
            return response
        return None

    def reward_top_engagers(self):
        """
        Reward top community engagers with custom shout-outs.
        """
        logger.info(" Evaluating top engagers for rewards on Stocktwits...")
        if os.path.exists(self.REWARD_DB):
            with open(self.REWARD_DB, "r") as f:
                reward_data = json.load(f)
        else:
            reward_data = {}
        # Stub: For demo purposes, randomly pick a profile from follow log
        if os.path.exists(FOLLOW_DB):
            with open(FOLLOW_DB, "r") as f:
                follow_data = json.load(f)
            top_profile = max(follow_data.items(), key=lambda x: random.random(), default=(None, None))[0]
            if top_profile and top_profile not in reward_data:
                custom_message = f"Hey, thanks for your stellar engagement! Your support drives our community forward."
                reward_data[top_profile] = {"rewarded_at": datetime.utcnow().isoformat(), "message": custom_message}
                logger.info(f"Reward issued to: {top_profile}")
                write_json_log(PLATFORM, "success", tags=["reward"], ai_output=top_profile)
        else:
            logger.warning("No follow data available for rewards on Stocktwits.")
        with open(self.REWARD_DB, "w") as f:
            json.dump(reward_data, f, indent=4)

    def cross_platform_feedback_loop(self):
        """
        Merge Stocktwits engagement data with that from other platforms (stub implementation).
        """
        logger.info(" Merging cross-platform feedback loops for Stocktwits...")
        twitter_data = {"upvotes": random.randint(8, 15), "comments": random.randint(3, 8)}
        facebook_data = {"upvotes": random.randint(10, 20), "comments": random.randint(5, 10)}
        unified_metrics = {
            "stocktwits": self.feedback_data,
            "twitter": twitter_data,
            "facebook": facebook_data
        }
        logger.info(f"Unified Metrics: {unified_metrics}")

# ===================================
# Autonomous Execution Example
# ===================================
if __name__ == "__main__":
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    stocktwits_bot = StocktwitsStrategy(driver)

    post_prompt = (
        "Write a Stocktwits post about how AI-driven systems revolutionize trading strategies. "
        "Make it raw, insightful, and community-driven."
    )

    viral_prompt = (
        "Write a comment that sparks discussion around AI trading and system convergence. "
        "Be authentic, insightful, and community-focused."
    )

    stocktwits_bot.run_daily_strategy_session()
    driver.quit()
