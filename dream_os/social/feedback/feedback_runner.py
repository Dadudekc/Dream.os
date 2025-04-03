import time
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta

from .feedback_service import FeedbackService
# Import the DB class
from .feedback_db import FeedbackDB, DEFAULT_DB_PATH
# Import the real StrategyUpdater
from .strategy_updater import StrategyUpdater, DEFAULT_CONFIG_DIR

# --- Mock Components (Keep StrategyUpdater mock for now) --- #

# Remove MockRecentPostRegistry
# class MockRecentPostRegistry:
# ... (removed) ...

# --- Real DB-backed Registry --- #

class DBRecentPostRegistry:
    """Registry that fetches recent posts from the FeedbackDB."""
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        # Note: Consider sharing the DB instance/connection pool if performance becomes an issue
        self.db = FeedbackDB(db_path=db_path)

    def get_posts_for_feedback(self, limit: int = 10, lookback_hours: int = 24*7) -> List[Dict[str, str]]:
        """Fetches recent posts from the DB, potentially filtering by last update time."""
        print(f"[DBRegistry] Getting up to {limit} posts for feedback (lookback: {lookback_hours}h)...")
        # Simplified logic: Fetch the most recent N posts regardless of update time
        # A more robust implementation would:
        # 1. Query the actual source of published posts (e.g., another table/system).
        # 2. Join with feedback_db to find posts not updated within `lookback_hours`.
        # For now, just fetch recent *feedback entries* as a proxy for recent posts.
        recent_feedback = self.db.fetch_recent_feedback(limit=limit * 2) # Fetch more to potentially find unique posts

        # Extract unique post_id/platform pairs
        unique_posts = {}
        for entry in recent_feedback:
            key = (entry["platform"], entry["post_id"])
            if key not in unique_posts:
                unique_posts[key] = {"platform": entry["platform"], "post_id": entry["post_id"]}
                if len(unique_posts) >= limit:
                    break

        posts = list(unique_posts.values())
        print(f"[DBRegistry] Found {len(posts)} unique posts from recent feedback entries.")
        return posts

    def close_db(self):
        if self.db:
            self.db.close()

    def __del__(self):
        self.close_db()

# --- Feedback Loop Runner --- #

class FeedbackLoopRunner:
    """
    Orchestrates the Feedback Optimization Loop.
    Fetches posts (via DBRegistry), runs feedback analysis via FeedbackService,
    and triggers strategy updates (via StrategyUpdater).
    """
    def __init__(self):
        self.feedback_service = FeedbackService() # Uses default DB path
        # Use the DB-backed registry
        self.post_registry = DBRecentPostRegistry() # Uses default DB path
        # Use the real StrategyUpdater
        self.strategy_updater = StrategyUpdater() # Uses default config dir

    def run_loop(self, post_limit: int = 10):
        """Runs the full feedback loop cycle."""
        print("===== Starting Feedback Optimization Loop (Using DB Registry & Strategy Updater) ====")
        start_time = time.time()

        # 1. Get posts needing feedback from DBRegistry
        # Using default lookback for now
        posts_to_process = self.post_registry.get_posts_for_feedback(limit=post_limit)
        if not posts_to_process:
            print("No posts found requiring feedback analysis from DB registry.")
            print("===== Feedback Optimization Loop Complete (No Posts) ====")
            return

        print(f"Found {len(posts_to_process)} posts to analyze via DB registry.")

        # 2. Process feedback for each post (using FeedbackService, which now uses FeedbackDB)
        processed_count = 0
        failed_count = 0
        for post_info in posts_to_process:
            platform = post_info.get("platform")
            post_id = post_info.get("post_id")
            if platform and post_id:
                try:
                    score = self.feedback_service.run_single_post_feedback(platform, post_id)
                    if score is not None:
                        processed_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    print(f"!! Unexpected error processing post {platform}:{post_id}: {e}")
                    failed_count += 1
            else:
                print(f"Skipping invalid post info: {post_info}")
                failed_count += 1
            time.sleep(0.2) # Slightly smaller delay

        print(f"\nFeedback processing complete. Processed: {processed_count}, Failed/Skipped: {failed_count}")

        # 3. Generate overall recommendations (using FeedbackService, which uses FeedbackDB)
        adjustments = self.feedback_service.recommend_adjustments()

        # 4. Apply recommendations using the real StrategyUpdater
        self.strategy_updater.apply(adjustments)

        end_time = time.time()
        duration = end_time - start_time
        print(f"===== Feedback Optimization Loop Complete ({duration:.2f}s) ====")

    def close_services(self):
        """Close down services like DB connections."""
        print("Closing FeedbackLoopRunner services...")
        if self.feedback_service:
            self.feedback_service.close_db()
        if self.post_registry:
             # Ensure registry closes its DB connection if it owns one
             if hasattr(self.post_registry, 'close_db') and callable(self.post_registry.close_db):
                 self.post_registry.close_db()

    def __del__(self):
        self.close_services()

# Example Usage
if __name__ == "__main__":
    print("Running FeedbackLoopRunner example with DBRegistry and StrategyUpdater...")
    # FeedbackDB handles table creation, no need for explicit setup run usually.

    runner = FeedbackLoopRunner()
    try:
        # Run the loop - this will now potentially modify config JSON files
        # based on the mock feedback data generated and analyzed.
        runner.run_loop(post_limit=8)
    finally:
        # Ensure connections are closed cleanly
        runner.close_services()
    print("\nPlease check the JSON files in configs/strategies/ for updates.") 