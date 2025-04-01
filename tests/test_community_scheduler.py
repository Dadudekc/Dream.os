import os
import asyncio
from datetime import datetime, timedelta
import unittest
from social.strategies.wordpress_strategy import WordPressCommunityStrategy
from social.strategies.community_scheduler import CommunityScheduler
from unittest.mock import MagicMock, patch

class TestCommunityScheduler(unittest.TestCase):
    """Unit tests for CommunityScheduler class."""

    def setUp(self):
        """Set up test environment."""
        self.scheduler = CommunityScheduler()
        self.wp_strategy = MagicMock(spec=WordPressCommunityStrategy)
        
        # Test video data
        self.test_video = {
            "title": "Test Video",
            "description": "This is a test video description",
            "video_id": "test123",
            "tags": ["test", "automation"],
            "thumbnail_url": "https://example.com/thumb.jpg"
        }

    def tearDown(self):
        """Clean up after tests."""
        self.scheduler.stop()
        
        # Clean up test files
        test_files = [
            "scheduled_tasks.json",
            "processed_comments.json",
            f"report_{datetime.now().strftime('%Y%m%d')}.json"
        ]
        
        for file in test_files:
            file_path = os.path.join(os.getenv("DATA_DIR", "./data"), file)
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_schedule_task(self):
        """Test scheduling a task."""
        # Test data
        content = {
            "title": "Test Video",
            "video_id": "test123",
            "description": "Test description"
        }
        post_time = datetime.now() + timedelta(hours=1)

        # Schedule task
        task_id = self.scheduler.schedule_task(self.wp_strategy, content, post_time)
        
        # Verify task was scheduled
        self.assertIn(task_id, self.scheduler.scheduled_tasks)
        self.assertEqual(len(self.scheduler.scheduled_tasks), 1)

    def test_cancel_task(self):
        """Test canceling a scheduled task."""
        # Schedule a task
        content = {"title": "Test"}
        post_time = datetime.now() + timedelta(minutes=30)
        task_id = self.scheduler.schedule_task(self.wp_strategy, content, post_time)

        # Cancel task
        self.scheduler.cancel_task(task_id)
        
        # Verify task was canceled
        self.assertNotIn(task_id, self.scheduler.scheduled_tasks)

    def test_schedule_engagement_check(self):
        """Test scheduling engagement checks."""
        # Schedule engagement check
        interval = 15
        job_id = self.scheduler.schedule_engagement_check(self.wp_strategy, interval)
        
        # Verify job was scheduled
        self.assertIn(job_id, self.scheduler.scheduled_jobs)

    def test_schedule_daily_report(self):
        """Test scheduling daily reports."""
        # Schedule daily report
        time = "00:00"
        job_id = self.scheduler.schedule_daily_report(self.wp_strategy, time)
        
        # Verify job was scheduled
        self.assertIn(job_id, self.scheduler.scheduled_jobs)

    @patch('social.strategies.community_scheduler.asyncio')
    async def test_generate_daily_report(self, mock_asyncio):
        """Test daily report generation."""
        # Mock strategy methods
        self.wp_strategy.get_community_metrics.return_value = {
            "total_members": 100,
            "active_members": 50,
            "engagement_rate": 0.3
        }

        # Generate report
        await self.scheduler._generate_daily_report(self.wp_strategy)
        
        # Verify strategy methods were called
        self.wp_strategy.get_community_metrics.assert_called_once()

    def test_error_handling(self):
        """Test error handling in scheduler."""
        # Test invalid interval
        with self.assertRaises(ValueError):
            self.scheduler.schedule_engagement_check(self.wp_strategy, -1)

        # Test invalid time format
        with self.assertRaises(ValueError):
            self.scheduler.schedule_daily_report(self.wp_strategy, "25:00")

        # Test invalid task data
        with self.assertRaises(Exception):
            self.scheduler.schedule_task(None, None, None)

    def test_persistence(self):
        """Test task persistence."""
        # Schedule tasks
        content = {"title": "Test"}
        post_time = datetime.now() + timedelta(hours=1)
        task_id = self.scheduler.schedule_task(self.wp_strategy, content, post_time)

        # Save state
        self.scheduler.save_state()

        # Create new scheduler and load state
        new_scheduler = CommunityScheduler()
        new_scheduler.load_state()

        # Verify tasks were restored
        self.assertIn(task_id, new_scheduler.scheduled_tasks)

    async def test_ai_responses(self):
        """Test AI response generation."""
        # Schedule AI responses every 15 minutes
        self.scheduler.schedule_ai_responses(self.wp_strategy, 15)
        
        # Verify task was scheduled
        self.assertTrue("ai_responses" in self.scheduler.scheduled_tasks)
        
        # Test processing a comment
        test_comment = {
            "id": "test_comment_1",
            "content": "Great video! How did you create those effects?",
            "post_id": 123
        }
        
        # Mock the comment processing
        await self.scheduler._process_comments(self.wp_strategy)
        
        # Verify comment was processed
        self.assertTrue(
            self.scheduler._is_comment_processed(test_comment["id"])
        )

    def test_scheduler_lifecycle(self):
        """Test scheduler start and stop."""
        # Start scheduler
        self.scheduler.start()
        self.assertTrue(self.scheduler.scheduler.running)
        
        # Stop scheduler
        self.scheduler.stop()
        self.assertFalse(self.scheduler.scheduler.running)

if __name__ == '__main__':
    unittest.main() 
