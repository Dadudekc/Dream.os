# dream_os/social/feedback/feedback_service.py
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Integrate with actual (mock) fetchers and analyzer
from .fetchers import get_fetcher_for_platform
from .engagement_analyzer import EngagementAnalyzer
# Import the new DB class
from .feedback_db import FeedbackDB, DEFAULT_DB_PATH

# DB_PATH is now managed by FeedbackDB

class FeedbackService:
    """
    Core engine for the Feedback Optimization Loop (FOL).
    Ingests metrics, normalizes, scores, stores (via FeedbackDB),
    and recommends adjustments.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        # Instantiate the analyzer and the database manager
        self.analyzer = EngagementAnalyzer()
        self.db = FeedbackDB(db_path=db_path)

    def _fetch_raw_metrics(self, platform: str, post_id: str) -> Optional[Dict[str, Any]]:
        """Fetches raw metrics from the appropriate platform fetcher."""
        print(f"Fetching raw metrics for {platform} post {post_id}")
        fetcher = get_fetcher_for_platform(platform)
        if fetcher:
            try:
                # Add post_id and platform to metrics if not already present by fetcher
                metrics = fetcher.fetch_metrics(post_id)
                if metrics and "post_id" not in metrics:
                    metrics["post_id"] = post_id
                if metrics and "platform" not in metrics:
                    metrics["platform"] = platform
                return metrics
            except Exception as e:
                print(f"Error fetching metrics via {type(fetcher).__name__} for {post_id}: {e}")
                return None
        else:
             print(f"No fetcher available for platform {platform}")
             return None

    def normalize_metrics(self, raw_data: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """
        Normalizes raw metrics into a common schema for analysis.
        Relies on a basic normalization, potentially improved in Analyzer.
        """
        print(f"Normalizing metrics for {platform} post {raw_data.get('post_id', '?')}")
        # Basic normalization, analyzer might do more sophisticated mapping
        normalized = {
            "post_id": raw_data.get("post_id", "unknown"),
            "platform": platform,
            "raw_metrics": raw_data, # Keep raw for reference
            "impressions": raw_data.get("impressions", 0),
            "reach": raw_data.get("reach", raw_data.get("impressions", 0)),
            "likes": raw_data.get("likes", 0),
            "comments": raw_data.get("comments", raw_data.get("replies", 0)),
            "shares": raw_data.get("shares", raw_data.get("retweets", 0)),
            "saves": raw_data.get("saves", 0),
            "clicks": raw_data.get("profile_clicks", 0) + raw_data.get("url_clicks", 0) + raw_data.get("website_clicks", 0),
            "timestamp": raw_data.get("timestamp", datetime.utcnow().isoformat())
        }
        return normalized

    def score_post_performance(self, normalized_metrics: Dict[str, Any]) -> float:
        """
        Scores the post based on normalized metrics using the EngagementAnalyzer.
        """
        post_id = normalized_metrics.get("post_id", "?")
        print(f"Scoring post performance for {normalized_metrics['platform']} post {post_id}")
        # Use the analyzer's composite scoring method
        score = self.analyzer.calculate_composite_score(normalized_metrics)
        return score

    def update_feedback_db(self, post_id: str, platform: str, normalized_metrics: Dict[str, Any], score: float) -> None:
        """Updates the database using the FeedbackDB instance."""
        print(f"Updating feedback DB via FeedbackDB for post {post_id}")
        try:
            # Use the FeedbackDB method to save
            self.db.save_post_feedback(post_id, platform, normalized_metrics, score)
            print(f"Successfully updated DB for post {post_id} via FeedbackDB")
        except Exception as e:
            # Log or handle exceptions from FeedbackDB save operation if necessary
            print(f"Error during FeedbackDB save for post {post_id}: {e}")

    def recommend_adjustments(self, top_n: int = 5) -> Dict[str, Any]:
        """
        Analyzes overall performance trends using FeedbackDB and recommends adjustments.
        """
        print("Analyzing trends via FeedbackDB and recommending adjustments...")
        recommendations = {
            "general": [],
            "platform_specific": {},
            "top_posts": [],
            "low_posts": []
        }
        try:
            # Get data using FeedbackDB methods
            platform_performance = self.db.get_platform_avg_score()
            top_posts = self.db.get_top_n_posts(n=top_n)
            low_posts = self.db.get_bottom_n_posts(n=top_n)

            # Process the data (similar logic as before, but using DB results)
            if platform_performance:
                rec = "Platform Avg Scores: " + ", ".join([f"{row['platform']}:{row['avg_score']:.1f} ({row['post_count']} posts)" for row in platform_performance])
                recommendations["general"].append(rec)

            recommendations["top_posts"] = [{ "id": post["post_id"], "platform": post["platform"], "score": post["score"]} for post in top_posts]
            if top_posts:
                 recommendations["general"].append(f"Analyze top {len(top_posts)} posts for successful patterns.")

            recommendations["low_posts"] = [{ "id": post["post_id"], "platform": post["platform"], "score": post["score"]} for post in low_posts]
            if low_posts:
                 recommendations["general"].append(f"Review lowest {len(low_posts)} posts for improvement areas.")

            # Use analyzer based on DB results (example using top post)
            if top_posts:
                try:
                    top_post_metrics = top_posts[0]["metrics"] # Metrics are already decoded by FeedbackDB
                    top_post_score = top_posts[0]["score"]
                    # Ensure essential keys are present for analyzer
                    top_post_metrics["platform"] = top_posts[0]["platform"]
                    top_post_metrics["post_id"] = top_posts[0]["post_id"]
                    top_post_metrics["timestamp"] = top_posts[0]["timestamp"]

                    tweaks = self.analyzer.suggest_tweaks(top_post_metrics, top_post_score)
                    if tweaks:
                        recommendations["general"].append(f"Top post ({top_posts[0]['post_id']}) suggests: {', '.join(tweaks)}")
                except (IndexError, KeyError) as e:
                    print(f"Could not analyze top post metrics from DB results: {e}")

        except Exception as e:
            # Catch potential errors during DB interaction or analysis
            print(f"Error during recommendation generation using FeedbackDB: {e}")

        print(f"Generated recommendations: {recommendations}")
        return recommendations

    def run_single_post_feedback(self, platform: str, post_id: str) -> Optional[float]:
        """Runs the feedback loop for a single post."""
        print(f"--- Running feedback for {platform} post: {post_id} ---")
        raw_metrics = self._fetch_raw_metrics(platform, post_id)
        if not raw_metrics:
            print(f"Failed to fetch raw metrics for {post_id}. Skipping.")
            return None

        # Ensure post_id is in metrics before normalization if fetcher didn't add it
        if "post_id" not in raw_metrics:
            raw_metrics["post_id"] = post_id

        normalized_metrics = self.normalize_metrics(raw_metrics, platform)
        score = self.score_post_performance(normalized_metrics)

        # Use the updated method which calls FeedbackDB
        self.update_feedback_db(post_id, platform, normalized_metrics, score)

        # Optionally get detailed analysis including tweaks for this specific post
        analysis = self.analyzer.analyze_post(normalized_metrics)
        print(f"Detailed Analysis: {analysis}")

        print(f"--- Feedback complete for {post_id}. Score: {score} ---")
        return score

    def close_db(self):
        """Explicitly closes the database connection."""
        print("Closing FeedbackService's DB connection...")
        if self.db:
            self.db.close()

    def __del__(self):
        """Ensure DB connection is closed when FeedbackService is destroyed."""
        self.close_db()

# Example Usage (for testing)
if __name__ == "__main__":
    print("Running FeedbackService example with FeedbackDB...")
    # No need to run db_setup separately, FeedbackDB handles table creation
    # db_setup() # Should not be needed if FeedbackDB works correctly

    service = FeedbackService()
    try:
        # Simulate processing for a few posts
        service.run_single_post_feedback("twitter", "tweet_db_1")
        service.run_single_post_feedback("instagram", "insta_db_1")
        service.run_single_post_feedback("twitter", "tweet_db_2")
        service.run_single_post_feedback("instagram", "insta_db_2")
        service.run_single_post_feedback("twitter", "tweet_db_3")

        # Generate overall recommendations based on DB data
        adjustments = service.recommend_adjustments()
        print("\nFinal Recommended Adjustments (from DB):")
        print(json.dumps(adjustments, indent=2))
    finally:
        # Explicitly close connection in example
        service.close_db() 