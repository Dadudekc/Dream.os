import logging
from typing import Dict, Tuple, List

logger = logging.getLogger(__name__)

class RateLimitManager:
    """
    Manages rate limits for social media platforms.
    Provides functionality to adjust rate limits based on feedback.
    """
    
    def __init__(self):
        self._rate_limits = {}
        self._initialize_default_limits()
    
    def _initialize_default_limits(self):
        """Initialize default rate limits for platforms."""
        self._rate_limits = {
            "twitter": {"post": {"cooldown": 60, "daily_max": 300}, "follow": {"cooldown": 10, "daily_max": 1000}},
            "linkedin": {"post": {"cooldown": 600, "daily_max": 20}, "message": {"cooldown": 30, "daily_max": 100}},
            "facebook": {"post": {"cooldown": 300, "daily_max": 50}},
            "instagram": {"post": {"cooldown": 3600, "daily_max": 10}, "follow": {"cooldown": 10, "daily_max": 200}},
            "reddit": {"post": {"cooldown": 600, "daily_max": 25}},
            "stocktwits": {"post": {"cooldown": 60, "daily_max": 200}}
        }
    
    def get_rate_limits(self) -> Dict:
        """Get current rate limits."""
        return self._rate_limits
    
    def adjust_rate_limit(self, platform: str, action: str, cooldown_multiplier: float = 1.5) -> None:
        """
        Adjust rate limit for a platform/action pair.
        
        Args:
            platform: Platform name (e.g. 'linkedin')
            action: Action type (e.g. 'post')
            cooldown_multiplier: Factor to multiply current cooldown by
        """
        if platform not in self._rate_limits or action not in self._rate_limits[platform]:
            logger.warning(f"No rate limits defined for {platform}:{action}")
            return
            
        current = self._rate_limits[platform][action]["cooldown"]
        new_cooldown = min(current * cooldown_multiplier, 3600)  # Cap at 1 hour
        self._rate_limits[platform][action]["cooldown"] = new_cooldown
        
        logger.warning(f"Increased cooldown for {platform}:{action} to {new_cooldown} sec")
    
    def adjust_from_failures(self, failed_tags: List[Tuple[str, int]]) -> None:
        """
        Adjust rate limits based on failure patterns.
        
        Args:
            failed_tags: List of (tag, count) tuples from failure analysis
        """
        for tag, count in failed_tags:
            # Map tag to platform/action
            platform = None
            action = None
            
            if "linkedin" in tag:
                platform = "linkedin"
                action = "post"
            elif "twitter" in tag:
                platform = "twitter"
                action = "post"
            # Add more platform mappings as needed
            
            if platform and action:
                self.adjust_rate_limit(platform, action)

# Singleton instance
rate_limit_manager = RateLimitManager() 