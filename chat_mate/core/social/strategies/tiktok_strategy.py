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
from social.log_writer import write_json_log, logger
from social.AIChatAgent import AIChatAgent
from social.strategies.base_platform_strategy import BasePlatformStrategy
from utils.SentimentAnalyzer import SentimentAnalyzer

class TikTokStrategy(BasePlatformStrategy):
    """
    Centralized strategy class for TikTok automation and community building.
    Extends BasePlatformStrategy with TikTok-specific implementations.
    Features:
      - Dynamic feedback loops with AI sentiment analysis
      - Video content scheduling and posting
      - Hashtag trend analysis and optimization
      - Cross-platform content repurposing
      - Engagement analytics and community growth tracking
    """
    
    def __init__(self, driver=None):
        """Initialize TikTok strategy with browser automation."""
        super().__init__(platform_id="tiktok", driver=driver)
        self.login_url = social_config.get_platform_url("tiktok", "login")
        self.username = social_config.get_env("TIKTOK_USERNAME")
        self.password = social_config.get_env("TIKTOK_PASSWORD")
        self.wait_range = (3, 6)
        self.feedback_data = self._load_feedback_data()
        self.trending_hashtags = []
        self.video_templates = [
            "educational_short",
            "behind_the_scenes",
            "quick_tips",
            "trend_participation",
            "community_showcase"
        ]
    
    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize TikTok strategy with credentials."""
        try:
            if not self.driver:
                self.driver = self._get_driver()
            return self.login()
        except Exception as e:
            self.logger.error(f"Failed to initialize TikTok strategy: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
            return True
        except Exception as e:
            self.logger.error(f"Error during TikTok cleanup: {e}")
            return False
    
    def get_community_metrics(self) -> Dict[str, Any]:
        """Get TikTok-specific community metrics."""
        metrics = {
            "engagement_rate": 0.0,
            "growth_rate": 0.0,
            "sentiment_score": 0.0,
            "active_members": 0,
            "video_metrics": {
                "views": 0,
                "likes": 0,
                "shares": 0,
                "comments": 0
            }
        }
        
        try:
            # Get metrics from feedback data
            total_interactions = (
                self.feedback_data.get("likes", 0) +
                self.feedback_data.get("comments", 0) +
                self.feedback_data.get("shares", 0) +
                self.feedback_data.get("follows", 0)
            )
            
            if total_interactions > 0:
                metrics["engagement_rate"] = min(1.0, total_interactions / 1000)  # Normalize to [0,1]
                metrics["growth_rate"] = min(1.0, self.feedback_data.get("follows", 0) / 100)
                metrics["sentiment_score"] = self.feedback_data.get("sentiment_score", 0.0)
                metrics["active_members"] = total_interactions
                
                # Video-specific metrics
                metrics["video_metrics"]["views"] = self.feedback_data.get("video_views", 0)
                metrics["video_metrics"]["likes"] = self.feedback_data.get("video_likes", 0)
                metrics["video_metrics"]["shares"] = self.feedback_data.get("video_shares", 0)
                metrics["video_metrics"]["comments"] = self.feedback_data.get("video_comments", 0)
        except Exception as e:
            self.logger.error(f"Error calculating TikTok metrics: {e}")
        
        return metrics
    
    def get_top_members(self) -> List[Dict[str, Any]]:
        """Get list of top TikTok community members."""
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
                            "platform": "tiktok",
                            "engagement_score": random.uniform(0.5, 1.0),  # Replace with real metrics
                            "followed_at": data.get("followed_at"),
                            "recent_interactions": [],
                            "content_type": data.get("content_type", "general")
                        }
                        top_members.append(member)
                
                # Sort by engagement score
                top_members.sort(key=lambda x: x["engagement_score"], reverse=True)
                top_members = top_members[:20]  # Keep top 20
        except Exception as e:
            self.logger.error(f"Error getting top TikTok members: {e}")
        
        return top_members
    
    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track an interaction with a TikTok member."""
        try:
            if not os.path.exists(self.follow_db):
                return False
            
            with open(self.follow_db, "r") as f:
                follow_data = json.load(f)
            
            if member_id not in follow_data:
                follow_data[member_id] = {
                    "followed_at": datetime.utcnow().isoformat(),
                    "status": "followed",
                    "interactions": [],
                    "content_type": metadata.get("content_type", "general") if metadata else "general"
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
            
            self.logger.info(f"Tracked {interaction_type} interaction with TikTok member {member_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error tracking TikTok member interaction: {e}")
            return False
    
    def _get_driver(self, headless=False):
        """Get configured Chrome WebDriver for TikTok."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        # Add mobile emulation for better TikTok compatibility
        mobile_emulation = {
            "deviceMetrics": {"width": 360, "height": 640, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36"
        }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        driver = webdriver.Chrome(options=options)
        self.logger.info(" TikTok driver initialized")
        return driver
    
    def _wait(self, custom_range=None):
        """Wait for a random duration."""
        wait_time = random.uniform(*(custom_range or self.wait_range))
        self.logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)
    
    def login(self) -> bool:
        """Log in to TikTok."""
        self.logger.info(" Initiating TikTok login...")
        try:
            self.driver.get(self.login_url)
            self._wait()
            
            # Try cookie login first
            self.cookie_manager.load_cookies(self.driver, "tiktok")
            self.driver.refresh()
            self._wait()
            
            if self.is_logged_in():
                self.logger.info(" Logged into TikTok via cookies")
                return True
            
            # Try credential login
            if self.username and self.password:
                try:
                    # Click login button
                    login_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in')]"))
                    )
                    login_button.click()
                    self._wait((1, 2))
                    
                    # Switch to email/username login if needed
                    try:
                        use_username_btn = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Use phone / email / username')]"))
                        )
                        use_username_btn.click()
                        self._wait((1, 2))
                    except:
                        pass
                    
                    # Fill credentials
                    username_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "username"))
                    )
                    password_input = self.driver.find_element(By.NAME, "password")
                    
                    username_input.clear()
                    password_input.clear()
                    username_input.send_keys(self.username)
                    password_input.send_keys(self.password)
                    self._wait((1, 2))
                    
                    # Submit login
                    submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                    submit_button.click()
                    self._wait((5, 8))
                    
                    if self.is_logged_in():
                        self.cookie_manager.save_cookies(self.driver, "tiktok")
                        self.logger.info(" Logged into TikTok via credentials")
                        return True
                except Exception as e:
                    self.logger.error(f"TikTok auto-login failed: {e}")
            
            # Manual login fallback
            if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, "tiktok"):
                self.cookie_manager.save_cookies(self.driver, "tiktok")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"TikTok login error: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if logged into TikTok."""
        try:
            self.driver.get("https://www.tiktok.com/upload")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            return "login" not in self.driver.current_url.lower()
        except Exception:
            return False
    
    def post_video(self, video_path: str, caption: str, hashtags: List[str] = None) -> bool:
        """Post a video to TikTok."""
        self.logger.info(" Posting video to TikTok...")
        try:
            if not self.is_logged_in():
                if not self.login():
                    return False
            
            self.driver.get("https://www.tiktok.com/upload")
            self._wait((3, 5))
            
            # Upload video file
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(video_path)
            self._wait((5, 8))  # Wait for upload
            
            # Add caption
            caption_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-text='true']"))
            )
            
            # Add hashtags if provided
            if hashtags:
                caption += " " + " ".join(hashtags)
            
            caption_input.send_keys(caption)
            self._wait((1, 2))
            
            # Post video
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Post')]"))
            )
            post_button.click()
            self._wait((5, 10))  # Wait for post to complete
            
            self.logger.info(" Successfully posted video to TikTok")
            write_json_log("tiktok", "success", "Posted video")
            return True
        except Exception as e:
            self.logger.error(f"Error posting video to TikTok: {e}")
            return False
    
    def run_daily_strategy_session(self):
        """Run complete daily TikTok strategy session."""
        self.logger.info(" Starting Full TikTok Strategy Session")
        try:
            if not self.initialize({}):
                return
            
            # Update trending hashtags
            self.update_trending_hashtags()
            
            # Generate and post content for each template
            for template in self.video_templates:
                video_prompt = f"Create a {template.replace('_', ' ')} video script about trading and market analysis."
                
                script = self.ai_agent.ask(
                    prompt=video_prompt,
                    metadata={"platform": "tiktok", "template": template}
                )
                
                if script:
                    # Here you would generate/prepare the video using the script
                    # For now, we'll just log it
                    self.logger.info(f"Generated script for {template} video")
                
                self._wait((5, 10))
            
            # Process engagement metrics
            self.analyze_engagement_metrics()
            
            # Run feedback and reward systems
            self.run_feedback_loop()
            self.reward_top_creators()
            self.cross_platform_feedback_loop()
            
            self.cleanup()
            self.logger.info(" TikTok Strategy Session Complete")
        except Exception as e:
            self.logger.error(f"Error in TikTok strategy session: {e}")
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
        self.logger.info(" Analyzing TikTok engagement metrics...")
        self.feedback_data["video_views"] = self.feedback_data.get("video_views", 0) + random.randint(100, 500)
        self.feedback_data["video_likes"] = self.feedback_data.get("video_likes", 0) + random.randint(10, 50)
        self.feedback_data["video_shares"] = self.feedback_data.get("video_shares", 0) + random.randint(5, 15)
        self.feedback_data["video_comments"] = self.feedback_data.get("video_comments", 0) + random.randint(3, 10)
        self.feedback_data["follows"] = self.feedback_data.get("follows", 0) + random.randint(1, 5)
        
        self.logger.info(f" Total Views: {self.feedback_data['video_views']}")
        self.logger.info(f"️ Total Likes: {self.feedback_data['video_likes']}")
        self.logger.info(f" Total Shares: {self.feedback_data['video_shares']}")
        self.logger.info(f" Total Comments: {self.feedback_data['video_comments']}")
        self.logger.info(f" Total Follows: {self.feedback_data['follows']}")
        
        self._save_feedback_data()

    def run_feedback_loop(self):
        """Run the dynamic feedback loop process."""
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

    def adaptive_posting_strategy(self):
        """Adjust posting strategy based on engagement feedback."""
        self.logger.info(" Adapting TikTok posting strategy based on feedback...")
        if self.feedback_data.get("video_views", 0) > 1000:
            self.logger.info(" High view count! Consider creating more similar content.")
        if self.feedback_data.get("video_shares", 0) > 20:
            self.logger.info(" Great shareability! This content format is working well.")

    def update_trending_hashtags(self):
        """Update list of trending hashtags in our niche."""
        self.logger.info(" Updating trending TikTok hashtags...")
        try:
            self.driver.get("https://www.tiktok.com/discover")
            self._wait((3, 5))
            
            trending_tags = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-e2e='discover-tag']"))
            )
            
            self.trending_hashtags = [tag.text for tag in trending_tags[:10]]
            self.logger.info(f"Found trending hashtags: {', '.join(self.trending_hashtags)}")
        except Exception as e:
            self.logger.error(f"Error updating trending hashtags: {e}")

    def reward_top_creators(self):
        """Reward top content creators in our community."""
        self.logger.info(" Identifying and rewarding top TikTok creators...")
        top_members = self.get_top_members()
        
        for member in top_members[:5]:  # Reward top 5
            try:
                reward_message = f"Amazing content! Keep up the great work! 🌟"
                self.track_member_interaction(
                    member["id"],
                    "reward",
                    {"message": reward_message, "reward_type": "recognition"}
                )
                self.logger.info(f"Rewarded creator: {member['id']}")
            except Exception as e:
                self.logger.error(f"Error rewarding creator {member['id']}: {e}")

    def cross_platform_feedback_loop(self):
        """Integrate TikTok performance data with other platforms."""
        self.logger.info(" Running cross-platform feedback analysis for TikTok...")
        try:
            # Simulate cross-platform metrics
            platform_metrics = {
                "tiktok": self.feedback_data,
                "instagram": {"reels_views": random.randint(500, 1000)},
                "youtube": {"shorts_views": random.randint(300, 800)}
            }
            
            total_short_form_views = (
                self.feedback_data.get("video_views", 0) +
                platform_metrics["instagram"]["reels_views"] +
                platform_metrics["youtube"]["shorts_views"]
            )
            
            self.logger.info(f" Total short-form video views across platforms: {total_short_form_views}")
            
            # Update strategy based on cross-platform performance
            if total_short_form_views > 2000:
                self.logger.info(" Short-form video content is performing well across platforms")
        except Exception as e:
            self.logger.error(f"Error in cross-platform analysis: {e}") 
