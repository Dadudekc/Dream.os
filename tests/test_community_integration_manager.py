import unittest
import os
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from social.CommunityIntegrationManager import CommunityIntegrationManager
from social.strategies.youtube_strategy import YouTubeStrategy
from social.strategies.wordpress_strategy import WordPressCommunityStrategy

class TestCommunityIntegrationManager(unittest.TestCase):
    """Unit tests for CommunityIntegrationManager class."""

    def setUp(self):
        """Set up test environment."""
        # Mock strategies
        self.youtube_strategy = MagicMock(spec=YouTubeStrategy)
        self.wordpress_strategy = MagicMock(spec=WordPressCommunityStrategy)
        
        # Initialize manager with mock strategies
        self.manager = CommunityIntegrationManager(
            youtube_strategy=self.youtube_strategy,
            wordpress_strategy=self.wordpress_strategy
        )
        
        # Test data
        self.test_video = {
            "title": "Test Video",
            "description": "Test description",
            "video_id": "test123",
            "tags": ["test", "video"],
            "thumbnail_url": "https://example.com/thumb.jpg"
        }
        
        self.test_comment = {
            "id": "comment123",
            "content": "Great video!",
            "video_id": self.test_video["video_id"],
            "author": "test_user",
            "platform": "youtube"
        }
        
        # Ensure data directory exists
        os.makedirs(os.getenv("DATA_DIR", "./data"), exist_ok=True)

    def tearDown(self):
        """Clean up after tests."""
        test_files = [
            "integration_metrics.json",
            "cross_platform_analytics.json",
            "engagement_history.json"
        ]
        for file in test_files:
            file_path = os.path.join(os.getenv("DATA_DIR", "./data"), file)
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_01_sync_content_should_distribute_across_platforms(self):
        """Test that content syncing works across platforms."""
        # Mock successful YouTube upload
        self.youtube_strategy.upload_video.return_value = True
        
        # Mock successful WordPress sync
        self.wordpress_strategy.sync_youtube_video.return_value = True
        
        # Sync content
        result = self.manager.sync_content(self.test_video)
        
        # Verify sync
        self.assertTrue(result)
        self.youtube_strategy.upload_video.assert_called_once()
        self.wordpress_strategy.sync_youtube_video.assert_called_once()

    def test_02_process_interactions_should_handle_all_platforms(self):
        """Test that interactions are processed across platforms."""
        # Mock interactions
        youtube_comment = dict(self.test_comment, platform="youtube")
        wordpress_comment = dict(self.test_comment, platform="wordpress")
        
        # Mock getting unprocessed comments
        self.youtube_strategy.get_unprocessed_comments.return_value = [youtube_comment]
        self.wordpress_strategy.get_unprocessed_comments.return_value = [wordpress_comment]
        
        # Process interactions
        processed = self.manager.process_interactions()
        
        # Verify processing
        self.assertTrue(processed)
        self.youtube_strategy.process_comments.assert_called_once()
        self.wordpress_strategy.process_comments.assert_called_once()

    def test_03_get_analytics_should_combine_platform_metrics(self):
        """Test that analytics combine metrics from all platforms."""
        # Mock platform metrics
        youtube_metrics = {
            "views": 1000,
            "likes": 100,
            "comments": 50
        }
        wordpress_metrics = {
            "views": 500,
            "likes": 50,
            "comments": 25
        }
        
        self.youtube_strategy.get_video_metrics.return_value = youtube_metrics
        self.wordpress_strategy.get_post_metrics.return_value = wordpress_metrics
        
        # Get combined analytics
        analytics = self.manager.get_analytics(self.test_video["video_id"])
        
        # Verify combined metrics
        self.assertIsInstance(analytics, dict)
        self.assertEqual(
            analytics["total_views"],
            youtube_metrics["views"] + wordpress_metrics["views"]
        )
        self.assertEqual(
            analytics["total_engagement"],
            sum(youtube_metrics.values()) + sum(wordpress_metrics.values())
        )

    def test_04_engagement_tracking_should_track_across_platforms(self):
        """Test that engagement is tracked across platforms."""
        # Track engagement
        self.manager.track_engagement(
            self.test_video["video_id"],
            "youtube",
            {"type": "comment", "user": "test_user"}
        )
        self.manager.track_engagement(
            self.test_video["video_id"],
            "wordpress",
            {"type": "like", "user": "test_user"}
        )
        
        # Get engagement history
        history = self.manager.get_engagement_history(self.test_video["video_id"])
        
        # Verify tracking
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["platform"], "youtube")
        self.assertEqual(history[1]["platform"], "wordpress")

    def test_05_member_management_should_track_across_platforms(self):
        """Test that member management works across platforms."""
        # Mock member data
        member_data = {
            "id": "user123",
            "platforms": ["youtube", "wordpress"],
            "engagement_level": "active"
        }
        
        # Add member
        self.manager.add_member(member_data)
        
        # Get member info
        member = self.manager.get_member_info(member_data["id"])
        
        # Verify member data
        self.assertIsNotNone(member)
        self.assertEqual(member["platforms"], member_data["platforms"])
        self.assertEqual(member["engagement_level"], member_data["engagement_level"])

    def test_06_content_optimization_should_apply_to_all_platforms(self):
        """Test that content optimization applies to all platforms."""
        # Mock optimization results
        optimized_content = {
            "title": "Optimized Title",
            "description": "Optimized description",
            "tags": ["optimized", "test"]
        }
        
        # Mock AI optimization
        self.manager.ai_strategy.optimize_content.return_value = optimized_content
        
        # Optimize content
        result = self.manager.optimize_content(self.test_video)
        
        # Verify optimization
        self.assertEqual(result["title"], optimized_content["title"])
        self.youtube_strategy.update_video.assert_called_once()
        self.wordpress_strategy.update_post.assert_called_once()

    def test_07_error_handling_should_manage_platform_failures(self):
        """Test that platform failures are handled correctly."""
        # Mock YouTube failure
        self.youtube_strategy.upload_video.side_effect = Exception("YouTube API Error")
        
        # Mock WordPress success
        self.wordpress_strategy.sync_youtube_video.return_value = True
        
        # Attempt sync
        result = self.manager.sync_content(self.test_video)
        
        # Verify partial success handling
        self.assertTrue(result["wordpress"])
        self.assertFalse(result["youtube"])
        self.assertIn("error", result["youtube_error"])

    def test_08_persistence_should_maintain_cross_platform_state(self):
        """Test that cross-platform state is maintained."""
        # Add test data
        self.manager.track_engagement(
            self.test_video["video_id"],
            "youtube",
            {"type": "comment"}
        )
        
        # Save state
        self.manager.save_state()
        
        # Create new manager and load state
        new_manager = CommunityIntegrationManager(
            youtube_strategy=self.youtube_strategy,
            wordpress_strategy=self.wordpress_strategy
        )
        new_manager.load_state()
        
        # Verify persistence
        history = new_manager.get_engagement_history(self.test_video["video_id"])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["platform"], "youtube")

    def test_09_scheduling_should_coordinate_across_platforms(self):
        """Test that scheduling coordinates across platforms."""
        # Schedule content
        schedule_time = datetime.now().isoformat()
        self.manager.schedule_content(
            self.test_video,
            schedule_time,
            platforms=["youtube", "wordpress"]
        )
        
        # Verify scheduling
        self.youtube_strategy.schedule_upload.assert_called_once()
        self.wordpress_strategy.schedule_post.assert_called_once()
        
        # Get scheduled content
        scheduled = self.manager.get_scheduled_content()
        self.assertEqual(len(scheduled), 1)
        self.assertEqual(scheduled[0]["content"]["video_id"], self.test_video["video_id"])

if __name__ == '__main__':
    unittest.main() 
