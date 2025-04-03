from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import random

# --- Base Fetcher --- #

class BaseFeedbackFetcher(ABC):
    """Abstract base class for platform-specific feedback fetchers."""

    def __init__(self, platform_id: str):
        self.platform_id = platform_id

    @abstractmethod
    def fetch_metrics(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches performance metrics for a specific post.
        Returns a dictionary of metrics or None if fetching fails.
        The structure of the returned dictionary is platform-specific initially.
        """
        pass

# --- Mock Fetcher Implementations --- #

class MockTwitterFetcher(BaseFeedbackFetcher):
    """Mock fetcher for Twitter feedback data."""
    def __init__(self):
        super().__init__("twitter")

    def fetch_metrics(self, post_id: str) -> Optional[Dict[str, Any]]:
        print(f"[MockFetcher] Fetching Twitter metrics for post: {post_id}")
        # Simulate API call / scraping result
        if random.random() < 0.1: # Simulate occasional failures
            print(f"[MockFetcher] Failed to fetch Twitter metrics for {post_id}")
            return None

        return {
            "impressions": random.randint(500, 5000),
            "likes": random.randint(10, 200),
            "retweets": random.randint(2, 50),
            "replies": random.randint(0, 20),
            "profile_clicks": random.randint(5, 100),
            "url_clicks": random.randint(1, 30),
            "timestamp": datetime.utcnow().isoformat(),
            "post_id": post_id,
            "platform": self.platform_id
        }

class MockInstagramFetcher(BaseFeedbackFetcher):
    """Mock fetcher for Instagram feedback data."""
    def __init__(self):
        super().__init__("instagram")

    def fetch_metrics(self, post_id: str) -> Optional[Dict[str, Any]]:
        print(f"[MockFetcher] Fetching Instagram metrics for post: {post_id}")
        if random.random() < 0.05: # Simulate lower failure rate for Insta mock
            print(f"[MockFetcher] Failed to fetch Instagram metrics for {post_id}")
            return None

        reach = random.randint(1000, 10000)
        impressions = int(reach * random.uniform(1.1, 1.5))
        likes = random.randint(50, 500)

        return {
            "impressions": impressions,
            "reach": reach,
            "likes": likes,
            "comments": random.randint(5, 50),
            "shares": random.randint(2, 40),
            "saves": random.randint(10, 100),
            "profile_visits": random.randint(10, 150),
            "website_clicks": random.randint(0, 20), # Example extra metric
            "timestamp": datetime.utcnow().isoformat(),
            "post_id": post_id,
            "platform": self.platform_id
        }

# --- Factory Function --- #

# Keep a registry of available fetchers
_FETCHERS = {
    "twitter": MockTwitterFetcher,
    "instagram": MockInstagramFetcher,
    # Add other mock fetchers here as needed
    # "facebook": MockFacebookFetcher,
    # "linkedin": MockLinkedInFetcher,
}

def get_fetcher_for_platform(platform: str) -> Optional[BaseFeedbackFetcher]:
    """Factory function to get a fetcher instance for a given platform."""
    fetcher_class = _FETCHERS.get(platform.lower())
    if fetcher_class:
        return fetcher_class()
    else:
        print(f"Warning: No mock fetcher registered for platform: {platform}")
        return None

# Example Usage
if __name__ == "__main__":
    twitter_fetcher = get_fetcher_for_platform("twitter")
    if twitter_fetcher:
        metrics = twitter_fetcher.fetch_metrics("tweetABC")
        print("\nFetched Twitter Metrics:")
        print(metrics)

    insta_fetcher = get_fetcher_for_platform("instagram")
    if insta_fetcher:
        metrics = insta_fetcher.fetch_metrics("instaXYZ")
        print("\nFetched Instagram Metrics:")
        print(metrics)

    unknown_fetcher = get_fetcher_for_platform("unknown_platform")
    # This will print a warning and return None 