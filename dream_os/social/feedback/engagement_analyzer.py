import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Constants for analysis - These might become configurable
DEFAULT_LOOKBACK_HOURS = 24
VELOCITY_WINDOW_HOURS = 1
DECAY_HALFLIFE_HOURS = 6 # Example: Engagement value halves every 6 hours

class EngagementAnalyzer:
    """
    Analyzes normalized engagement metrics to calculate rates, velocity,
    scores, and suggest potential strategy tweaks.
    """

    def calculate_engagement_rate(self, metrics: Dict[str, Any], rate_type: str = "reach") -> float:
        """
        Calculates engagement rate based on reach or impressions.
        Engagement = (Likes + Comments + Shares + Saves + Clicks) / Base
        """
        base_metric = metrics.get(rate_type, 0)
        if base_metric <= 0:
            return 0.0

        interactions = (
            metrics.get("likes", 0) +
            metrics.get("comments", 0) +
            metrics.get("shares", 0) +
            metrics.get("saves", 0) +
            metrics.get("clicks", 0)
        )

        return round((interactions / base_metric) * 100, 2) # Return as percentage

    def calculate_velocity(self, metrics: Dict[str, Any], current_time: Optional[datetime] = None) -> float:
        """
        Calculates engagement velocity (interactions per hour) since the post time.
        Assumes metrics contain a timestamp.
        """
        if current_time is None:
            current_time = datetime.utcnow()

        post_timestamp_str = metrics.get("timestamp")
        if not post_timestamp_str:
            return 0.0

        try:
            post_time = datetime.fromisoformat(post_timestamp_str.replace('Z', '+00:00'))
            if post_time.tzinfo is None:
                 post_time = post_time.replace(tzinfo=timezone.utc) # Assume UTC if no timezone
            # Ensure current_time is offset-aware for comparison
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)

        except (ValueError, TypeError):
            print(f"Warning: Could not parse timestamp {post_timestamp_str}")
            return 0.0

        time_diff: timedelta = current_time - post_time
        hours_since_post = max(time_diff.total_seconds() / 3600, 1 / 60) # Avoid division by zero, min 1 minute

        interactions = (
            metrics.get("likes", 0) +
            metrics.get("comments", 0) +
            metrics.get("shares", 0) +
            metrics.get("saves", 0) +
            metrics.get("clicks", 0)
        )

        return round(interactions / hours_since_post, 2)

    # Placeholder - Requires historical data or multiple data points for a post
    def calculate_decay(self, post_id: str, historical_metrics: List[Dict[str, Any]]) -> Optional[float]:
        """
        Estimates an engagement decay factor based on historical metrics for the post.
        Requires time-series data, not just a single snapshot.
        Placeholder: Needs implementation with actual historical data access.
        """
        print(f"Placeholder: Decay calculation for {post_id} requires historical data.")
        # Example logic:
        # 1. Sort historical_metrics by timestamp.
        # 2. Calculate velocity between intervals.
        # 3. Fit an exponential decay curve or use a simpler heuristic.
        # decay_factor = math.exp(-math.log(2) * hours_elapsed / DECAY_HALFLIFE_HOURS)
        return None

    # Placeholder - Requires data from multiple platforms for the same campaign/content piece
    def calculate_cross_platform_resonance(self, content_id: str, multi_platform_metrics: List[Dict[str, Any]]) -> float:
        """
        Calculates a score indicating how well content resonates across different platforms.
        Requires linking posts across platforms via a common content_id.
        Placeholder: Needs implementation with cross-platform data access.
        """
        print(f"Placeholder: Cross-platform resonance for {content_id} requires linked data.")
        # Example logic:
        # 1. Aggregate key metrics (e.g., engagement rate) across platforms.
        # 2. Calculate variance or standard deviation to measure consistency.
        # 3. High average + low variance = high resonance.
        return 0.0

    def calculate_composite_score(self, metrics: Dict[str, Any], weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calculates a weighted composite score based on normalized metrics.
        Refines the basic scoring in FeedbackService.
        """
        if weights is None:
            # Default weights - can be tuned per platform or campaign goal
            weights = {
                "engagement_rate_reach": 0.4, # Engagement relative to reach
                "velocity": 0.3,              # How quickly it gains traction
                "saves": 0.15,                # Indicates high value content
                "shares": 0.1,                # Amplification factor
                "comments": 0.05              # Deeper engagement signal
                # Decay/Resonance could be added here when available
            }

        score = 0.0
        engagement_rate = self.calculate_engagement_rate(metrics, rate_type="reach")
        velocity = self.calculate_velocity(metrics)

        score += engagement_rate * weights.get("engagement_rate_reach", 0)
        score += math.log1p(velocity) * weights.get("velocity", 0) # Log transform velocity as it can vary widely
        score += math.log1p(metrics.get("saves", 0)) * weights.get("saves", 0)
        score += math.log1p(metrics.get("shares", 0)) * weights.get("shares", 0)
        score += math.log1p(metrics.get("comments", 0)) * weights.get("comments", 0)

        # Normalize to a 0-100 scale (approximate)
        # This normalization might need adjustment based on typical score ranges
        normalized_score = min(max(score * 10, 0), 100) # Simple scaling/clamping

        return round(normalized_score, 2)

    # Placeholder - Needs more sophisticated rules/ML model
    def suggest_tweaks(self, metrics: Dict[str, Any], score: float) -> List[str]:
        """
        Analyzes metrics and score to suggest potential strategy tweaks.
        Placeholder: Implement rule-based or simple ML approach.
        """
        suggestions = []
        platform = metrics.get("platform", "unknown")
        engagement_rate = self.calculate_engagement_rate(metrics)
        velocity = self.calculate_velocity(metrics)

        # Example rules:
        if score < 30:
            suggestions.append("Low score: Review content format, topic relevance, and posting time.")
        elif score > 75:
            suggestions.append("High score: Analyze what worked (topic, format, time) and replicate.")

        if engagement_rate < 1.0: # Threshold depends heavily on platform/industry
            suggestions.append("Low engagement rate: Improve call-to-action, visual appeal, or audience targeting.")

        if velocity < 5 and score < 50: # Low interactions per hour and mediocre score
            suggestions.append("Low velocity: Consider boosting the post or improving initial hook/visibility.")

        # Platform specific suggestions (example)
        if platform == "instagram" and metrics.get("saves", 0) > metrics.get("likes", 0) * 0.1:
            suggestions.append("High saves on Instagram: Content is valuable; create more save-worthy posts (e.g., tutorials, tips).")
        if platform == "twitter" and metrics.get("shares", 0) > metrics.get("likes", 0) * 0.2: # High retweet ratio
            suggestions.append("High retweets on Twitter: Content is shareable; focus on strong opinions, questions, or breaking news.")

        if not suggestions and score > 50:
             suggestions.append("Solid performance. Continue monitoring trends.")

        return suggestions

    def analyze_post(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs a full analysis on a single post's metrics.
        """
        analysis_result = {
            "post_id": metrics.get("post_id", "unknown"), # Ensure post_id is passed in metrics
            "platform": metrics.get("platform", "unknown"),
            "engagement_rate_reach": self.calculate_engagement_rate(metrics, "reach"),
            "engagement_rate_impressions": self.calculate_engagement_rate(metrics, "impressions"),
            "velocity": self.calculate_velocity(metrics),
            # "decay_factor": self.calculate_decay(post_id, []), # Needs historical data
            # "cross_platform_resonance": self.calculate_cross_platform_resonance(content_id, []), # Needs linked data
        }
        # Calculate score using the analyzer's own method for consistency
        composite_score = self.calculate_composite_score(metrics)
        analysis_result["score"] = composite_score
        analysis_result["suggested_tweaks"] = self.suggest_tweaks(metrics, composite_score)

        return analysis_result

# Example Usage (for testing)
if __name__ == "__main__":
    analyzer = EngagementAnalyzer()

    # Mock normalized metrics (similar to what FeedbackService produces)
    mock_insta_metrics = {
        "post_id": "insta456",
        "platform": "instagram",
        "raw_metrics": {}, # Omitted for brevity
        "impressions": 2500,
        "reach": 2000,
        "likes": 150,
        "comments": 12,
        "shares": 8,
        "saves": 25,
        "clicks": 30,
        "timestamp": (datetime.utcnow() - timedelta(hours=4)).isoformat() # Posted 4 hours ago
    }

    mock_tweet_metrics = {
        "post_id": "tweet123",
        "platform": "twitter",
        "raw_metrics": {}, # Omitted for brevity
        "impressions": 1500,
        "reach": 1500,
        "likes": 75,
        "comments": 5, # Mapped from replies
        "shares": 15, # Mapped from retweets
        "saves": 0, # N/A for Twitter typically
        "clicks": 30, # Profile + URL clicks
        "timestamp": (datetime.utcnow() - timedelta(hours=12)).isoformat() # Posted 12 hours ago
    }

    insta_analysis = analyzer.analyze_post(mock_insta_metrics)
    print("--- Instagram Post Analysis ---")
    print(json.dumps(insta_analysis, indent=2))

    tweet_analysis = analyzer.analyze_post(mock_tweet_metrics)
    print("\n--- Twitter Post Analysis ---")
    print(json.dumps(tweet_analysis, indent=2)) 