import os
import asyncio
import unittest
from datetime import datetime, timedelta
from typing import Dict, Any

from social.strategies.wordpress_strategy import WordPressCommunityStrategy
from social.strategies.community_scheduler import CommunityScheduler
from social.strategies.ai_strategy import AIStrategy

class TestCommunityIntegration(unittest.TestCase):
    """Integration tests for the community builder system."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Initialize strategies
        cls.wp_strategy = WordPressCommunityStrategy()
        cls.scheduler = CommunityScheduler()
        cls.ai_strategy = AIStrategy()
        
        # Test data
        cls.test_video = {
            "title": "Integration Test Video",
            "description": "This is a test video for integration testing",
            "video_id": "test_integration_123",
            "tags": ["test", "integration"],
            "thumbnail_url": "https://example.com/thumb.jpg"
        }
        
        cls.test_comment = {
            "id": "test_comment_1",
            "content": "This is a great video! How do you make these?",
            "post_id": 123,
            "author": "test_user"
        }

    async def test_end_to_end_content_flow(self):
        """Test end-to-end content flow from video to WordPress post."""
        try:
            # 1. Optimize content using AI
            optimized_content = await self.ai_strategy.optimize_content(self.test_video)
            self.assertIsNotNone(optimized_content.get("title"))
            self.assertIsNotNone(optimized_content.get("description"))
            
            # 2. Schedule content posting
            post_time = datetime.now() + timedelta(minutes=5)
            self.scheduler.schedule_task(self.wp_strategy, optimized_content, post_time)
            
            # 3. Verify scheduled task
            task_id = f"post_{optimized_content['video_id']}"
            self.assertIn(task_id, self.scheduler.scheduled_tasks)
            
            # 4. Mock post creation and verify
            post_result = await self.wp_strategy.sync_youtube_video(optimized_content)
            self.assertTrue(post_result)
            
        except Exception as e:
            self.fail(f"End-to-end content flow failed: {e}")

    async def test_ai_response_integration(self):
        """Test AI response integration with WordPress comments."""
        try:
            # 1. Generate AI response to comment
            context = {
                "type": "question",
                "user_type": "new_user",
                "content_type": "video",
                "platform": "wordpress"
            }
            
            response = await self.ai_strategy.generate_comment_response(
                self.test_comment["content"],
                context
            )
            
            self.assertIsNotNone(response)
            self.assertTrue(len(response) > 0)
            
            # 2. Analyze sentiment
            sentiment = self.ai_strategy.analyze_sentiment(
                self.test_comment["content"],
                {"is_first_time": True}
            )
            
            self.assertIn("score", sentiment)
            self.assertIn("label", sentiment)
            
            # 3. Track interaction
            self.wp_strategy.track_member_interaction(
                self.test_comment["author"],
                "comment",
                {
                    "sentiment": sentiment,
                    "ai_response": response
                }
            )
            
        except Exception as e:
            self.fail(f"AI response integration failed: {e}")

    async def test_engagement_monitoring(self):
        """Test engagement monitoring and automated responses."""
        try:
            # 1. Schedule engagement check
            self.scheduler.schedule_engagement_check(self.wp_strategy, interval_minutes=5)
            
            # 2. Get community metrics
            metrics = self.wp_strategy.get_community_metrics()
            self.assertIsInstance(metrics, dict)
            
            # 3. Generate engagement prompt if needed
            if metrics.get("engagement_rate", 0) < 0.3:
                recent_content = [self.test_video]  # Mock recent content
                prompt = await self.ai_strategy.generate_engagement_prompt(
                    metrics,
                    recent_content
                )
                self.assertIsNotNone(prompt)
                
        except Exception as e:
            self.fail(f"Engagement monitoring failed: {e}")

    async def test_daily_reporting(self):
        """Test daily report generation and analytics."""
        try:
            # 1. Schedule daily report
            self.scheduler.schedule_daily_report(self.wp_strategy, "00:00")
            
            # 2. Generate test report
            await self.scheduler._generate_daily_report(self.wp_strategy)
            
            # 3. Get AI response analytics
            analytics = self.ai_strategy.get_response_analytics()
            self.assertIsInstance(analytics, dict)
            self.assertIn("total_responses", analytics)
            
            # 4. Verify report file creation
            report_file = os.path.join(
                os.getenv("DATA_DIR", "./data"),
                f"report_{datetime.now().strftime('%Y%m%d')}.json"
            )
            self.assertTrue(os.path.exists(report_file))
            
        except Exception as e:
            self.fail(f"Daily reporting failed: {e}")

    def test_error_handling(self):
        """Test error handling and fallback responses."""
        try:
            # 1. Test invalid video data
            invalid_video = {"title": "Invalid"}
            self.assertFalse(self.wp_strategy.sync_youtube_video(invalid_video))
            
            # 2. Test AI fallback responses
            fallback = self.ai_strategy._get_fallback_response("comment")
            self.assertIsNotNone(fallback)
            
            # 3. Test scheduler error handling
            with self.assertRaises(Exception):
                self.scheduler.schedule_task(None, None, None)
                
        except Exception as e:
            self.fail(f"Error handling test failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        # Stop scheduler
        cls.scheduler.stop()
        
        # Clean up test files
        test_files = [
            "scheduled_tasks.json",
            "processed_comments.json",
            "ai_response_history.json",
            f"report_{datetime.now().strftime('%Y%m%d')}.json"
        ]
        
        for file in test_files:
            file_path = os.path.join(os.getenv("DATA_DIR", "./data"), file)
            if os.path.exists(file_path):
                os.remove(file_path)

if __name__ == '__main__':
    unittest.main() 
