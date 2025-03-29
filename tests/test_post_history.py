import unittest
import os
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from social.data.post_history import PostHistory

class TestPostHistory(unittest.TestCase):
    """Unit tests for PostHistory class."""

    def setUp(self):
        """Set up test environment."""
        self.post_history = PostHistory()
        
        # Test data
        self.test_post = {
            "id": "post123",
            "title": "Test Post",
            "content": "Test content",
            "timestamp": datetime.now().isoformat(),
            "platform": "wordpress",
            "engagement": {
                "likes": 10,
                "comments": 5,
                "shares": 2
            }
        }
        
        # Ensure data directory exists
        os.makedirs(os.getenv("DATA_DIR", "./data"), exist_ok=True)

    def tearDown(self):
        """Clean up after tests."""
        # Clean up test files
        test_files = [
            "post_history.json",
            "engagement_metrics.json",
            "post_analytics.json"
        ]
        for file in test_files:
            file_path = os.path.join(os.getenv("DATA_DIR", "./data"), file)
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_01_add_post_should_store_correctly(self):
        """Test that adding a post stores it correctly."""
        # Add post
        self.post_history.add_post(self.test_post)
        
        # Verify post was added
        posts = self.post_history.get_posts()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["id"], self.test_post["id"])
        self.assertEqual(posts[0]["title"], self.test_post["title"])

    def test_02_get_post_by_id_should_return_correct_post(self):
        """Test that getting a post by ID returns the correct post."""
        # Add post
        self.post_history.add_post(self.test_post)
        
        # Get post
        post = self.post_history.get_post_by_id(self.test_post["id"])
        self.assertIsNotNone(post)
        self.assertEqual(post["id"], self.test_post["id"])
        
        # Test nonexistent post
        nonexistent = self.post_history.get_post_by_id("nonexistent")
        self.assertIsNone(nonexistent)

    def test_03_update_post_should_modify_correctly(self):
        """Test that updating a post modifies it correctly."""
        # Add post
        self.post_history.add_post(self.test_post)
        
        # Update post
        updated_data = {
            "title": "Updated Title",
            "engagement": {
                "likes": 15,
                "comments": 7,
                "shares": 3
            }
        }
        self.post_history.update_post(self.test_post["id"], updated_data)
        
        # Verify update
        updated_post = self.post_history.get_post_by_id(self.test_post["id"])
        self.assertEqual(updated_post["title"], updated_data["title"])
        self.assertEqual(updated_post["engagement"], updated_data["engagement"])

    def test_04_get_posts_by_platform_should_filter_correctly(self):
        """Test that getting posts by platform filters correctly."""
        # Add posts for different platforms
        wp_post = dict(self.test_post, platform="wordpress")
        yt_post = dict(self.test_post, id="post456", platform="youtube")
        self.post_history.add_post(wp_post)
        self.post_history.add_post(yt_post)
        
        # Get posts by platform
        wp_posts = self.post_history.get_posts_by_platform("wordpress")
        yt_posts = self.post_history.get_posts_by_platform("youtube")
        
        # Verify filtering
        self.assertEqual(len(wp_posts), 1)
        self.assertEqual(len(yt_posts), 1)
        self.assertEqual(wp_posts[0]["platform"], "wordpress")
        self.assertEqual(yt_posts[0]["platform"], "youtube")

    def test_05_get_recent_posts_should_return_correct_timeframe(self):
        """Test that getting recent posts returns correct timeframe."""
        # Add posts with different timestamps
        now = datetime.now()
        recent_post = dict(self.test_post, timestamp=now.isoformat())
        old_post = dict(
            self.test_post,
            id="old_post",
            timestamp=(now - timedelta(days=10)).isoformat()
        )
        self.post_history.add_post(recent_post)
        self.post_history.add_post(old_post)
        
        # Get recent posts (last 7 days)
        recent_posts = self.post_history.get_recent_posts(days=7)
        
        # Verify timeframe
        self.assertEqual(len(recent_posts), 1)
        self.assertEqual(recent_posts[0]["id"], recent_post["id"])

    def test_06_get_engagement_metrics_should_calculate_correctly(self):
        """Test that engagement metrics are calculated correctly."""
        # Add posts with engagement data
        posts = [
            dict(self.test_post, id=f"post{i}", engagement={
                "likes": 10 * i,
                "comments": 5 * i,
                "shares": 2 * i
            })
            for i in range(1, 4)
        ]
        for post in posts:
            self.post_history.add_post(post)
        
        # Get metrics
        metrics = self.post_history.get_engagement_metrics()
        
        # Verify calculations
        self.assertIn("total_posts", metrics)
        self.assertIn("total_engagement", metrics)
        self.assertIn("average_engagement", metrics)
        self.assertEqual(metrics["total_posts"], 3)
        self.assertEqual(
            metrics["total_engagement"]["likes"],
            sum(p["engagement"]["likes"] for p in posts)
        )

    def test_07_persistence_should_save_and_load_correctly(self):
        """Test that post history persists correctly."""
        # Add test posts
        self.post_history.add_post(self.test_post)
        
        # Save state
        self.post_history.save_state()
        
        # Create new instance and load state
        new_history = PostHistory()
        new_history.load_state()
        
        # Verify persistence
        posts = new_history.get_posts()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["id"], self.test_post["id"])

    def test_08_error_handling_should_handle_invalid_inputs(self):
        """Test that error handling works correctly."""
        # Test invalid post data
        with self.assertRaises(ValueError):
            self.post_history.add_post({})
        
        # Test updating nonexistent post
        with self.assertRaises(KeyError):
            self.post_history.update_post("nonexistent", {"title": "New"})
        
        # Test invalid platform
        posts = self.post_history.get_posts_by_platform("invalid")
        self.assertEqual(len(posts), 0)

    def test_09_delete_post_should_remove_correctly(self):
        """Test that deleting a post removes it correctly."""
        # Add post
        self.post_history.add_post(self.test_post)
        
        # Delete post
        self.post_history.delete_post(self.test_post["id"])
        
        # Verify deletion
        posts = self.post_history.get_posts()
        self.assertEqual(len(posts), 0)
        
        # Test deleting nonexistent post
        with self.assertRaises(KeyError):
            self.post_history.delete_post("nonexistent")

if __name__ == '__main__':
    unittest.main()
