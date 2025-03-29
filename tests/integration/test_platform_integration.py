import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from social.CommunityIntegrationManager import CommunityIntegrationManager
from social.strategies.youtube_strategy import YouTubeStrategy
from social.strategies.wordpress_strategy import WordPressCommunityStrategy
from social.strategies.ai_strategy import AIStrategy
from social.ai.chat_agent import AIChatAgent

@pytest.mark.integration
class TestPlatformIntegration:
    """Integration tests for platform interactions."""

    @pytest.fixture(autouse=True)
    def setup(self, test_video_data, test_comment_data, mock_openai):
        """Set up test environment."""
        # Initialize strategies with mocks
        self.youtube_strategy = YouTubeStrategy()
        self.wordpress_strategy = WordPressCommunityStrategy()
        self.ai_strategy = AIStrategy()
        self.chat_agent = AIChatAgent()
        
        # Mock external APIs
        self.youtube_strategy.client = MagicMock()
        self.wordpress_strategy.client = MagicMock()
        self.ai_strategy.ai_agent = mock_openai
        
        # Initialize manager
        self.manager = CommunityIntegrationManager(
            youtube_strategy=self.youtube_strategy,
            wordpress_strategy=self.wordpress_strategy,
            ai_strategy=self.ai_strategy
        )
        
        # Test data
        self.test_video = test_video_data
        self.test_comment = test_comment_data
        
        yield
        
        # Cleanup
        test_files = [
            "integration_test_data.json",
            "test_metrics.json",
            "test_analytics.json"
        ]
        for file in test_files:
            file_path = os.path.join(os.getenv("DATA_DIR", "./data"), file)
            if os.path.exists(file_path):
                os.remove(file_path)

    @pytest.mark.asyncio
    async def test_01_content_flow_should_sync_across_platforms(self):
        """Test end-to-end content flow across platforms."""
        # 1. Optimize content with AI
        optimized = await self.ai_strategy.optimize_content(self.test_video)
        assert optimized["title"] != self.test_video["title"]
        
        # 2. Upload to YouTube
        self.youtube_strategy.client.videos().insert().execute.return_value = {
            "id": self.test_video["video_id"]
        }
        upload_result = await self.youtube_strategy.upload_video(optimized)
        assert upload_result
        
        # 3. Sync to WordPress
        self.wordpress_strategy.client.call.return_value = {"id": 123}
        sync_result = await self.wordpress_strategy.sync_youtube_video(optimized)
        assert sync_result

    @pytest.mark.asyncio
    async def test_02_comment_flow_should_process_across_platforms(self):
        """Test end-to-end comment flow across platforms."""
        # 1. Generate AI response
        response = await self.chat_agent.generate_response(
            self.test_comment["content"],
            {"platform": "youtube", "user_type": "new_user"}
        )
        assert response
        
        # 2. Process on YouTube
        self.youtube_strategy.client.comments().insert().execute.return_value = {
            "id": "response123"
        }
        yt_result = await self.youtube_strategy.reply_to_comment(
            self.test_comment["id"],
            response
        )
        assert yt_result
        
        # 3. Process on WordPress
        self.wordpress_strategy.client.call.return_value = {"id": "wp_response123"}
        wp_result = await self.wordpress_strategy.reply_to_comment(
            self.test_comment["id"],
            response
        )
        assert wp_result

    @pytest.mark.asyncio
    async def test_03_analytics_flow_should_aggregate_across_platforms(self):
        """Test end-to-end analytics flow across platforms."""
        # 1. Collect YouTube metrics
        self.youtube_strategy.client.videos().list().execute.return_value = {
            "items": [{
                "statistics": {
                    "viewCount": "1000",
                    "likeCount": "100",
                    "commentCount": "50"
                }
            }]
        }
        
        # 2. Collect WordPress metrics
        self.wordpress_strategy.client.call.return_value = {
            "views": 500,
            "likes": 50,
            "comments": 25
        }
        
        # 3. Get combined analytics
        analytics = await self.manager.get_analytics(self.test_video["video_id"])
        assert analytics["total_views"] == 1500
        assert analytics["total_engagement"] == 225

    @pytest.mark.asyncio
    async def test_04_scheduling_flow_should_coordinate_across_platforms(self):
        """Test end-to-end scheduling flow across platforms."""
        # 1. Schedule content
        schedule_time = datetime.now() + timedelta(hours=1)
        schedule_result = await self.manager.schedule_content(
            self.test_video,
            schedule_time,
            platforms=["youtube", "wordpress"]
        )
        assert schedule_result
        
        # 2. Verify scheduled tasks
        tasks = self.manager.get_scheduled_content()
        assert len(tasks) == 1
        assert tasks[0]["platforms"] == ["youtube", "wordpress"]
        
        # 3. Mock execution time and run scheduled tasks
        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value = schedule_time
            execution_result = await self.manager.execute_scheduled_tasks()
            assert execution_result["success"]

    @pytest.mark.asyncio
    async def test_05_engagement_flow_should_track_across_platforms(self):
        """Test end-to-end engagement flow across platforms."""
        # 1. Track YouTube engagement
        yt_engagement = {
            "type": "comment",
            "user": "test_user",
            "content": self.test_comment["content"],
            "sentiment": 0.8
        }
        await self.manager.track_engagement(
            self.test_video["video_id"],
            "youtube",
            yt_engagement
        )
        
        # 2. Track WordPress engagement
        wp_engagement = {
            "type": "like",
            "user": "test_user",
            "post_id": 123,
            "timestamp": datetime.now().isoformat()
        }
        await self.manager.track_engagement(
            self.test_video["video_id"],
            "wordpress",
            wp_engagement
        )
        
        # 3. Generate engagement report
        report = await self.manager.generate_engagement_report(
            self.test_video["video_id"]
        )
        assert report["total_engagements"] == 2
        assert report["platforms"]["youtube"]["total"] == 1
        assert report["platforms"]["wordpress"]["total"] == 1

    @pytest.mark.asyncio
    async def test_06_ai_integration_flow_should_enhance_interactions(self):
        """Test end-to-end AI integration flow."""
        # 1. Generate optimized response
        context = {
            "platform": "youtube",
            "user_type": "new_user",
            "video_title": self.test_video["title"],
            "previous_interactions": []
        }
        response = await self.chat_agent.generate_response(
            self.test_comment["content"],
            context
        )
        assert response
        
        # 2. Analyze sentiment
        sentiment = await self.ai_strategy.analyze_sentiment(
            self.test_comment["content"]
        )
        assert "score" in sentiment
        assert "label" in sentiment
        
        # 3. Generate engagement prompt
        prompt = await self.ai_strategy.generate_engagement_prompt(
            {"engagement_rate": 0.2},
            [self.test_video]
        )
        assert prompt

    @pytest.mark.asyncio
    async def test_07_error_recovery_flow_should_handle_failures(self):
        """Test end-to-end error recovery flow."""
        # 1. Simulate YouTube API failure
        self.youtube_strategy.client.videos().insert().execute.side_effect = Exception(
            "YouTube API Error"
        )
        
        # 2. Attempt content sync
        result = await self.manager.sync_content(self.test_video)
        assert not result["youtube"]
        assert "error" in result["youtube_error"]
        
        # 3. Verify WordPress still works
        assert result["wordpress"]
        
        # 4. Verify error is logged and tracked
        errors = self.manager.get_error_log()
        assert len(errors) == 1
        assert errors[0]["platform"] == "youtube"

    @pytest.mark.asyncio
    async def test_08_data_persistence_flow_should_maintain_state(self):
        """Test end-to-end data persistence flow."""
        # 1. Add test data
        await self.manager.track_engagement(
            self.test_video["video_id"],
            "youtube",
            {"type": "comment"}
        )
        
        # 2. Save state
        self.manager.save_state()
        
        # 3. Create new manager and load state
        new_manager = CommunityIntegrationManager(
            youtube_strategy=self.youtube_strategy,
            wordpress_strategy=self.wordpress_strategy,
            ai_strategy=self.ai_strategy
        )
        new_manager.load_state()
        
        # 4. Verify state persistence
        history = new_manager.get_engagement_history(self.test_video["video_id"])
        assert len(history) == 1
        assert history[0]["platform"] == "youtube"

    @pytest.mark.asyncio
    async def test_09_cross_platform_optimization_flow(self):
        """Test end-to-end cross-platform optimization flow."""
        # 1. Get platform-specific metrics
        metrics = {
            "youtube": {
                "views": 1000,
                "engagement_rate": 0.3
            },
            "wordpress": {
                "views": 500,
                "engagement_rate": 0.2
            }
        }
        
        # 2. Generate optimization suggestions
        suggestions = await self.ai_strategy.generate_optimization_suggestions(
            self.test_video,
            metrics
        )
        assert suggestions
        assert "title" in suggestions
        assert "description" in suggestions
        
        # 3. Apply optimizations
        result = await self.manager.apply_cross_platform_optimizations(
            self.test_video["video_id"],
            suggestions
        )
        assert result["youtube"]
        assert result["wordpress"] 