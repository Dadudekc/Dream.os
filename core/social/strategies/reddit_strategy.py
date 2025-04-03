import os
import time
import random
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    TimeoutException
)

from social.strategies.base_platform_strategy import BasePlatformStrategy
from utils.cookie_manager import CookieManager
from social.log_writer import get_social_logger, write_json_log
from social.social_config import social_config
from social.AIChatAgent import AIChatAgent
from utils.SentimentAnalyzer import SentimentAnalyzer
from .strategy_config_loader import StrategyConfigLoader

logger = get_social_logger()

# Define constants
PLATFORM = "reddit"
FEEDBACK_DB = "social/data/reddit_feedback_tracker.json"
REWARD_DB = "social/data/reddit_reward_tracker.json"
FOLLOW_DB = "social/data/reddit_follow_tracker.json"

class RedditStrategy(BasePlatformStrategy):
    """
    Centralized strategy class for Reddit automation and community building,
    leveraging StrategyConfigLoader.
    Extends BasePlatformStrategy with Reddit-specific implementations.
    Features:
      - Dynamic feedback loops with AI sentiment analysis
      - Reinforcement loops using ChatGPT responses
      - Reward system for top engaging users/subreddits
      - Cross-platform feedback integration (stubbed)
    """
    PLATFORM = PLATFORM

    def __init__(self, driver=None):
        """Initialize Reddit strategy using StrategyConfigLoader."""
        super().__init__(platform_id=self.PLATFORM, driver=driver)
        self.config_loader = StrategyConfigLoader(platform=self.PLATFORM)
        self.ai_agent = AIChatAgent(
            model=self.config_loader.get_parameter("ai_model", "gpt-4o"),
            tone=self.config_loader.get_parameter("ai_comment_tone", "Victor"),
            provider=self.config_loader.get_parameter("ai_provider", "openai")
        )
        self.cookie_manager = CookieManager()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.feedback_data = self._load_feedback_data()
        self.username = None
        self.password = None
        self.subreddits = self.config_loader.get_parameter("target_subreddits", default=["algotrading", "systemtrader", "automation"])
        self.follow_db_path = self.config_loader.get_data_path(FOLLOW_DB)

    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize Reddit strategy with credentials from secure source."""
        logger.info(f"Initializing {self.PLATFORM.capitalize()}Strategy...")
        self.username = credentials.get("username")
        self.password = credentials.get("password")
        if not self.username or not self.password:
            logger.error(f"{self.PLATFORM.capitalize()} credentials (username, password) not provided.")
            return False
        try:
            if not self.driver:
                logger.info("No driver provided, initializing default driver.")
                self.driver = super()._get_driver()
            return self.login()
        except Exception as e:
            logger.error(f"Failed to initialize {self.PLATFORM.capitalize()} strategy: {e}", exc_info=True)
            return False

    def cleanup(self) -> bool:
        """Clean up resources (driver)."""
        logger.info(f"Cleaning up {self.PLATFORM.capitalize()}Strategy resources...")
        return super().cleanup()

    def get_community_metrics(self) -> Dict[str, Any]:
        """Get Reddit-specific community metrics using feedback data and config."""
        logger.info(f"Retrieving {self.PLATFORM.capitalize()} community metrics...")
        metrics = {
            "platform": self.PLATFORM,
            "engagement_rate_estimate": self.config_loader.get_parameter("estimated_engagement_rate", default=0.8),
            "target_subreddits": self.subreddits,
            "current_post_frequency": self.config_loader.get_parameter("post_frequency_per_day", default=1),
            "active_members_estimate": 0,
            "sentiment_score": self.feedback_data.get("overall_sentiment", 0.5)
        }

        try:
            total_interactions = (
                self.feedback_data.get("upvotes_received", 0) +
                self.feedback_data.get("comments_received", 0) +
                self.feedback_data.get("posts_made", 0)
            )
            metrics["active_members_estimate"] = total_interactions
        except Exception as e:
            logger.error(f"Error calculating {self.PLATFORM.capitalize()} metrics: {e}")

        logger.debug(f"{self.PLATFORM.capitalize()} Metrics: {metrics}")
        return metrics

    def get_top_members(self) -> List[Dict[str, Any]]:
        """
        Get list of top Reddit community members/subreddits based on tracking data.
        (Placeholder - requires robust interaction tracking).
        """
        logger.info(f"Identifying top {self.PLATFORM.capitalize()} members/subreddits (placeholder)...")
        top_members = []
        if os.path.exists(self.follow_db_path):
            try:
                with open(self.follow_db_path, "r") as f:
                    follow_data = json.load(f)

                for member_id, data in follow_data.items():
                    interactions = data.get("interactions", [])
                    engagement_score = len(interactions)
                    member = {
                        "id": member_id,
                        "platform": self.PLATFORM,
                        "engagement_score": engagement_score,
                        "type": data.get("type", "unknown"),
                        "last_interaction": interactions[-1]["timestamp"] if interactions else data.get("tracked_at")
                    }
                    top_members.append(member)

                top_members.sort(key=lambda x: x["engagement_score"], reverse=True)
                top_members = top_members[:self.config_loader.get_parameter("top_members_count", 20)]

            except Exception as e:
                logger.error(f"Error processing follow data from {self.follow_db_path}: {e}")
        else:
            logger.info(f"Follow tracker file not found at {self.follow_db_path}. Cannot determine top members.")

        return top_members

    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Track an interaction with a Reddit user or subreddit.
        Logs interaction to the follow/interaction tracking file.
        """
        logger.info(f"Tracking {self.PLATFORM.capitalize()} interaction: Member/Sub={member_id}, Type={interaction_type}")
        try:
            if os.path.exists(self.follow_db_path):
                with open(self.follow_db_path, "r") as f:
                    follow_data = json.load(f)
            else:
                follow_data = {}

            if member_id not in follow_data:
                follow_data[member_id] = {
                    "tracked_at": datetime.utcnow().isoformat(),
                    "type": metadata.get("member_type", "unknown") if metadata else "unknown",
                    "status": "active",
                    "interactions": []
                }

            interaction = {
                "type": interaction_type,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            follow_data[member_id].setdefault("interactions", []).append(interaction)

            os.makedirs(os.path.dirname(self.follow_db_path), exist_ok=True)
            with open(self.follow_db_path, "w") as f:
                json.dump(follow_data, f, indent=4)

            logger.debug(f"Interaction tracked for {member_id}.")
            return True
        except Exception as e:
            logger.error(f"Error tracking {self.PLATFORM.capitalize()} member interaction for {member_id}: {e}")
            return False

    def _get_driver(self, headless=False):
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
        """Log in to Reddit using credentials and cookies."""
        logger.info(f"Initiating login process for {self.PLATFORM}.")
        if not self._get_driver():
            logger.error("Cannot login: WebDriver is not initialized.")
            return False
        if not self.username or not self.password:
            logger.error("Cannot login: Username or password not set.")
            return False

        login_url = self.config_loader.get_platform_url("login")
        base_url = self.config_loader.get_platform_url("base")
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=15)

        try:
            self.driver.get(login_url)
            self._wait()
            self.cookie_manager.load_cookies(self.driver, self.PLATFORM)
            self.driver.refresh()
            self._wait()

            if self.is_logged_in():
                logger.info(f"Logged into {self.PLATFORM} via cookies or existing session.")
                write_json_log(self.PLATFORM, "successful", tags=["cookie_login"])
                return True

            logger.info("Cookie/Session login failed. Attempting credential login.")
            self.driver.get(login_url)
            self._wait()

            try:
                iframe = WebDriverWait(self.driver, default_wait).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                self.driver.switch_to.frame(iframe)
                logger.debug("Switched to login iframe.")
            except TimeoutException:
                logger.debug("No login iframe detected, proceeding on main page.")
                self.driver.switch_to.default_content()

            username_input = WebDriverWait(self.driver, default_wait).until(
                EC.visibility_of_element_located((By.ID, "loginUsername"))
            )
            password_input = self.driver.find_element(By.ID, "loginPassword")
            username_input.clear()
            password_input.clear()
            username_input.send_keys(self.username)
            password_input.send_keys(self.password)
            login_button = WebDriverWait(self.driver, default_wait).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            login_button.click()
            logger.info(f"Submitted credentials for {self.PLATFORM}.")
            self.driver.switch_to.default_content()
            self._wait((5, 10))

            if self.is_logged_in():
                logger.info(f"Logged in successfully to {self.PLATFORM} using credentials.")
                self.cookie_manager.save_cookies(self.driver, self.PLATFORM)
                write_json_log(self.PLATFORM, "successful", tags=["credential_login"])
                return True
            else:
                logger.error(f"Credential login failed for {self.PLATFORM}.")
                write_json_log(self.PLATFORM, "failed", tags=["credential_login"], ai_output="Login verification failed after credential submission.")
                return False

        except Exception as e:
            logger.error(f"Error during {self.PLATFORM} login: {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["login_error"], ai_output=str(e))
            try:
                self.driver.switch_to.default_content()
            except: pass
            return False

    def is_logged_in(self) -> bool:
        """Check if logged into Reddit more reliably."""
        if not self.driver:
            return False
        base_url = self.config_loader.get_platform_url("base")
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=5)
        try:
            current_url = self.driver.current_url
            if "reddit.com" not in current_url:
                self.driver.get(base_url)
                self._wait((2,4))
            elif "login" in current_url:
                return False

            profile_indicator_xpath = "//button[contains(@aria-label, 'User account')] | //a[contains(@href, '/user/')]/span"
            WebDriverWait(self.driver, default_wait).until(
                EC.presence_of_element_located((By.XPATH, profile_indicator_xpath))
            )
            logger.debug(f"{self.PLATFORM} login confirmed via profile indicator.")
            return True
        except (TimeoutException, NoSuchElementException):
            logger.debug(f"{self.PLATFORM} login check failed (profile indicator not found).")
            return False
        except Exception as e:
            logger.warning(f"Error during {self.PLATFORM} login check: {e}")
            return False

    def post_content(self, subreddit: str, title: str, body: str = None) -> bool:
        """
        Post content (text or link) to a specific subreddit.
        """
        logger.info(f"Attempting to post to r/{subreddit} on {self.PLATFORM}.")
        if not self.is_logged_in():
            logger.warning("Not logged in. Attempting login before posting...")
            if not self.login():
                write_json_log(self.PLATFORM, "failed", tags=["post", "login_required"], ai_output="Login failed before posting.")
                return False

        submit_url = f"{self.config_loader.get_platform_url('base')}/r/{subreddit}/submit"
        default_wait = self.config_loader.get_parameter("default_selenium_wait", default=15)

        try:
            self.driver.get(submit_url)
            self._wait((3, 5))

            title_textarea_xpath = "//textarea[@placeholder='Title']"
            title_field = WebDriverWait(self.driver, default_wait).until(
                EC.element_to_be_clickable((By.XPATH, title_textarea_xpath))
            )
            title_field.send_keys(title)
            logger.debug("Entered post title.")
            self._wait((0.5, 1.5))

            if body:
                body_editor_xpath = "//div[@role='textbox' and contains(@class, 'richtext')]"
                body_field = WebDriverWait(self.driver, default_wait).until(
                    EC.visibility_of_element_located((By.XPATH, body_editor_xpath))
                )
                body_field.click()
                body_field.send_keys(body)
                logger.debug("Entered post body.")
                self._wait((1, 3))

            post_button_xpath = "//button[normalize-space()='Post']"
            post_button = WebDriverWait(self.driver, default_wait).until(
                EC.element_to_be_clickable((By.XPATH, post_button_xpath))
            )
            post_button.click()
            logger.info(f"Post submitted to r/{subreddit}.")
            self._wait((5, 10))

            logger.info(f"Content posted successfully to r/{subreddit}.")
            write_json_log(self.PLATFORM, "successful", tags=["post", f"subreddit:{subreddit}"], details=title)
            self.track_member_interaction(subreddit, "post_made", {"title": title, "body_length": len(body or "")})
            return True

        except Exception as e:
            logger.error(f"Failed to post to r/{subreddit}: {e}", exc_info=True)
            write_json_log(self.PLATFORM, "failed", tags=["post", f"subreddit:{subreddit}", "error"], ai_output=str(e))
            return False

    def run_daily_strategy_session(self):
        """
        Executes the full daily strategy for Reddit.
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

        post_freq = self.config_loader.get_parameter("post_frequency_per_day", default=1)
        keywords = self.config_loader.get_parameter("targeting_keywords", default=["trading systems", "automation tools", "market analysis"])
        target_subreddits = self.config_loader.get_parameter("target_subreddits", default=self.subreddits)

        logger.info(f"Session Config: Post Freq={post_freq}, Subreddits={target_subreddits}, Keywords={keywords}")

        for i in range(post_freq):
            logger.info(f"--- Preparing Post {i+1}/{post_freq} ---")
            subreddit = random.choice(target_subreddits)
            topic = random.choice(keywords) if keywords else "a relevant topic"

            title_prompt = f"Generate a compelling, concise Reddit post title about '{topic}' suitable for r/{subreddit}. Persona: Victor."
            body_prompt = f"Generate an insightful Reddit post body discussing '{topic}' for r/{subreddit}. Keep it engaging and encourage discussion. Include relevant details but be concise. Persona: Victor."

            ai_title = self.ai_agent.ask(title_prompt)
            ai_body = self.ai_agent.ask(body_prompt)

            if ai_title and ai_body:
                logger.info(f"Posting content about '{topic}' to r/{subreddit}...")
                if not self.post_content(subreddit, ai_title, ai_body):
                    logger.error(f"Failed to post content piece {i+1} to r/{subreddit}.")
            else:
                logger.warning(f"AI failed to generate title or body for '{topic}' in r/{subreddit}.")
            self._wait()

        if self.config_loader.get_parameter("enable_engagement", default=False):
            logger.info("--- Starting Community Engagement Phase (Placeholder) ---")
            num_comments = self.config_loader.get_parameter("engagement_comments_per_run", default=5)
            num_upvotes = self.config_loader.get_parameter("engagement_upvotes_per_run", default=10)
            ai_tone = self.config_loader.get_parameter("ai_comment_tone", default="Victor")
            self.ai_agent.tone = ai_tone

            logger.warning(f"Reddit engagement (commenting/upvoting) is not fully implemented.")

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
                with open(feedback_db_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading feedback data from {feedback_db_path}: {e}")
                return {}
        return {}

    def _save_feedback_data(self):
        """Saves feedback data to the JSON file using config path."""
        feedback_db_path = self.config_loader.get_data_path(FEEDBACK_DB)
        logger.debug(f"Saving feedback data to: {feedback_db_path}")
        try:
            os.makedirs(os.path.dirname(feedback_db_path), exist_ok=True)
            with open(feedback_db_path, "w") as f:
                json.dump(self.feedback_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving feedback data: {e}")

    def analyze_engagement_metrics(self):
        """
        Analyzes Reddit engagement metrics stored in feedback_data.
        (Placeholder - requires actual data scraping or API usage).
        """
        logger.info(f"Analyzing {self.PLATFORM.capitalize()} engagement metrics (placeholder)...")
        interactions = self.feedback_data.get("interactions", [])
        karma_estimate = self.feedback_data.get("estimated_karma", 0)

        sentiments = [i['metadata'].get('sentiment') for i in interactions if 'sentiment' in i.get('metadata', {})]
        if sentiments:
            positive_rate = sentiments.count('positive') / len(sentiments)
            negative_rate = sentiments.count('negative') / len(sentiments)
            self.feedback_data["overall_sentiment"] = positive_rate - negative_rate

        self.feedback_data["estimated_karma"] = karma_estimate
        logger.info(f"Updated Metrics - Est. Karma: {karma_estimate}, Sentiment: {self.feedback_data.get('overall_sentiment'):.2f}")
        self._save_feedback_data()

    def adaptive_posting_strategy(self):
        """
        Adjusts posting strategy based on analyzed feedback.
        (Placeholder - requires linking metrics to strategy changes).
        """
        logger.info(f"Adapting {self.PLATFORM.capitalize()} posting strategy (placeholder)...")
        karma = self.feedback_data.get("estimated_karma", 0)
        sentiment = self.feedback_data.get("overall_sentiment", 0.0)

        high_karma_threshold = self.config_loader.get_parameter("engagement_high_threshold_karma", 100)
        low_karma_threshold = self.config_loader.get_parameter("engagement_low_threshold_karma", 10)

        if karma > high_karma_threshold and sentiment > 0.2:
            logger.info("Feedback positive: Consider posting to more niche subreddits or increasing interaction.")

        elif karma < low_karma_threshold or sentiment < -0.2:
            logger.warning("Feedback indicates low engagement/negative sentiment: Review content quality, subreddit choice, or tone.")

    def analyze_comment_sentiment(self, comment: str) -> str:
        """Analyzes sentiment using the dedicated SentimentAnalyzer."""
        return self.sentiment_analyzer.analyze(comment)

    def reinforce_engagement(self, comment: str, comment_author: str, post_id: str):
        """Generates and potentially posts a reinforcing reply to a positive comment on Reddit."""
        sentiment = self.analyze_comment_sentiment(comment)
        if sentiment == "positive":
            logger.info(f"Positive Reddit comment by {comment_author}. Generating reinforcement...")
            reinforcement_prompt = f"As Victor, write a brief, relevant, and appreciative reply to this positive Reddit comment on post {post_id}: '{comment}'"
            reply = self.ai_agent.ask(prompt=reinforcement_prompt, metadata={"platform": self.PLATFORM, "persona": "Victor", "task": "reinforce_engagement"})
            if reply:
                logger.info(f"Generated reinforcement reply for Reddit: {reply}")
                self.track_member_interaction(comment_author, "positive_comment_received", {"comment": comment, "intended_reply": reply, "post_id": post_id})
                return reply
            else:
                logger.warning("AI failed to generate reinforcement reply.")
        else:
            logger.debug(f"Reddit comment sentiment ({sentiment}) does not warrant reinforcement.")
        return None

    def run_feedback_loop(self):
        """Runs the analysis and adaptation steps of the feedback loop."""
        logger.info(f"--- Running {self.PLATFORM.capitalize()} Feedback Analysis ---")
        self.analyze_engagement_metrics()
        logger.info(f"--- Running {self.PLATFORM.capitalize()} Adaptive Strategy ---")
        self.adaptive_posting_strategy()

if __name__ == "__main__":
    print(f"Running {PLATFORM.capitalize()}Strategy directly for testing...")
    strategy = RedditStrategy()
    creds = {
        "username": social_config.get_env("REDDIT_USERNAME"),
        "password": social_config.get_env("REDDIT_PASSWORD")
    }
    if strategy.initialize(creds):
        print("Strategy initialized.")
        if strategy.is_logged_in():
            print("Login successful.")
            strategy.run_daily_strategy_session()
        else:
            print("Login failed. Aborting test.")
    else:
        print("Strategy initialization failed.")

    strategy.cleanup()
    print(f"{PLATFORM.capitalize()}Strategy direct test finished.")
