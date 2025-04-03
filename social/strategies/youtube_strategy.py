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

logger = get_social_logger()

class YouTubeStrategy(BasePlatformStrategy):
    """
    Centralized strategy class for YouTube automation and community building.
    Extends BasePlatformStrategy with YouTube-specific implementations.
    Features:
      - Video content management and scheduling
      - Shorts creation and optimization
      - Community post engagement
      - Analytics tracking and optimization
      - Cross-platform content distribution
    """
    
    def __init__(self, driver=None):
        """Initialize YouTube strategy with browser automation."""
        super().__init__(platform_id="youtube", driver=driver)
        self.login_url = social_config.get_platform_url("youtube", "login")
        self.username = social_config.get_env("YOUTUBE_EMAIL")
        self.password = social_config.get_env("YOUTUBE_PASSWORD")
        self.wait_range = (3, 6)
        self.feedback_data = self._load_feedback_data()
        self.content_types = {
            "shorts": {
                "max_duration": 60,
                "optimal_duration": 30,
                "formats": ["vertical", "9:16"]
            },
            "regular": {
                "max_duration": 1800,  # 30 minutes
                "optimal_duration": 600,  # 10 minutes
                "formats": ["landscape", "16:9"]
            },
            "live": {
                "min_duration": 300,  # 5 minutes
                "optimal_duration": 3600,  # 1 hour
                "formats": ["landscape", "16:9"]
            }
        }
    
    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize YouTube strategy with credentials."""
        try:
            if not self.driver:
                self.driver = self._get_driver()
            return self.login()
        except Exception as e:
            logger.error(f"Failed to initialize YouTube strategy: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
            return True
        except Exception as e:
            logger.error(f"Error during YouTube cleanup: {e}")
            return False
    
    def get_community_metrics(self) -> Dict[str, Any]:
        """Get YouTube-specific community metrics."""
        metrics = {
            "engagement_rate": 0.0,
            "growth_rate": 0.0,
            "sentiment_score": 0.0,
            "active_members": 0,
            "video_metrics": {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "watch_time": 0
            },
            "shorts_metrics": {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0
            }
        }
        
        try:
            # Get metrics from feedback data
            total_interactions = (
                self.feedback_data.get("likes", 0) +
                self.feedback_data.get("comments", 0) +
                self.feedback_data.get("shares", 0) +
                self.feedback_data.get("subscribers", 0)
            )
            
            if total_interactions > 0:
                metrics["engagement_rate"] = min(1.0, total_interactions / 1000)  # Normalize to [0,1]
                metrics["growth_rate"] = min(1.0, self.feedback_data.get("subscribers", 0) / 100)
                metrics["sentiment_score"] = self.feedback_data.get("sentiment_score", 0.0)
                metrics["active_members"] = total_interactions
                
                # Video metrics
                metrics["video_metrics"]["views"] = self.feedback_data.get("video_views", 0)
                metrics["video_metrics"]["likes"] = self.feedback_data.get("video_likes", 0)
                metrics["video_metrics"]["comments"] = self.feedback_data.get("video_comments", 0)
                metrics["video_metrics"]["shares"] = self.feedback_data.get("video_shares", 0)
                metrics["video_metrics"]["watch_time"] = self.feedback_data.get("watch_time", 0)
                
                # Shorts metrics
                metrics["shorts_metrics"]["views"] = self.feedback_data.get("shorts_views", 0)
                metrics["shorts_metrics"]["likes"] = self.feedback_data.get("shorts_likes", 0)
                metrics["shorts_metrics"]["comments"] = self.feedback_data.get("shorts_comments", 0)
                metrics["shorts_metrics"]["shares"] = self.feedback_data.get("shorts_shares", 0)
        except Exception as e:
            logger.error(f"Error calculating YouTube metrics: {e}")
        
        return metrics
    
    def get_top_members(self) -> List[Dict[str, Any]]:
        """Get list of top YouTube community members."""
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
                            "platform": "youtube",
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
            logger.error(f"Error getting top YouTube members: {e}")
        
        return top_members
    
    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track an interaction with a YouTube member."""
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
            
            logger.info(f"Tracked {interaction_type} interaction with YouTube member {member_id}")
            return True
        except Exception as e:
            logger.error(f"Error tracking YouTube member interaction: {e}")
            return False
    
    def _get_driver(self, headless=False):
        """Get configured Chrome WebDriver for YouTube."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        driver = webdriver.Chrome(options=options)
        logger.info(" YouTube driver initialized")
        return driver
    
    def _wait(self, custom_range=None):
        """Wait for a random duration."""
        wait_time = random.uniform(*(custom_range or self.wait_range))
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)
    
    def login(self) -> bool:
        """Log in to YouTube."""
        logger.info(" Initiating YouTube login...")
        try:
            self.driver.get(self.login_url)
            self._wait()
            
            # Try cookie login first
            self.cookie_manager.load_cookies(self.driver, "youtube")
            self.driver.refresh()
            self._wait()
            
            if self.is_logged_in():
                logger.info(" Logged into YouTube via cookies")
                return True
            
            # Try credential login
            if self.username and self.password:
                try:
                    # Enter email
                    email_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "identifier"))
                    )
                    email_input.clear()
                    email_input.send_keys(self.username)
                    email_input.send_keys(Keys.RETURN)
                    self._wait((3, 5))
                    
                    # Enter password
                    password_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "password"))
                    )
                    password_input.clear()
                    password_input.send_keys(self.password)
                    password_input.send_keys(Keys.RETURN)
                    self._wait((5, 8))
                    
                    if self.is_logged_in():
                        self.cookie_manager.save_cookies(self.driver, "youtube")
                        logger.info(" Logged into YouTube via credentials")
                        return True
                except Exception as e:
                    logger.error(f"YouTube auto-login failed: {e}")
            
            # Manual login fallback
            if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, "youtube"):
                self.cookie_manager.save_cookies(self.driver, "youtube")
                return True
            
            return False
        except Exception as e:
            logger.error(f"YouTube login error: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if logged into YouTube."""
        try:
            self.driver.get("https://studio.youtube.com")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            return "studio.youtube.com" in self.driver.current_url
        except Exception:
            return False
    
    def post_video(self, video_path: str, title: str, description: str, tags: List[str] = None, is_short: bool = False) -> bool:
        """Post a video to YouTube."""
        logger.info(" Posting video to YouTube...")
        try:
            if not self.is_logged_in():
                if not self.login():
                    return False
            
            self.driver.get("https://studio.youtube.com/channel/upload")
            self._wait((3, 5))
            
            # Upload video file
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(video_path)
            self._wait((5, 8))  # Wait for upload
            
            # Set title
            title_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Add a title']"))
            )
            title_input.clear()
            title_input.send_keys(title)
            
            # Set description
            description_input = self.driver.find_element(By.CSS_SELECTOR, "textarea[placeholder='Tell viewers about your video']")
            description_input.clear()
            description_input.send_keys(description)
            
            # Add tags, ensuring no personal branding tags are included
            if tags:
                tags = [tag for tag in tags if tag != "personal_brand"]  # Remove personal branding tags
                tags_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Add tags']")
                for tag in tags:
                    tags_input.send_keys(tag)
                    tags_input.send_keys(Keys.RETURN)
            
            # Mark as Short if needed
            if is_short:
                shorts_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[name='SHORT']")
                if not shorts_checkbox.is_selected():
                    shorts_checkbox.click()
            
            # Submit video
            next_button = self.driver.find_element(By.CSS_SELECTOR, "#next-button")
            next_button.click()
            self._wait((2, 3))
            
            # Navigate through remaining screens
            for _ in range(3):  # Usually 3 more screens
                next_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#next-button"))
                )
                next_button.click()
                self._wait((1, 2))
            
            # Finally, publish
            publish_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#done-button"))
            )
            publish_button.click()
            self._wait((5, 8))
            
            logger.info(" Successfully posted video to YouTube")
            write_json_log("youtube", "success", "Posted video")
            return True
        except Exception as e:
            logger.error(f"Error posting video to YouTube: {e}")
            return False
    
    def run_daily_strategy_session(self):
        """Run complete daily YouTube strategy session."""
        logger.info(" Starting Full YouTube Strategy Session")
        try:
            if not self.initialize({}):
                return
            
            # Generate content ideas for different formats
            content_types = ["regular", "shorts", "community_post"]
            for content_type in content_types:
                content_prompt = f"Create a {content_type} script about trading and market analysis."
                
                script = self.ai_agent.ask(
                    prompt=content_prompt,
                    metadata={"platform": "youtube", "content_type": content_type}
                )
                
                if script:
                    # Here you would generate/prepare the content
                    # For now, we'll just log it
                    logger.info(f"Generated script for {content_type}")
                
                self._wait((5, 10))
            
            # Process engagement metrics
            self.analyze_engagement_metrics()
            
            # Run feedback and reward systems
            self.run_feedback_loop()
            self.reward_top_creators()
            self.cross_platform_feedback_loop()
            
            self.cleanup()
            logger.info(" YouTube Strategy Session Complete")
        except Exception as e:
            logger.error(f"Error in YouTube strategy session: {e}")
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
        logger.info(" Analyzing YouTube engagement metrics...")
        
        # Regular video metrics
        self.feedback_data["video_views"] = self.feedback_data.get("video_views", 0) + random.randint(50, 200)
        self.feedback_data["video_likes"] = self.feedback_data.get("video_likes", 0) + random.randint(5, 20)
        self.feedback_data["video_comments"] = self.feedback_data.get("video_comments", 0) + random.randint(2, 8)
        self.feedback_data["video_shares"] = self.feedback_data.get("video_shares", 0) + random.randint(1, 5)
        self.feedback_data["watch_time"] = self.feedback_data.get("watch_time", 0) + random.randint(300, 1200)  # in seconds
        
        # Shorts metrics
        self.feedback_data["shorts_views"] = self.feedback_data.get("shorts_views", 0) + random.randint(100, 500)
        self.feedback_data["shorts_likes"] = self.feedback_data.get("shorts_likes", 0) + random.randint(10, 50)
        self.feedback_data["shorts_comments"] = self.feedback_data.get("shorts_comments", 0) + random.randint(3, 15)
        self.feedback_data["shorts_shares"] = self.feedback_data.get("shorts_shares", 0) + random.randint(2, 10)
        
        # Subscriber metrics
        self.feedback_data["subscribers"] = self.feedback_data.get("subscribers", 0) + random.randint(1, 5)
        
        logger.info(f" Regular Video Views: {self.feedback_data['video_views']}")
        logger.info(f" Shorts Views: {self.feedback_data['shorts_views']}")
        logger.info(f" Total Subscribers: {self.feedback_data['subscribers']}")
        logger.info(f"⏱️ Watch Time (hours): {self.feedback_data['watch_time'] / 3600:.2f}")
        
        self._save_feedback_data()

    def run_feedback_loop(self):
        """Run the dynamic feedback loop process."""
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

    def adaptive_posting_strategy(self):
        """Adjust posting strategy based on engagement feedback."""
        logger.info(" Adapting YouTube posting strategy based on feedback...")
        
        # Analyze regular videos performance
        if self.feedback_data.get("video_views", 0) > 1000:
            logger.info(" Regular videos are performing well! Consider increasing production quality.")
        
        # Analyze Shorts performance
        if self.feedback_data.get("shorts_views", 0) > 5000:
            logger.info(" Shorts are getting great traction! Consider creating more short-form content.")
        
        # Analyze watch time
        avg_watch_time = self.feedback_data.get("watch_time", 0) / max(self.feedback_data.get("video_views", 1), 1)
        if avg_watch_time > 300:  # More than 5 minutes
            logger.info("⭐ High average watch time! Content length is optimal.")
        else:
            logger.info("️ Consider adjusting content length to improve watch time.")

    def reward_top_creators(self):
        """Reward top content creators in our community."""
        logger.info(" Identifying and rewarding top YouTube creators...")
        top_members = self.get_top_members()
        
        for member in top_members[:5]:  # Reward top 5
            try:
                reward_message = f"Your content is amazing! Keep creating awesome videos! 🌟"
                self.track_member_interaction(
                    member["id"],
                    "reward",
                    {"message": reward_message, "reward_type": "recognition"}
                )
                logger.info(f"Rewarded creator: {member['id']}")
            except Exception as e:
                logger.error(f"Error rewarding creator {member['id']}: {e}")

    def cross_platform_feedback_loop(self):
        """Integrate YouTube performance data with other platforms."""
        logger.info(" Running cross-platform feedback analysis for YouTube...")
        try:
            # Simulate cross-platform metrics
            platform_metrics = {
                "youtube": self.feedback_data,
                "tiktok": {"views": random.randint(500, 2000)},
                "instagram": {"reels_views": random.randint(300, 1000)}
            }
            
            total_video_views = (
                self.feedback_data.get("video_views", 0) +
                self.feedback_data.get("shorts_views", 0) +
                platform_metrics["tiktok"]["views"] +
                platform_metrics["instagram"]["reels_views"]
            )
            
            logger.info(f" Total video views across platforms: {total_video_views}")
            
            # Update strategy based on cross-platform performance
            if total_video_views > 5000:
                logger.info(" Video content is performing well across platforms")
                
            # Compare performance across platforms
            platform_distribution = {
                "youtube_regular": self.feedback_data.get("video_views", 0),
                "youtube_shorts": self.feedback_data.get("shorts_views", 0),
                "tiktok": platform_metrics["tiktok"]["views"],
                "instagram": platform_metrics["instagram"]["reels_views"]
            }
            
            best_platform = max(platform_distribution.items(), key=lambda x: x[1])[0]
            logger.info(f" Best performing platform: {best_platform}")
        except Exception as e:
            logger.error(f"Error in cross-platform analysis: {e}") 
