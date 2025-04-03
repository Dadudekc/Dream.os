# dream_os/social/feedback/db_setup.py
import sqlite3
import os

# Use the same DB path as defined in feedback_service
# Ideally, this path would be managed by a central config
DB_PATH = "feedback_db.sqlite"
DB_DIR = os.path.dirname(__file__) or "."
FULL_DB_PATH = os.path.join(DB_DIR, DB_PATH)

def setup_database():
    """Creates the feedback_db.sqlite database and the post_feedback table if they don't exist."""
    print(f"Setting up database at: {FULL_DB_PATH}")
    try:
        # Ensure the directory exists (though it should if this script is in the right place)
        os.makedirs(DB_DIR, exist_ok=True)

        conn = sqlite3.connect(FULL_DB_PATH)
        cursor = conn.cursor()

        # Create table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_feedback (
            post_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            metrics TEXT, -- Store normalized metrics as JSON string
            score REAL,   -- Use REAL for floating point numbers
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Optional: Create indices for faster lookups if needed later
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_platform_timestamp ON post_feedback (platform, timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_score ON post_feedback (score);")

        conn.commit()
        print("Database table 'post_feedback' created or already exists.")

    except sqlite3.Error as e:
        print(f"Database setup error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during DB setup: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    setup_database() 