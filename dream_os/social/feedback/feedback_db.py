# dream_os/social/feedback/feedback_db.py

import sqlite3
import json
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

# Define the default path relative to this file's location
DEFAULT_DB_PATH = Path(__file__).parent / "feedback_db.sqlite"

class FeedbackDB:
    """Manages persistence of post feedback data in an SQLite database."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        """Initialize the database connection and ensure the table exists."""
        self.db_path = db_path
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Use Row factory for dict-like access
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        """Creates the post_feedback table if it doesn't exist."""
        try:
            with self.conn:
                self.conn.execute("""
                CREATE TABLE IF NOT EXISTS post_feedback (
                    post_id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    metrics_json TEXT, -- Store normalized metrics (without raw) as JSON string
                    score REAL,        -- Use REAL for floating point numbers
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                # Optional: Add indices (Consider adding based on query patterns)
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_platform_timestamp ON post_feedback (platform, timestamp);")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_score ON post_feedback (score);")
        except sqlite3.Error as e:
            print(f"Database error during table creation: {e}")
            # Re-raise or handle appropriately
            raise

    def save_post_feedback(self, post_id: str, platform: str, metrics: Dict[str, Any], score: float):
        """Saves or replaces feedback for a given post."""
        metrics_to_store = {k: v for k, v in metrics.items() if k != 'raw_metrics'}
        timestamp = metrics.get("timestamp", datetime.utcnow().isoformat())
        try:
            with self.conn:
                self.conn.execute("""
                INSERT OR REPLACE INTO post_feedback (post_id, platform, metrics_json, score, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    post_id,
                    platform,
                    json.dumps(metrics_to_store),
                    score,
                    timestamp
                ))
        except sqlite3.Error as e:
            print(f"Database error saving feedback for post {post_id}: {e}")
            # Consider logging this error more formally

    def fetch_recent_feedback(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetches the most recent feedback entries."""
        try:
            with self.conn:
                cursor = self.conn.execute("""
                SELECT post_id, platform, metrics_json, score, timestamp
                FROM post_feedback
                ORDER BY timestamp DESC
                LIMIT ?
                """, (limit,))
                results = []
                for row in cursor.fetchall():
                    try:
                        metrics_data = json.loads(row["metrics_json"]) if row["metrics_json"] else {}
                        results.append({
                            "post_id": row["post_id"],
                            "platform": row["platform"],
                            "metrics": metrics_data,
                            "score": row["score"],
                            "timestamp": row["timestamp"],
                        })
                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode metrics JSON for post {row['post_id']}")
                        continue # Skip malformed records
                return results
        except sqlite3.Error as e:
            print(f"Database error fetching recent feedback: {e}")
            return []

    def get_post_score(self, post_id: str) -> Optional[float]:
        """Retrieves the score for a specific post."""
        try:
            with self.conn:
                cursor = self.conn.execute(
                    "SELECT score FROM post_feedback WHERE post_id = ?", (post_id,)
                )
                result = cursor.fetchone()
                return result["score"] if result else None
        except sqlite3.Error as e:
            print(f"Database error fetching score for post {post_id}: {e}")
            return None

    def get_platform_avg_score(self) -> List[Dict[str, Any]]:
        """Calculates the average score per platform."""
        try:
            with self.conn:
                cursor = self.conn.execute("""
                    SELECT platform, AVG(score) as avg_score, COUNT(post_id) as post_count
                    FROM post_feedback
                    WHERE score IS NOT NULL
                    GROUP BY platform
                    ORDER BY avg_score DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Database error fetching platform average scores: {e}")
            return []

    def get_top_n_posts(self, n: int = 5) -> List[Dict[str, Any]]:
        """Fetches the top N posts by score."""
        return self._get_posts_ordered_by_score("DESC", n)

    def get_bottom_n_posts(self, n: int = 5) -> List[Dict[str, Any]]:
        """Fetches the bottom N posts by score."""
        return self._get_posts_ordered_by_score("ASC", n)

    def _get_posts_ordered_by_score(self, order: str, limit: int) -> List[Dict[str, Any]]:
        """Helper to fetch posts ordered by score."""
        if order.upper() not in ["ASC", "DESC"]:
            raise ValueError("Order must be ASC or DESC")
        try:
            with self.conn:
                cursor = self.conn.execute(f"""
                    SELECT post_id, platform, metrics_json, score, timestamp
                    FROM post_feedback
                    WHERE score IS NOT NULL
                    ORDER BY score {order}
                    LIMIT ?
                """, (limit,))
                results = []
                for row in cursor.fetchall():
                     try:
                        metrics_data = json.loads(row["metrics_json"]) if row["metrics_json"] else {}
                        results.append({
                            "post_id": row["post_id"],
                            "platform": row["platform"],
                            "metrics": metrics_data,
                            "score": row["score"],
                            "timestamp": row["timestamp"],
                        })
                     except json.JSONDecodeError:
                        print(f"Warning: Could not decode metrics JSON for post {row['post_id']}")
                        continue # Skip malformed records
                return results
        except sqlite3.Error as e:
            print(f"Database error fetching posts ordered by score: {e}")
            return []

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            print("FeedbackDB connection closed.")

    def __del__(self):
        """Ensure connection is closed when the object is destroyed."""
        self.close()

# Example Usage (can be run for testing)
if __name__ == "__main__":
    print("Testing FeedbackDB...")
    # Uses the default path: dream_os/social/feedback/feedback_db.sqlite
    db = FeedbackDB()

    # Mock data
    mock_metrics_1 = {"platform": "twitter", "likes": 10, "comments": 1, "shares": 2, "timestamp": datetime.utcnow().isoformat()}
    mock_metrics_2 = {"platform": "instagram", "likes": 50, "comments": 5, "saves": 10, "timestamp": datetime.utcnow().isoformat()}

    print("\nSaving mock feedback...")
    db.save_post_feedback("test_tweet_1", "twitter", mock_metrics_1, 65.3)
    db.save_post_feedback("test_insta_1", "instagram", mock_metrics_2, 88.1)
    db.save_post_feedback("test_tweet_2", "twitter", {**mock_metrics_1, "likes": 5}, 42.0) # Lower score

    print("\nFetching recent feedback (limit 5)...")
    recent = db.fetch_recent_feedback(limit=5)
    print(json.dumps(recent, indent=2))

    print(f"\nFetching score for test_tweet_1...")
    score = db.get_post_score("test_tweet_1")
    print(f"Score: {score}")

    print(f"\nFetching score for non_existent_post...")
    score = db.get_post_score("non_existent_post")
    print(f"Score: {score}")

    print("\nFetching platform average scores...")
    avg_scores = db.get_platform_avg_score()
    print(json.dumps(avg_scores, indent=2))

    print("\nFetching top 2 posts...")
    top_posts = db.get_top_n_posts(n=2)
    print(json.dumps(top_posts, indent=2))

    print("\nFetching bottom 2 posts...")
    bottom_posts = db.get_bottom_n_posts(n=2)
    print(json.dumps(bottom_posts, indent=2))

    print("\nClosing DB connection...")
    db.close()
    print("\nFeedbackDB Test Complete.") 