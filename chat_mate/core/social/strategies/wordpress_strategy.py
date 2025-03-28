import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, comments, media
from wordpress_xmlrpc.compat import xmlrpc_client
from bs4 import BeautifulSoup

from social.strategies.base_platform_strategy import BasePlatformStrategy
from utils.SentimentAnalyzer import SentimentAnalyzer
from config.ConfigManager import ConfigManager

class WordPressCommunityStrategy(BasePlatformStrategy):
    """
    WordPress community strategy that integrates with YouTube for automated community building.
    Features:
    - Auto-syncs YouTube videos as WordPress posts
    - Manages comments across both platforms
    - Generates engagement reports
    - Handles community moderation
    - Creates automated responses
    """
    
    def __init__(self, driver=None):
        """Initialize WordPress strategy."""
        super().__init__(platform_id="wordpress", driver=driver)
        self.config = ConfigManager().get_config("wordpress")
        self.logger = logging.getLogger(__name__)
        self.wp_client = None
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Initialize paths
        self.data_dir = os.getenv("DATA_DIR", "./data")
        self.wp_data_file = os.path.join(self.data_dir, "wordpress_data.json")
        
        # Load WordPress credentials
        self.wp_url = os.getenv("WORDPRESS_URL")
        self.wp_username = os.getenv("WORDPRESS_USERNAME")
        self.wp_password = os.getenv("WORDPRESS_APPLICATION_PASSWORD")
        
        # Community settings
        self.auto_moderation = True
        self.comment_moderation = os.getenv("WORDPRESS_COMMENT_MODERATION", "true").lower() == "true"
        self.max_comments_per_hour = int(os.getenv("COMMENT_RATE_LIMIT", "5"))
        
        # Initialize tracking data
        self.community_data = self._load_community_data()

    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize WordPress connection and verify credentials."""
        try:
            # Initialize WordPress XML-RPC client
            self.wp_client = Client(
                f"{self.wp_url}/xmlrpc.php",
                self.wp_username,
                self.wp_password
            )
            
            # Test connection
            self.wp_client.call(posts.GetPosts({'number': 1}))
            self.logger.info(" Successfully connected to WordPress")
            return True
        except Exception as e:
            self.logger.error(f" Failed to initialize WordPress connection: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up resources and save data."""
        try:
            self._save_community_data()
            return True
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return False

    def sync_youtube_video(self, video_data: Dict[str, Any]) -> bool:
        """
        Sync a YouTube video as a WordPress post with embedded video and content.
        
        Args:
            video_data: Dictionary containing video information
                - title: Video title
                - description: Video description
                - video_id: YouTube video ID
                - tags: List of video tags
                - thumbnail_url: URL of video thumbnail
        """
        try:
            # Create WordPress post
            post = WordPressPost()
            post.title = video_data["title"]
            
            # Create embedded video content
            video_embed = f'<!-- wp:embed {{"url":"https://www.youtube.com/watch?v={video_data["video_id"]}","type":"video","providerNameSlug":"youtube"}} -->'
            video_embed += f'<figure class="wp-block-embed is-type-video is-provider-youtube">'
            video_embed += f'<div class="wp-block-embed__wrapper">'
            video_embed += f'https://www.youtube.com/watch?v={video_data["video_id"]}'
            video_embed += f'</div></figure>'
            video_embed += f'<!-- /wp:embed -->'
            
            # Add description and call-to-action
            content = f"{video_embed}\n\n"
            content += f"<!-- wp:paragraph -->\n"
            content += f"<p>{video_data['description']}</p>\n"
            content += f"<!-- /wp:paragraph -->\n\n"
            content += f"<!-- wp:paragraph -->\n"
            content += f"<p>🔔 Subscribe to our YouTube channel for more content like this!</p>\n"
            content += f"<!-- /wp:paragraph -->"
            
            post.content = content
            post.terms_names = {
                'category': self.config.get("categories", ["Videos"]),
                'post_tag': video_data.get("tags", [])
            }
            post.post_status = 'publish'
            
            # Post to WordPress
            post_id = self.wp_client.call(posts.NewPost(post))
            
            # Track in community data
            self.community_data["synced_videos"][video_data["video_id"]] = {
                "wp_post_id": post_id,
                "synced_at": datetime.now().isoformat(),
                "engagement": {
                    "comments": 0,
                    "likes": 0
                }
            }
            
            self._save_community_data()
            self.logger.info(f" Successfully synced YouTube video to WordPress: {post_id}")
            return True
            
        except Exception as e:
            self.logger.error(f" Failed to sync YouTube video: {e}")
            return False

    def moderate_comment(self, comment_text: str) -> bool:
        """
        Automatically moderate a comment using sentiment analysis and content rules.
        
        Args:
            comment_text: The comment text to moderate
            
        Returns:
            bool: True if comment is approved, False if it should be blocked
        """
        try:
            # Check sentiment
            sentiment = self.sentiment_analyzer.analyze(comment_text)
            
            # Check for spam/inappropriate content
            spam_indicators = ["http://", "https://", "www.", ".com", "buy now", "click here"]
            has_spam = any(indicator in comment_text.lower() for indicator in spam_indicators)
            
            # Decision logic
            if has_spam:
                return False
            if sentiment < -0.7:  # Very negative sentiment
                return False
            if len(comment_text) < 2:  # Too short
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error moderating comment: {e}")
            return False

    def get_community_metrics(self) -> Dict[str, Any]:
        """Get WordPress community engagement metrics."""
        try:
            metrics = {
                "total_posts": 0,
                "total_comments": 0,
                "total_synced_videos": len(self.community_data["synced_videos"]),
                "engagement_rate": 0.0,
                "sentiment_score": 0.0,
                "active_members": set(),
                "top_posts": []
            }
            
            # Get recent posts
            recent_posts = self.wp_client.call(posts.GetPosts({'number': 10}))
            
            for post in recent_posts:
                metrics["total_posts"] += 1
                
                # Get comments for post
                post_comments = self.wp_client.call(comments.GetComments({'post_id': post.id}))
                comment_count = len(post_comments)
                metrics["total_comments"] += comment_count
                
                # Track unique commenters
                for comment in post_comments:
                    metrics["active_members"].add(comment.author)
                
                # Track top posts
                metrics["top_posts"].append({
                    "id": post.id,
                    "title": post.title,
                    "comments": comment_count,
                    "date": post.date.isoformat()
                })
            
            # Calculate engagement rate
            if metrics["total_posts"] > 0:
                metrics["engagement_rate"] = metrics["total_comments"] / metrics["total_posts"]
            
            # Convert active_members to count
            metrics["active_members"] = len(metrics["active_members"])
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting community metrics: {e}")
            return {}

    def get_top_members(self) -> List[Dict[str, Any]]:
        """Get list of most engaged community members."""
        try:
            member_activity = {}
            
            # Get recent comments
            recent_comments = self.wp_client.call(comments.GetComments({'number': 100}))
            
            for comment in recent_comments:
                if comment.author not in member_activity:
                    member_activity[comment.author] = {
                        "comment_count": 0,
                        "last_active": comment.date,
                        "recent_comments": []
                    }
                
                member_activity[comment.author]["comment_count"] += 1
                member_activity[comment.author]["recent_comments"].append({
                    "content": comment.content,
                    "date": comment.date.isoformat()
                })
            
            # Sort by activity
            top_members = []
            for author, data in sorted(
                member_activity.items(),
                key=lambda x: x[1]["comment_count"],
                reverse=True
            )[:20]:
                top_members.append({
                    "username": author,
                    "engagement_score": min(1.0, data["comment_count"] / 20),
                    "comment_count": data["comment_count"],
                    "last_active": data["last_active"].isoformat(),
                    "recent_comments": data["recent_comments"][:5]
                })
            
            return top_members
            
        except Exception as e:
            self.logger.error(f"Error getting top members: {e}")
            return []

    def _load_community_data(self) -> Dict[str, Any]:
        """Load community data from file."""
        if os.path.exists(self.wp_data_file):
            with open(self.wp_data_file, 'r') as f:
                return json.load(f)
        return {
            "synced_videos": {},
            "moderation_queue": [],
            "member_activity": {},
            "last_sync": None
        }

    def _save_community_data(self):
        """Save community data to file."""
        os.makedirs(os.path.dirname(self.wp_data_file), exist_ok=True)
        with open(self.wp_data_file, 'w') as f:
            json.dump(self.community_data, f, indent=4)

    def generate_engagement_report(self) -> Dict[str, Any]:
        """Generate a detailed engagement report."""
        metrics = self.get_community_metrics()
        top_members = self.get_top_members()
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "metrics": metrics,
            "top_members": top_members,
            "recommendations": []
        }
        
        # Generate recommendations
        if metrics["engagement_rate"] < 0.5:
            report["recommendations"].append(
                "Consider posting more engaging questions in your content"
            )
        if metrics["active_members"] < 10:
            report["recommendations"].append(
                "Try reaching out to silent readers with polls or easy-to-answer questions"
            )
        
        return report

    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track member interactions."""
        try:
            if member_id not in self.community_data["member_activity"]:
                self.community_data["member_activity"][member_id] = {
                    "interactions": [],
                    "first_seen": datetime.now().isoformat()
                }
            
            self.community_data["member_activity"][member_id]["interactions"].append({
                "type": interaction_type,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            })
            
            self._save_community_data()
            return True
        except Exception as e:
            self.logger.error(f"Error tracking member interaction: {e}")
            return False 