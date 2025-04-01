import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.SentimentAnalyzer import SentimentAnalyzer
from social.AIChatAgent import AIChatAgent

class UnifiedPostManager:
    """
    Manages post creation, scheduling, and distribution across multiple social platforms.
    Provides a unified interface for content management and cross-platform posting.
    """
    
    def __init__(self):
        """Initialize the unified post manager."""
        self.logger = logging.getLogger(__name__)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.ai_agent = AIChatAgent()
        self.post_history = self._load_post_history()
    
    def _load_post_history(self) -> Dict[str, Any]:
        """Load post history from file."""
        history_path = "data/post_history.json"
        if os.path.exists(history_path):
            try:
                with open(history_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading post history: {e}")
        return {"posts": []}
    
    def _save_post_history(self):
        """Save post history to file."""
        history_path = "data/post_history.json"
        try:
            os.makedirs(os.path.dirname(history_path), exist_ok=True)
            with open(history_path, "w") as f:
                json.dump(self.post_history, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving post history: {e}")
    
    def post_to_platform(self, platform_id: str, content: Dict[str, Any], strategy: Any) -> Dict[str, Any]:
        """
        Post content to a specific platform using its strategy.
        
        Args:
            platform_id (str): Platform identifier
            content (Dict): Content to post
            strategy: Platform-specific strategy instance
            
        Returns:
            Dict: Results of the posting operation
        """
        result = {
            "success": False,
            "platform": platform_id,
            "timestamp": datetime.now().isoformat(),
            "post_id": None,
            "metrics": {},
            "error": None
        }
        
        try:
            # Analyze sentiment if text content is present
            if "text" in content:
                sentiment_score = self.sentiment_analyzer.analyze(content["text"])
                content["sentiment_score"] = sentiment_score
            
            # Adapt content for platform if needed
            adapted_content = self._adapt_content_for_platform(content, platform_id)
            
            # Use platform strategy to post
            if hasattr(strategy, "post_content"):
                post_result = strategy.post_content(adapted_content)
                if post_result.get("success", False):
                    result.update({
                        "success": True,
                        "post_id": post_result.get("post_id"),
                        "metrics": post_result.get("metrics", {})
                    })
                    
                    # Add to post history
                    self.post_history["posts"].append({
                        "platform": platform_id,
                        "content": adapted_content,
                        "timestamp": result["timestamp"],
                        "post_id": result["post_id"],
                        "initial_metrics": result["metrics"]
                    })
                    self._save_post_history()
                else:
                    result["error"] = post_result.get("error", "Unknown error")
            else:
                result["error"] = f"Platform {platform_id} strategy does not support posting"
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"Error posting to {platform_id}: {e}")
        
        return result
    
    def _adapt_content_for_platform(self, content: Dict[str, Any], platform_id: str) -> Dict[str, Any]:
        """
        Adapt content for specific platform requirements.
        
        Args:
            content (Dict): Original content
            platform_id (str): Target platform
            
        Returns:
            Dict: Adapted content
        """
        adapted = content.copy()
        
        # Platform-specific adaptations
        if platform_id == "twitter":
            # Twitter character limit
            if "text" in adapted:
                adapted["text"] = adapted["text"][:280]
        elif platform_id == "instagram":
            # Instagram requires at least one image
            if "images" not in adapted and "video" not in adapted:
                self.logger.warning("Instagram posts require media content")
        elif platform_id == "youtube":
            # YouTube requires video content
            if "video" not in adapted:
                self.logger.warning("YouTube posts require video content")
        elif platform_id == "tiktok":
            # TikTok requires video in correct format
            if "video" not in adapted:
                self.logger.warning("TikTok posts require video content")
        
        return adapted
    
    def schedule_post(self, content: Dict[str, Any], platforms: List[str], schedule_time: datetime) -> str:
        """
        Schedule a post for later publication.
        
        Args:
            content (Dict): Content to post
            platforms (List): Target platforms
            schedule_time (datetime): When to post
            
        Returns:
            str: Schedule ID
        """
        schedule_id = f"schedule_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        schedule_path = f"data/scheduled_posts/{schedule_id}.json"
        os.makedirs(os.path.dirname(schedule_path), exist_ok=True)
        
        schedule_data = {
            "id": schedule_id,
            "content": content,
            "platforms": platforms,
            "schedule_time": schedule_time.isoformat(),
            "status": "scheduled"
        }
        
        try:
            with open(schedule_path, "w") as f:
                json.dump(schedule_data, f, indent=4)
            self.logger.info(f"Post scheduled with ID: {schedule_id}")
        except Exception as e:
            self.logger.error(f"Error scheduling post: {e}")
            return None
        
        return schedule_id
    
    def get_scheduled_posts(self) -> List[Dict[str, Any]]:
        """Get list of scheduled posts."""
        scheduled = []
        schedule_dir = "data/scheduled_posts"
        
        if os.path.exists(schedule_dir):
            for filename in os.listdir(schedule_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(schedule_dir, filename), "r") as f:
                            scheduled.append(json.load(f))
                    except Exception as e:
                        self.logger.error(f"Error loading scheduled post {filename}: {e}")
        
        return scheduled
    
    def cancel_scheduled_post(self, schedule_id: str) -> bool:
        """Cancel a scheduled post."""
        schedule_path = f"data/scheduled_posts/{schedule_id}.json"
        
        if os.path.exists(schedule_path):
            try:
                os.remove(schedule_path)
                self.logger.info(f"Cancelled scheduled post: {schedule_id}")
                return True
            except Exception as e:
                self.logger.error(f"Error cancelling scheduled post: {e}")
        
        return False
    
    def get_post_analytics(self, post_id: str, platform_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analytics for a specific post.
        
        Args:
            post_id (str): Post identifier
            platform_id (str): Platform identifier
            
        Returns:
            Dict or None: Post analytics if available
        """
        for post in self.post_history["posts"]:
            if post.get("post_id") == post_id and post.get("platform") == platform_id:
                return {
                    "initial_metrics": post.get("initial_metrics", {}),
                    "current_metrics": self._get_current_metrics(post_id, platform_id),
                    "platform": platform_id,
                    "timestamp": post.get("timestamp"),
                    "content": post.get("content")
                }
        return None
    
    def _get_current_metrics(self, post_id: str, platform_id: str) -> Dict[str, Any]:
        """Get current metrics for a post from its platform."""
        # This would typically call platform-specific APIs
        # For now, return placeholder metrics
        return {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0
        }
    
    def generate_content_ideas(self, topic: str, platform_id: str = None) -> List[Dict[str, Any]]:
        """
        Generate content ideas using AI.
        
        Args:
            topic (str): Topic to generate ideas for
            platform_id (str, optional): Target platform for specific formats
            
        Returns:
            List: Generated content ideas
        """
        try:
            prompt = f"Generate content ideas about {topic}"
            if platform_id:
                prompt += f" specifically for {platform_id}"
            
            response = self.ai_agent.ask(
                prompt=prompt,
                metadata={"purpose": "content_ideas", "platform": platform_id}
            )
            
            if isinstance(response, list):
                return response
            return []
        except Exception as e:
            self.logger.error(f"Error generating content ideas: {e}")
            return [] 
