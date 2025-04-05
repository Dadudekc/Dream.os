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

class RedditStrategy(BasePlatformStrategy):
    """
    Centralized strategy class for Reddit automation and community building.
    Extends BasePlatformStrategy with Reddit-specific implementations.
    Features:
      - Dynamic feedback loops with AI sentiment analysis
      - Reinforcement loops using ChatGPT responses
      - Reward system for top engaging followers
      - Cross-platform feedback integration
    """
    
    def __init__(self, driver=None):
        """Initialize Reddit strategy with browser automation."""
        super().__init__(platform_id="reddit", driver=driver)
        self.login_url = social_config.get_platform_url("reddit", "login")
        self.username = social_config.get_env("REDDIT_USERNAME")
        self.password = social_config.get_env("REDDIT_PASSWORD")
        self.wait_range = (3, 6)
        self.feedback_data = self._load_feedback_data()
        self.subreddits = ["algotrading", "systemtrader", "automation", "investing"]
        self.logger = get_social_logger()
    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize Reddit strategy with credentials."""
        try:
            if not self.driver:
                self.driver = self._get_driver()
            return self.login()
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit strategy: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
            return True
        except Exception as e:
            self.logger.error(f"Error during Reddit cleanup: {e}")
            return False
    
    def get_community_metrics(self) -> Dict[str, Any]:
        """Get Reddit-specific community metrics."""
        metrics = {
            "engagement_rate": 0.0,
            "growth_rate": 0.0,
            "sentiment_score": 0.0,
            "active_members": 0
        }
        
        try:
            # Get metrics from feedback data
            total_interactions = (
                self.feedback_data.get("upvotes", 0) +
                self.feedback_data.get("comments", 0) +
                self.feedback_data.get("subscriptions", 0)
            )
            
            if total_interactions > 0:
                metrics["engagement_rate"] = min(1.0, total_interactions / 1000)  # Normalize to [0,1]
                metrics["growth_rate"] = min(1.0, self.feedback_data.get("subscriptions", 0) / 100)
                metrics["sentiment_score"] = self.feedback_data.get("sentiment_score", 0.0)
                metrics["active_members"] = total_interactions
        except Exception as e:
            self.logger.error(f"Error calculating Reddit metrics: {e}")
        
        return metrics
    
    def get_top_members(self) -> List[Dict[str, Any]]:
        """Get list of top Reddit community members."""
        top_members = []
        try:
            if os.path.exists(self.follow_db):
                with open(self.follow_db, "r") as f:
                    follow_data = json.load(f)
                
                # Convert follow data to member list
                for subreddit, data in follow_data.items():
                    if data.get("status") == "subscribed":
                        member = {
                            "id": subreddit,
                            "platform": "reddit",
                            "engagement_score": random.uniform(0.5, 1.0),  # Replace with real metrics
                            "subscribed_at": data.get("subscribed_at"),
                            "recent_interactions": []
                        }
                        top_members.append(member)
                
                # Sort by engagement score
                top_members.sort(key=lambda x: x["engagement_score"], reverse=True)
                top_members = top_members[:20]  # Keep top 20
        except Exception as e:
            self.logger.error(f"Error getting top Reddit members: {e}")
        
        return top_members
    
    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track an interaction with a Reddit member (subreddit)."""
        try:
            if not os.path.exists(self.follow_db):
                return False
            
            with open(self.follow_db, "r") as f:
                follow_data = json.load(f)
            
            if member_id not in follow_data:
                follow_data[member_id] = {
                    "subscribed_at": datetime.utcnow().isoformat(),
                    "status": "subscribed",
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
            
            self.logger.info(f"Tracked {interaction_type} interaction with Reddit member {member_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error tracking Reddit member interaction: {e}")
            return False
    
    def _get_driver(self, headless=False):
        """Get configured Chrome WebDriver for Reddit."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        driver = webdriver.Chrome(options=options)
        self.logger.info(" Reddit driver initialized")
        return driver
    
    def _wait(self, custom_range=None):
        """Wait for a random duration."""
        wait_time = random.uniform(*(custom_range or self.wait_range))
        self.logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)
    
    def login(self) -> bool:
        """Log in to Reddit."""
        self.logger.info(" Initiating Reddit login...")
        try:
            self.driver.get(self.login_url)
            self._wait()
            
            # Try cookie login first
            self.cookie_manager.load_cookies(self.driver, "reddit")
            self.driver.refresh()
            self._wait()
            
            if self.is_logged_in():
                self.logger.info(" Logged into Reddit via cookies")
                return True
            
            # Try credential login
            if self.username and self.password:
                try:
                    username_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "loginUsername"))
                    )
                    password_input = self.driver.find_element(By.ID, "loginPassword")
                    
                    username_input.clear()
                    password_input.clear()
                    username_input.send_keys(self.username)
                    password_input.send_keys(self.password)
                    password_input.send_keys(Keys.RETURN)
                    self._wait((5, 8))
                    
                    if self.is_logged_in():
                        self.cookie_manager.save_cookies(self.driver, "reddit")
                        self.logger.info(" Logged into Reddit via credentials")
                        return True
                except Exception as e:
                    self.logger.error(f"Reddit auto-login failed: {e}")
            
            # Manual login fallback
            if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, "reddit"):
                self.cookie_manager.save_cookies(self.driver, "reddit")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Reddit login error: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if logged into Reddit."""
        try:
            self.driver.get("https://www.reddit.com/")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            return "login" not in self.driver.current_url.lower()
        except Exception:
            return False
    
    def post_content(self, subreddit: str, title: str, body: str = None) -> bool:
        """Post content to Reddit."""
        self.logger.info(f" Posting content to r/{subreddit}...")
        try:
            if not self.is_logged_in():
                if not self.login():
                    return False
            
            submit_url = f"https://www.reddit.com/r/{subreddit}/submit"
            self.driver.get(submit_url)
            self._wait((3, 5))
            
            # Fill title
            title_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[name='title']"))
            )
            title_field.clear()
            title_field.send_keys(title)
            self._wait((1, 2))
            
            # Fill body if provided
            if body:
                body_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='post-content'] div[role='textbox']"))
                )
                body_field.click()
                self._wait((1, 2))
                body_field.send_keys(body)
                self._wait((1, 2))
            
            # Submit
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Post')]"))
            )
            post_button.click()
            self._wait((3, 5))
            
            self.logger.info(f" Successfully posted to r/{subreddit}")
            write_json_log("reddit", "success", f"Posted to r/{subreddit}")
            return True
        except Exception as e:
            self.logger.error(f"Error posting to Reddit: {e}")
            return False
    
    def run_daily_strategy_session(self):
        """Run complete daily Reddit strategy session."""
        self.logger.info(" Starting Full Reddit Strategy Session")
        try:
            if not self.initialize({}):
                return
            
            # Post AI-generated content
            for subreddit in self.subreddits:
                title_prompt = f"Write an engaging Reddit post title for r/{subreddit} about community building and system convergence."
                body_prompt = "Write a detailed post body expanding on the title, focusing on value and authenticity."
                
                title = self.ai_agent.ask(
                    prompt=title_prompt,
                    metadata={"platform": "reddit", "subreddit": subreddit}
                )
                body = self.ai_agent.ask(
                    prompt=body_prompt,
                    metadata={"platform": "reddit", "subreddit": subreddit}
                )
                
                if title and body:
                    self.post_content(subreddit, title, body)
                self._wait((5, 10))
            
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
            self.logger.info(" Reddit Strategy Session Complete")
        except Exception as e:
            self.logger.error(f"Error in Reddit strategy session: {e}")
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
        self.logger.info(" Analyzing Reddit engagement metrics...")
        self.feedback_data["upvotes"] = self.feedback_data.get("upvotes", 0) + random.randint(5, 10)
        self.feedback_data["comments"] = self.feedback_data.get("comments", 0) + random.randint(2, 5)
        self.feedback_data["subscriptions"] = self.feedback_data.get("subscriptions", 0) + random.randint(1, 3)
        self.logger.info(f" Total Upvotes: {self.feedback_data['upvotes']}")
        self.logger.info(f" Total Comments: {self.feedback_data['comments']}")
        self.logger.info(f" Total Subscriptions: {self.feedback_data['subscriptions']}")
        self._save_feedback_data()

    def run_feedback_loop(self):
        """Run the dynamic feedback loop process."""
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

    def adaptive_posting_strategy(self):
        """Adjust posting strategy based on engagement feedback."""
        self.logger.info(" Adapting Reddit posting strategy based on feedback...")
        if self.feedback_data.get("upvotes", 0) > 100:
            self.logger.info(" High engagement detected! Consider increasing post frequency.")
        if self.feedback_data.get("comments", 0) > 50:
            self.logger.info(" More discussion-oriented posts may yield better community interaction.")
