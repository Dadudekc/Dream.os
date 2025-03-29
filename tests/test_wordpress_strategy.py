import unittest
import os
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from social.strategies.wordpress_strategy import WordPressCommunityStrategy

class TestWordPressCommunityStrategy(unittest.TestCase):
    """Unit tests for WordPressCommunityStrategy class."""

    def setUp(self):
        """Set up test environment."""
        self.wp_strategy = WordPressCommunityStrategy()
        
        # Mock WordPress client
        self.wp_strategy.client = MagicMock()
        
        # Test data
        self.test_video = {
            "title": "Test Video",
            "description": "Test description",
            "video_id": "test123",
            "tags": ["test", "video"],
            "thumbnail_url": "https://example.com/thumb.jpg"
        }
        
        self.test_comment = {
            "id": "comment1",
            "content": "Great video!",
            "post_id": 123,
            "author": "test_user"
        }

    def tearDown(self):
        """Clean up after tests."""
        # Clean up test files
        test_files = [
            "member_interactions.json",
            "processed_comments.json",
            "community_metrics.json"
        ]
        for file in test_files:
            file_path = os.path.join(os.getenv("DATA_DIR", "./data"), file)
            if os.path.exists(file_path):
                os.remove(file_path)

    async def test_sync_youtube_video(self):
        """Test syncing YouTube video to WordPress."""
        # Mock WordPress post creation
        self.wp_strategy.client.call.return_value = {"id": 456}
        
        # Sync video
        result = await self.wp_strategy.sync_youtube_video(self.test_video)
        
        # Verify sync
        self.assertTrue(result)
        self.wp_strategy.client.call.assert_called_once()
        
        # Verify post data
        call_args = self.wp_strategy.client.call.call_args[0]
        self.assertEqual(call_args[0], "wp.newPost")
        self.assertIn(self.test_video["title"], str(call_args[1]))

    def test_track_member_interaction(self):
        """Test member interaction tracking."""
        # Track interaction
        self.wp_strategy.track_member_interaction(
            self.test_comment["author"],
            "comment",
            {"sentiment": 0.8}
        )
        
        # Verify tracking
        interactions = self.wp_strategy.get_member_interactions(
            self.test_comment["author"]
        )
        self.assertIsNotNone(interactions)
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0]["type"], "comment")

    def test_get_community_metrics(self):
        """Test community metrics collection."""
        # Mock WordPress API responses
        self.wp_strategy.client.call.side_effect = [
            [{"id": 1}, {"id": 2}],  # posts
            [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}],  # comments
            [{"id": "u1"}, {"id": "u2"}]  # users
        ]
        
        # Get metrics
        metrics = self.wp_strategy.get_community_metrics()
        
        # Verify metrics
        self.assertIsInstance(metrics, dict)
        self.assertIn("total_posts", metrics)
        self.assertIn("total_comments", metrics)
        self.assertIn("active_members", metrics)
        self.assertIn("engagement_rate", metrics)

    async def test_process_comments(self):
        """Test comment processing."""
        # Mock unprocessed comments
        self.wp_strategy.get_unprocessed_comments = MagicMock(
            return_value=[self.test_comment]
        )
        
        # Mock AI response
        ai_response = "Thank you for your comment!"
        self.wp_strategy.ai_strategy = MagicMock()
        self.wp_strategy.ai_strategy.generate_comment_response.return_value = ai_response
        
        # Process comments
        await self.wp_strategy.process_comments()
        
        # Verify processing
        self.wp_strategy.ai_strategy.generate_comment_response.assert_called_once()
        self.wp_strategy.client.call.assert_called()  # Should call to post response

    def test_member_history(self):
        """Test member interaction history."""
        # Add test interactions
        member = "test_user"
        interactions = [
            {"type": "comment", "timestamp": datetime.now().isoformat()},
            {"type": "like", "timestamp": datetime.now().isoformat()}
        ]
        
        for interaction in interactions:
            self.wp_strategy.track_member_interaction(
                member,
                interaction["type"],
                {"timestamp": interaction["timestamp"]}
            )
        
        # Get history
        history = self.wp_strategy.get_member_interactions(member)
        
        # Verify history
        self.assertEqual(len(history), len(interactions))
        self.assertEqual(history[0]["type"], interactions[0]["type"])

    def test_error_handling(self):
        """Test error handling in WordPress strategy."""
        # Test invalid video sync
        self.wp_strategy.client.call.side_effect = Exception("API Error")
        result = self.wp_strategy.sync_youtube_video({})
        self.assertFalse(result)
        
        # Test invalid member lookup
        history = self.wp_strategy.get_member_interactions("nonexistent")
        self.assertEqual(len(history), 0)
        
        # Test metrics error handling
        self.wp_strategy.client.call.side_effect = Exception("API Error")
        metrics = self.wp_strategy.get_community_metrics()
        self.assertIn("error", metrics)

    def test_data_persistence(self):
        """Test data persistence functionality."""
        # Add test data
        self.wp_strategy.track_member_interaction(
            "test_user",
            "comment",
            {"timestamp": datetime.now().isoformat()}
        )
        
        # Save state
        self.wp_strategy.save_state()
        
        # Create new strategy and load state
        new_strategy = WordPressCommunityStrategy()
        new_strategy.load_state()
        
        # Verify data persistence
        history = new_strategy.get_member_interactions("test_user")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["type"], "comment")

if __name__ == '__main__':
    unittest.main() 