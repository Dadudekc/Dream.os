import sqlite3
from datetime import datetime
import os
import logging
from social.strategies.config_loader import get_env_or_config

# ------------------------------------------------------
# Logger Setup
# ------------------------------------------------------
logger = logging.getLogger("UnifiedContextEngine")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)

# ------------------------------------------------------
# UnifiedContextEngine (ContextDB v2)
# ------------------------------------------------------
class UnifiedContextEngine:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_env_or_config("SOCIAL_DB_PATH")

        if not self.db_path:
            raise ValueError("❌ SOCIAL_DB_PATH not set in .env or config file.")

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Return dict-like rows
            self.create_tables()
            logger.info(f" Connected to DB: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f" Failed to connect to DB: {e}")
            raise

    # ------------------------------------------------------
    # Table Creation
    # ------------------------------------------------------
    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    post_content TEXT NOT NULL,
                    post_time TEXT NOT NULL,
                    engagement INTEGER DEFAULT 0,
                    sentiment TEXT DEFAULT 'neutral'
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS engagements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    action_time TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY (post_id) REFERENCES posts (id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    action TEXT NOT NULL,
                    limit_count INTEGER DEFAULT 0,
                    last_reset TEXT NOT NULL
                )
            """)
        logger.info(" Tables ensured: posts, engagements, rate_limits")

    # ------------------------------------------------------
    # Core Post Logging with Sentiment
    # ------------------------------------------------------
    def log_post(self, platform, post_content, engagement=0, sentiment="neutral"):
        post_time = datetime.utcnow().isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO posts (platform, post_content, post_time, engagement, sentiment)
                VALUES (?, ?, ?, ?, ?)
            """, (platform, post_content, post_time, engagement, sentiment))
        logger.info(f" Post logged on {platform} | Sentiment: {sentiment}")

    def fetch_recent_posts(self, platform=None, limit=10):
        cursor = self.conn.cursor()
        if platform:
            cursor.execute("""
                SELECT * FROM posts WHERE platform = ?
                ORDER BY post_time DESC LIMIT ?
            """, (platform, limit))
        else:
            cursor.execute("""
                SELECT * FROM posts ORDER BY post_time DESC LIMIT ?
            """, (limit,))
        results = cursor.fetchall()
        logger.debug(f" Fetched {len(results)} posts from {platform or 'all platforms'}")
        return results

    def fetch_last_post_content(self, platform):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT post_content FROM posts WHERE platform = ?
            ORDER BY post_time DESC LIMIT 1
        """, (platform,))
        result = cursor.fetchone()
        logger.info(f" Last post content fetched for {platform}")
        return result["post_content"] if result else None

    # ------------------------------------------------------
    # Engagement Logging
    # ------------------------------------------------------
    def log_engagement(self, post_id, action, details=""):
        action_time = datetime.utcnow().isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO engagements (post_id, action, action_time, details)
                VALUES (?, ?, ?, ?)
            """, (post_id, action, action_time, details))
        logger.info(f" Engagement logged | Post ID: {post_id} | Action: {action}")

    def fetch_engagements_for_post(self, post_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM engagements WHERE post_id = ?
        """, (post_id,))
        results = cursor.fetchall()
        logger.debug(f" Fetched {len(results)} engagements for post ID {post_id}")
        return results

    # ------------------------------------------------------
    # Rate Limits Tracking
    # ------------------------------------------------------
    def get_rate_limit(self, platform, action):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM rate_limits WHERE platform = ? AND action = ?
        """, (platform, action))
        result = cursor.fetchone()
        return result

    def update_rate_limit(self, platform, action, limit_count, last_reset=None):
        last_reset = last_reset or datetime.utcnow().isoformat()

        existing = self.get_rate_limit(platform, action)
        with self.conn:
            if existing:
                self.conn.execute("""
                    UPDATE rate_limits
                    SET limit_count = ?, last_reset = ?
                    WHERE platform = ? AND action = ?
                """, (limit_count, last_reset, platform, action))
            else:
                self.conn.execute("""
                    INSERT INTO rate_limits (platform, action, limit_count, last_reset)
                    VALUES (?, ?, ?, ?)
                """, (platform, action, limit_count, last_reset))

        logger.info(f" Rate limit updated: {platform} {action} => {limit_count}")

    # ------------------------------------------------------
    # Sentiment Update for Feedback Loops
    # ------------------------------------------------------
    def update_sentiment(self, post_id, sentiment):
        with self.conn:
            self.conn.execute("""
                UPDATE posts
                SET sentiment = ?
                WHERE id = ?
            """, (sentiment, post_id))
        logger.info(f"🧠 Sentiment updated for post ID {post_id} => {sentiment}")

    # ------------------------------------------------------
    # Close Connection
    # ------------------------------------------------------
    def close(self):
        self.conn.close()
        logger.info(" DB connection closed")

# ------------------------------------------------------
# Example Usage (Optional Testing)
# ------------------------------------------------------
if __name__ == "__main__":
    db = UnifiedContextEngine()

    # Example Post Logging
    db.log_post("twitter", "Testing the UnifiedContextEngine upgrade!", sentiment="positive")

    # Engagement
    db.log_engagement(post_id=1, action="like", details="Liked by user123")

    # Rate Limits
    db.update_rate_limit("twitter", "post", limit_count=5)
    rate_limit = db.get_rate_limit("twitter", "post")
    print(f"Rate limit data: {rate_limit}")

    # Sentiment
    db.update_sentiment(post_id=1, sentiment="very_positive")

    # Fetch posts
    recent_posts = db.fetch_recent_posts(platform="twitter", limit=5)
    print("Recent posts:", recent_posts)

    db.close()
