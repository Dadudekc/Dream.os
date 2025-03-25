import os
import json
import logging
import time
import threading
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import random

from PyQt5.QtCore import QObject, pyqtSignal

from utils.path_manager import PathManager
from social.log_writer import logger, write_json_log
from social.strategies.twitter_strategy import TwitterStrategy
from social.strategies.facebook_strategy import FacebookStrategy
from social.strategies.reddit_strategy import RedditStrategy
from social.strategies.stocktwits_strategy import StocktwitsStrategy
from social.strategies.linkedin_strategy import LinkedinStrategy
from social.strategies.instagram_strategy import InstagramStrategy
from social.strategies.tiktok_strategy import TikTokStrategy
from social.strategies.youtube_strategy import YouTubeStrategy
from social.UnifiedCommunityDashboard import UnifiedCommunityDashboard as CommunityDashboard
from social.social_post_manager import SocialPostManager
from utils.SentimentAnalyzer import SentimentAnalyzer
from core.ConfigManager import ConfigManager
from social.UnifiedPostManager import UnifiedPostManager
from social.StrategyLoader import StrategyLoader

class CommunityIntegrationManager:
    """
    Manages integrations with various social platforms, handles authentication,
    and provides a unified interface for community building.
    """
    
    # Define platform credentials mapping
    PLATFORM_CREDENTIALS = {
        "twitter": {
            "api_key": "TWITTER_API_KEY",
            "api_secret": "TWITTER_API_SECRET",
            "access_token": "TWITTER_ACCESS_TOKEN",
            "access_secret": "TWITTER_ACCESS_SECRET"
        },
        "facebook": {
            "app_id": "FACEBOOK_APP_ID",
            "app_secret": "FACEBOOK_APP_SECRET",
            "access_token": "FACEBOOK_ACCESS_TOKEN"
        },
        "reddit": {
            "client_id": "REDDIT_CLIENT_ID",
            "client_secret": "REDDIT_CLIENT_SECRET",
            "username": "REDDIT_USERNAME",
            "password": "REDDIT_PASSWORD"
        },
        "discord": {
            "bot_token": "DISCORD_BOT_TOKEN",
            "guild_id": "DISCORD_GUILD_ID"
        },
        "tiktok": {
            "username": "TIKTOK_USERNAME",
            "password": "TIKTOK_PASSWORD",
            "session_id": "TIKTOK_SESSION_ID"
        },
        "youtube": {
            "email": "YOUTUBE_EMAIL",
            "password": "YOUTUBE_PASSWORD",
            "api_key": "YOUTUBE_API_KEY",
            "client_id": "YOUTUBE_CLIENT_ID",
            "client_secret": "YOUTUBE_CLIENT_SECRET"
        }
    }
    
    def __init__(self, config=None):
        """
        Initialize the community integration manager.
        
        Args:
            config (dict, optional): Configuration settings for the manager.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Community Integration Manager")
        
        # Initialize configuration
        self.config_manager = ConfigManager()
        self.config = config or self.config_manager.get_config("community_integration")
        
        # Initialize dashboard
        self.dashboard = CommunityDashboard()
        
        # Initialize post manager
        self.post_manager = UnifiedPostManager()
        
        # Initialize sentiment analyzer
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Platform status tracking
        self.platforms = self._initialize_platforms()
        
        # Strategies for different platforms
        self.strategies = {}
        self._load_strategies()
        
        # Load saved platform status
        self._load_platform_status()
        
        self.logger.info(f"Community Integration Manager initialized with {len(self.platforms)} platforms")

    def _check_platform_credentials(self, platform_id: str) -> bool:
        """
        Check if all required credentials are available for a platform.
        
        Args:
            platform_id (str): Platform identifier.
            
        Returns:
            bool: True if all required credentials are present.
        """
        if platform_id not in self.PLATFORM_CREDENTIALS:
            return False
            
        return all(
            os.environ.get(env_var)
            for env_var in self.PLATFORM_CREDENTIALS[platform_id].values()
        )

    def _initialize_platforms(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize available platform configurations.
        
        Returns:
            Dict: Dictionary of platform configurations.
        """
        platforms = {}
        
        for platform_id, creds in self.PLATFORM_CREDENTIALS.items():
            has_credentials = self._check_platform_credentials(platform_id)
            
            platforms[platform_id] = {
                "name": platform_id.capitalize(),
                "enabled": self.config.get(f"{platform_id}_enabled", False),
                "connected": False,
                "last_connected": None,
                "credentials": {
                    key: os.environ.get(env_var)
                    for key, env_var in creds.items()
                },
                "has_credentials": has_credentials
            }
        
        return platforms
    
    def _load_strategies(self):
        """Load platform-specific strategies."""
        try:
            strategy_loader = StrategyLoader()
            
            # Load strategies for enabled platforms with credentials
            for platform_id, platform in self.platforms.items():
                if platform["enabled"] and platform["has_credentials"]:
                    strategy_name = f"{platform_id.capitalize()}CommunityStrategy"
                    try:
                        self.strategies[platform_id] = strategy_loader.load_strategy(strategy_name)
                        self.logger.info(f"Loaded strategy for {platform_id}")
                    except Exception as e:
                        self.logger.error(f"Error loading strategy for {platform_id}: {str(e)}")
            
            self.logger.info(f"Loaded {len(self.strategies)} platform strategies")
        except Exception as e:
            self.logger.error(f"Error loading strategies: {str(e)}")
    
    def _load_platform_status(self):
        """Load saved platform status from file."""
        try:
            platform_status_path = PathManager.get_path("data") + "/platform_status.json"
            
            if os.path.exists(platform_status_path):
                with open(platform_status_path, "r") as f:
                    status_data = json.load(f)
                
                # Update platforms with saved status
                for platform_id, status in status_data.items():
                    if platform_id in self.platforms:
                        # Only update certain fields from saved data
                        if "enabled" in status:
                            self.platforms[platform_id]["enabled"] = status["enabled"]
                        if "connected" in status:
                            self.platforms[platform_id]["connected"] = status["connected"]
                        if "last_connected" in status:
                            self.platforms[platform_id]["last_connected"] = status["last_connected"]
                
                self.logger.info("Loaded platform status from file")
        except Exception as e:
            self.logger.error(f"Error loading platform status: {str(e)}")
    
    def _save_platform_status(self):
        """Save current platform status to file."""
        try:
            platform_status_path = PathManager.get_path("data") + "/platform_status.json"
            
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(platform_status_path), exist_ok=True)
            
            # Prepare data to save
            status_data = {}
            for platform_id, platform in self.platforms.items():
                status_data[platform_id] = {
                    "enabled": platform["enabled"],
                    "connected": platform["connected"],
                    "last_connected": platform["last_connected"]
                }
            
            with open(platform_status_path, "w") as f:
                json.dump(status_data, f, indent=2)
            
            self.logger.info("Saved platform status to file")
        except Exception as e:
            self.logger.error(f"Error saving platform status: {str(e)}")
    
    def get_available_platforms(self) -> Dict[str, Dict[str, Any]]:
        """
        Get available platforms with their status.
        
        Returns:
            Dict: Dictionary of platform information.
        """
        return self.platforms
    
    def get_platform(self, platform_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information for a specific platform.
        
        Args:
            platform_id (str): Platform identifier.
            
        Returns:
            Dict or None: Platform information or None if not found.
        """
        return self.platforms.get(platform_id)
    
    def get_all_platforms(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all platforms with their status.
        
        Returns:
            Dict: Dictionary of platform information.
        """
        return self.platforms
    
    def enable_platform(self, platform_id: str) -> bool:
        """
        Enable a platform.
        
        Args:
            platform_id (str): Platform to enable.
            
        Returns:
            bool: True if successfully enabled, False otherwise.
        """
        if platform_id not in self.platforms:
            self.logger.error(f"Unknown platform: {platform_id}")
            return False
        
        self.platforms[platform_id]["enabled"] = True
        self._save_platform_status()
        
        # Load strategy if not already loaded
        if platform_id not in self.strategies and self.platforms[platform_id]["has_credentials"]:
            strategy_name = f"{platform_id.capitalize()}CommunityStrategy"
            try:
                strategy_loader = StrategyLoader()
                self.strategies[platform_id] = strategy_loader.load_strategy(strategy_name)
                self.logger.info(f"Loaded strategy for {platform_id}")
            except Exception as e:
                self.logger.error(f"Error loading strategy for {platform_id}: {str(e)}")
        
        self.logger.info(f"Enabled platform: {platform_id}")
        return True
    
    def disable_platform(self, platform_id: str) -> bool:
        """
        Disable a platform.
        
        Args:
            platform_id (str): Platform to disable.
            
        Returns:
            bool: True if successfully disabled, False otherwise.
        """
        if platform_id not in self.platforms:
            self.logger.error(f"Unknown platform: {platform_id}")
            return False
        
        self.platforms[platform_id]["enabled"] = False
        self._save_platform_status()
        
        # Disconnect if connected
        if self.platforms[platform_id]["connected"]:
            self.disconnect_platform(platform_id)
        
        self.logger.info(f"Disabled platform: {platform_id}")
        return True
    
    def connect_platform(self, platform_id: str) -> bool:
        """
        Connect to a platform.
        
        Args:
            platform_id (str): Platform to connect.
            
        Returns:
            bool: True if successfully connected, False otherwise.
        """
        if platform_id not in self.platforms:
            self.logger.error(f"Unknown platform: {platform_id}")
            return False
        
        if not self.platforms[platform_id]["enabled"]:
            self.logger.error(f"Platform {platform_id} is not enabled")
            return False
        
        if not self.platforms[platform_id]["has_credentials"]:
            self.logger.error(f"Missing credentials for platform {platform_id}")
            return False
        
        # Try to connect using the strategy
        if platform_id in self.strategies:
            try:
                # Initialize the strategy with credentials
                credentials = self.platforms[platform_id]["credentials"]
                success = self.strategies[platform_id].initialize(credentials)
                
                if success:
                    self.platforms[platform_id]["connected"] = True
                    self.platforms[platform_id]["last_connected"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self._save_platform_status()
                    
                    self.logger.info(f"Connected to platform: {platform_id}")
                    return True
                else:
                    self.logger.error(f"Failed to connect to platform: {platform_id}")
                    return False
            except Exception as e:
                self.logger.error(f"Error connecting to platform {platform_id}: {str(e)}")
                return False
        else:
            self.logger.error(f"No strategy available for platform {platform_id}")
            return False
    
    def disconnect_platform(self, platform_id: str) -> bool:
        """
        Disconnect from a platform.
        
        Args:
            platform_id (str): Platform to disconnect.
            
        Returns:
            bool: True if successfully disconnected, False otherwise.
        """
        if platform_id not in self.platforms:
            self.logger.error(f"Unknown platform: {platform_id}")
            return False
        
        if not self.platforms[platform_id]["connected"]:
            # Already disconnected
            return True
        
        # Try to disconnect using the strategy
        if platform_id in self.strategies:
            try:
                success = self.strategies[platform_id].cleanup()
                
                # Mark as disconnected even if cleanup fails
                self.platforms[platform_id]["connected"] = False
                self._save_platform_status()
                
                self.logger.info(f"Disconnected from platform: {platform_id}")
                return True
            except Exception as e:
                self.logger.error(f"Error disconnecting from platform {platform_id}: {str(e)}")
                
                # Still mark as disconnected
                self.platforms[platform_id]["connected"] = False
                self._save_platform_status()
                
                return False
        else:
            # No strategy, just mark as disconnected
            self.platforms[platform_id]["connected"] = False
            self._save_platform_status()
            
            self.logger.info(f"Disconnected from platform: {platform_id}")
            return True
    
    def run_daily_community_management(self) -> Dict[str, Any]:
        """
        Run daily community management workflow.
        
        Returns:
            Dict: Results of the workflow execution.
        """
        results = {
            "metrics_collected": False,
            "insights_generated": False,
            "plan_updated": False,
            "errors": []
        }
        
        # Connect to enabled platforms
        self._connect_enabled_platforms()
        
        # Update metrics
        try:
            metrics = self._collect_metrics()
            if metrics:
                self.dashboard.save_metrics(metrics)
                results["metrics_collected"] = True
        except Exception as e:
            error_msg = f"Error collecting metrics: {str(e)}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Generate insights if metrics were collected
        if results["metrics_collected"]:
            try:
                insights = self.generate_insights_and_recommendations()
                if insights:
                    results["insights"] = insights
                    results["insights_generated"] = True
            except Exception as e:
                error_msg = f"Error generating insights: {str(e)}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
        
        # Update community building plan if insights were generated
        if results["insights_generated"]:
            try:
                plan = self.create_community_building_plan()
                if plan:
                    results["plan_updated"] = True
            except Exception as e:
                error_msg = f"Error updating community plan: {str(e)}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
        
        return results
    
    def _connect_enabled_platforms(self):
        """Connect to all enabled platforms."""
        for platform_id, platform in self.platforms.items():
            if platform["enabled"] and not platform["connected"] and platform["has_credentials"]:
                self.connect_platform(platform_id)
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """
        Collect metrics from all connected platforms.
        
        Returns:
            Dict: Collected metrics.
        """
        metrics = {
            "total": {
                "community_health_score": 0,
                "engagement_rate": 0,
                "growth_rate": 0,
                "sentiment_score": 0,
                "active_members": 0
            },
            "platforms": {}
        }
        
        platform_count = 0
        
        # Collect metrics from each connected platform
        for platform_id, platform in self.platforms.items():
            if platform["connected"] and platform_id in self.strategies:
                try:
                    platform_metrics = self.strategies[platform_id].get_community_metrics()
                    if platform_metrics:
                        metrics["platforms"][platform_id] = platform_metrics
                        
                        # Aggregate metrics
                        metrics["total"]["engagement_rate"] += platform_metrics.get("engagement_rate", 0)
                        metrics["total"]["growth_rate"] += platform_metrics.get("growth_rate", 0)
                        metrics["total"]["sentiment_score"] += platform_metrics.get("sentiment_score", 0)
                        metrics["total"]["active_members"] += platform_metrics.get("active_members", 0)
                        
                        platform_count += 1
                except Exception as e:
                    self.logger.error(f"Error collecting metrics from {platform_id}: {str(e)}")
        
        # Calculate averages
        if platform_count > 0:
            metrics["total"]["engagement_rate"] /= platform_count
            metrics["total"]["growth_rate"] /= platform_count
            metrics["total"]["sentiment_score"] /= platform_count
            
            # Calculate overall health score
            health_score = (
                metrics["total"]["engagement_rate"] * 35 +
                metrics["total"]["growth_rate"] * 35 +
                (metrics["total"]["sentiment_score"] + 1) / 2 * 30  # Normalize sentiment from [-1,1] to [0,1]
            ) * 100
            
            metrics["total"]["community_health_score"] = min(max(health_score, 0), 100)
        
        return metrics
    
    def analyze_community_health(self) -> Dict[str, Any]:
        """
        Analyze the overall health of the community across platforms.
        
        Returns:
            Dict: Health report with scores and analysis.
        """
        # Get latest metrics
        metrics = self.dashboard.get_latest_metrics()
        if not metrics:
            return {"error": "No metrics available for health analysis"}
        
        # Calculate health metrics
        health_report = {
            "overall_score": metrics["total"].get("community_health_score", 0),
            "engagement_score": metrics["total"].get("engagement_rate", 0) * 100,
            "growth_score": metrics["total"].get("growth_rate", 0) * 100,
            "sentiment_score": metrics["total"].get("sentiment_score", 0) * 50 + 50,  # Convert [-1,1] to [0,100]
            "platform_scores": {},
            "areas_of_strength": [],
            "areas_of_improvement": []
        }
        
        # Calculate platform-specific scores
        for platform_id, platform_metrics in metrics.get("platforms", {}).items():
            platform_health = platform_metrics.get("community_health_score", 0)
            if not platform_health and "engagement_rate" in platform_metrics:
                # Calculate health if not provided
                platform_health = (
                    platform_metrics.get("engagement_rate", 0) * 35 +
                    platform_metrics.get("growth_rate", 0) * 35 +
                    (platform_metrics.get("sentiment_score", 0) + 1) / 2 * 30
                ) * 100
            
            health_report["platform_scores"][platform_id] = platform_health
        
        # Determine areas of strength and improvement
        if health_report["engagement_score"] > 60:
            health_report["areas_of_strength"].append("Community Engagement")
        elif health_report["engagement_score"] < 40:
            health_report["areas_of_improvement"].append("Community Engagement")
        
        if health_report["growth_score"] > 60:
            health_report["areas_of_strength"].append("Community Growth")
        elif health_report["growth_score"] < 40:
            health_report["areas_of_improvement"].append("Community Growth")
        
        if health_report["sentiment_score"] > 60:
            health_report["areas_of_strength"].append("Community Sentiment")
        elif health_report["sentiment_score"] < 40:
            health_report["areas_of_improvement"].append("Community Sentiment")
        
        return health_report
    
    def generate_insights_and_recommendations(self) -> Dict[str, Any]:
        """
        Generate insights and recommendations based on community data.
        
        Returns:
            Dict: Insights and recommendations.
        """
        # Get health report
        health_report = self.analyze_community_health()
        
        # Get metrics history
        metrics_history = self.dashboard.get_metrics_history(days=30)
        
        # Initialize insights structure
        insights = {
            "health_report": health_report,
            "overall": {
                "summary": "",
                "strengths": [],
                "weaknesses": [],
                "opportunities": [],
                "recommendations": []
            },
            "platforms": {},
            "trends": {
                "total": {}
            }
        }
        
        # Generate overall summary based on health report
        overall_score = health_report.get("overall_score", 0)
        if overall_score > 75:
            insights["overall"]["summary"] = (
                "Your community is thriving with strong engagement and positive sentiment. "
                "Focus on scaling and deepening relationships with key members."
            )
        elif overall_score > 50:
            insights["overall"]["summary"] = (
                "Your community is healthy but has room for improvement. "
                "Concentrate on increasing engagement and maintaining growth momentum."
            )
        elif overall_score > 25:
            insights["overall"]["summary"] = (
                "Your community needs attention. Focus on addressing negative sentiment "
                "and creating more engaging content to stimulate activity."
            )
        else:
            insights["overall"]["summary"] = (
                "Your community requires immediate intervention. Consider a complete "
                "strategy overhaul focusing on rebuilding trust and re-engaging members."
            )
        
        # Add strengths from health report
        insights["overall"]["strengths"] = health_report.get("areas_of_strength", [])
        
        # Add weaknesses from health report
        insights["overall"]["weaknesses"] = health_report.get("areas_of_improvement", [])
        
        # Generate recommendations based on health analysis
        if "Community Engagement" in health_report.get("areas_of_improvement", []):
            insights["overall"]["recommendations"].append(
                "Increase interactive content like polls and questions to boost engagement"
            )
            insights["overall"]["recommendations"].append(
                "Respond more quickly to member comments and messages"
            )
        
        if "Community Growth" in health_report.get("areas_of_improvement", []):
            insights["overall"]["recommendations"].append(
                "Implement a referral program to encourage members to invite others"
            )
            insights["overall"]["recommendations"].append(
                "Increase content frequency during peak activity hours"
            )
        
        if "Community Sentiment" in health_report.get("areas_of_improvement", []):
            insights["overall"]["recommendations"].append(
                "Address common concerns or complaints that are affecting sentiment"
            )
            insights["overall"]["recommendations"].append(
                "Highlight positive community stories and member achievements"
            )
        
        # Generate opportunities
        insights["overall"]["opportunities"] = [
            "Cross-platform community building to create a more unified experience",
            "Leveraging top community members as advocates and moderators",
            "Creating specialized content for different segments of your community"
        ]
        
        # Calculate trends from metrics history
        if metrics_history:
            for metric_name in ["community_health_score", "engagement_rate", "growth_rate", "sentiment_score", "active_members"]:
                values = [entry["metrics"]["total"].get(metric_name, 0) for entry in metrics_history if "total" in entry["metrics"]]
                if len(values) >= 2:
                    change = values[-1] - values[0]
                    percent_change = (change / values[0] * 100) if values[0] > 0 else 0
                    
                    insights["trends"]["total"][metric_name] = {
                        "value": values[-1],
                        "change": change,
                        "percent_change": percent_change,
                        "trend": "up" if change > 0 else ("down" if change < 0 else "stable")
                    }
        
        # Platform-specific insights
        for platform_id, platform in self.platforms.items():
            if platform["connected"] and platform_id in self.strategies:
                try:
                    platform_insights = self.strategies[platform_id].get_platform_insights()
                    if platform_insights:
                        insights["platforms"][platform_id] = platform_insights
                    else:
                        # Generate basic platform insights
                        insights["platforms"][platform_id] = {
                            "strengths": [],
                            "weaknesses": [],
                            "opportunities": [],
                            "recommendations": []
                        }
                        
                        # Add platform-specific recommendations
                        if platform_id == "twitter":
                            insights["platforms"][platform_id]["recommendations"] = [
                                "Use more hashtags relevant to your community topics",
                                "Engage with industry influencers to expand reach"
                            ]
                        elif platform_id == "facebook":
                            insights["platforms"][platform_id]["recommendations"] = [
                                "Post more visual content to increase engagement",
                                "Create more group events to foster community interaction"
                            ]
                        elif platform_id == "reddit":
                            insights["platforms"][platform_id]["recommendations"] = [
                                "Focus on providing value in subreddit discussions",
                                "Host regular AMAs (Ask Me Anything) sessions"
                            ]
                        elif platform_id == "discord":
                            insights["platforms"][platform_id]["recommendations"] = [
                                "Create more specialized channels for specific interests",
                                "Host regular voice chat events or community calls"
                            ]
                except Exception as e:
                    self.logger.error(f"Error generating insights for {platform_id}: {str(e)}")
        
        return insights
    
    def create_community_building_plan(self) -> Dict[str, Any]:
        """
        Create a 30-day community building plan.
        
        Returns:
            Dict: Community building plan.
        """
        # Get insights first
        insights = self.generate_insights_and_recommendations()
        
        # Start with today's date
        start_date = datetime.now()
        
        # Create plan structure
        plan = {
            "generated_at": start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "days": []
        }
        
        # Define activity types
        activity_types = {
            "engagement": [
                "Post an interactive poll about {topic}",
                "Host a Q&A session about {topic}",
                "Share a challenge related to {topic}",
                "Feature a community member who {achievement}",
                "Create a discussion thread about {topic}"
            ],
            "content": [
                "Share a tutorial on how to {topic}",
                "Post a case study about {topic}",
                "Create an infographic about {topic}",
                "Share industry news about {topic}",
                "Post a video demonstration of {topic}"
            ],
            "community_building": [
                "Welcome new members who joined this week",
                "Highlight top community contributors",
                "Start a community brainstorming session about {topic}",
                "Create a resource directory for {topic}",
                "Organize a virtual meetup for community members"
            ],
            "mixed": [
                "Share user-generated content about {topic}",
                "Run a small contest related to {topic}",
                "Share success stories from community members",
                "Post a behind-the-scenes look at {topic}",
                "Ask for feedback about {topic}"
            ]
        }
        
        # Topic ideas based on insights
        topics = [
            "industry trends",
            "best practices",
            "productivity tips",
            "common challenges",
            "success strategies",
            "tool recommendations",
            "recent innovations",
            "community goals",
            "future developments",
            "learning resources"
        ]
        
        # Achievements for featuring members
        achievements = [
            "contributed valuable insights",
            "helped other community members",
            "demonstrated expertise in {topic}",
            "shared an innovative approach",
            "overcame a significant challenge"
        ]
        
        # Generate activities for each day
        for day in range(1, 31):
            current_date = start_date + timedelta(days=day-1)
            
            # Determine focus for this day
            if day % 7 == 1:  # First day of week
                focus = "engagement"
            elif day % 7 == 4:  # Middle of week
                focus = "content"
            elif day % 7 == 0:  # End of week
                focus = "community_building"
            else:
                focus = "mixed"
            
            # Select activities for this day
            day_activities = []
            
            # 1-2 activities per day
            num_activities = random.randint(1, 2)
            for _ in range(num_activities):
                activity_template = random.choice(activity_types[focus])
                
                # Replace placeholders
                if "{topic}" in activity_template:
                    activity = activity_template.replace("{topic}", random.choice(topics))
                elif "{achievement}" in activity_template:
                    achievement_template = random.choice(achievements)
                    if "{topic}" in achievement_template:
                        achievement = achievement_template.replace("{topic}", random.choice(topics))
                    else:
                        achievement = achievement_template
                    activity = activity_template.replace("{achievement}", achievement)
                else:
                    activity = activity_template
                
                day_activities.append(activity)
            
            # Add platforms to focus on
            platforms_to_focus = []
            for platform_id, platform in self.platforms.items():
                if platform["enabled"] and random.random() < 0.3:  # 30% chance to focus on each platform
                    platforms_to_focus.append(platform["name"])
            
            if platforms_to_focus:
                platform_str = ", ".join(platforms_to_focus)
                day_activities.append(f"Focus on {platform_str} platform(s) today")
            
            # Add day to plan
            plan["days"].append({
                "day": day,
                "date": current_date.strftime("%Y-%m-%d"),
                "focus": focus.replace("_", " ").title(),
                "activities": day_activities
            })
        
        return plan
    
    def post_content(self, content: Dict[str, Any], platforms: List[str] = None) -> Dict[str, Any]:
        """
        Post content to specified platforms.
        
        Args:
            content (Dict): Content to post including text, media, etc.
            platforms (List, optional): List of platform IDs to post to. If None, post to all connected platforms.
            
        Returns:
            Dict: Results of posting operations.
        """
        results = {
            "success": False,
            "platforms": {},
            "errors": []
        }
        
        # Determine which platforms to post to
        if platforms is None:
            target_platforms = [p_id for p_id, p in self.platforms.items() if p["connected"]]
        else:
            target_platforms = [p_id for p_id in platforms if p_id in self.platforms and self.platforms[p_id]["connected"]]
        
        if not target_platforms:
            results["errors"].append("No connected platforms to post to")
            return results
        
        # Use post manager to post content
        for platform_id in target_platforms:
            try:
                if platform_id in self.strategies:
                    platform_result = self.post_manager.post_to_platform(platform_id, content, self.strategies[platform_id])
                    results["platforms"][platform_id] = platform_result
                    
                    if platform_result.get("success", False):
                        self.logger.info(f"Successfully posted to {platform_id}")
                    else:
                        error_msg = platform_result.get("error", f"Unknown error posting to {platform_id}")
                        self.logger.error(error_msg)
                        results["errors"].append(error_msg)
                else:
                    error_msg = f"No strategy available for platform {platform_id}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["platforms"][platform_id] = {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Error posting to {platform_id}: {str(e)}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                results["platforms"][platform_id] = {"success": False, "error": error_msg}
        
        # Overall success if at least one platform succeeded
        results["success"] = any(p.get("success", False) for p in results["platforms"].values())
        
        return results
    
    def identify_advocates(self) -> List[Dict[str, Any]]:
        """
        Identify top community members and potential advocates.
        
        Returns:
            List: List of top members with their details.
        """
        all_members = []
        
        # Collect members from each platform
        for platform_id, platform in self.platforms.items():
            if platform["connected"] and platform_id in self.strategies:
                try:
                    platform_members = self.strategies[platform_id].get_top_members()
                    for member in platform_members:
                        # Add platform identifier
                        member["primary_platform"] = platform_id
                        all_members.append(member)
                except Exception as e:
                    self.logger.error(f"Error getting top members from {platform_id}: {str(e)}")
        
        # Sort by engagement score
        all_members.sort(key=lambda x: x.get("engagement_score", 0), reverse=True)
        
        # Take top 20 members
        top_members = all_members[:20]
        
        # Add sentiment scores if not present
        for member in top_members:
            if "sentiment_score" not in member and "recent_posts" in member:
                # Analyze sentiment of recent posts
                try:
                    sentiment_scores = []
                    for post in member["recent_posts"]:
                        if "content" in post:
                            score = self.sentiment_analyzer.analyze(post["content"])
                            sentiment_scores.append(score)
                    
                    if sentiment_scores:
                        member["sentiment_score"] = sum(sentiment_scores) / len(sentiment_scores)
                except Exception as e:
                    self.logger.error(f"Error analyzing sentiment for member: {str(e)}")
        
        # Save to dashboard
        self.dashboard.top_members = top_members
        
        return top_members
    
    def track_member_interactions(self, member_id: str, platform_id: str, interaction_type: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Track interactions with community members.
        
        Args:
            member_id (str): Member identifier.
            platform_id (str): Platform identifier.
            interaction_type (str): Type of interaction.
            metadata (Dict, optional): Additional metadata about the interaction.
            
        Returns:
            bool: True if successfully tracked, False otherwise.
        """
        try:
            if platform_id in self.platforms and platform_id in self.strategies:
                # Track using platform strategy
                result = self.strategies[platform_id].track_member_interaction(member_id, interaction_type, metadata)
                
                # Also aggregate in dashboard
                if result and hasattr(self.dashboard, 'track_interaction'):
                    self.dashboard.track_interaction(member_id, platform_id, interaction_type, metadata)
                
                return result
            else:
                self.logger.error(f"Cannot track interaction: Platform {platform_id} not available")
                return False
        except Exception as e:
            self.logger.error(f"Error tracking member interaction: {str(e)}")
            return False 