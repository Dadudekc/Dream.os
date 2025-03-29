import pytest
import time
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from social.CommunityIntegrationManager import CommunityIntegrationManager
from social.strategies.youtube_strategy import YouTubeStrategy
from social.strategies.wordpress_strategy import WordPressCommunityStrategy
from social.strategies.ai_strategy import AIStrategy

@pytest.mark.performance
class TestPerformance:
    """Performance tests for the community builder system."""

    @pytest.fixture(autouse=True)
    def setup(self, test_video_data, test_comment_data, mock_openai):
        """Set up test environment."""
        # Initialize strategies with mocks
        self.youtube_strategy = YouTubeStrategy()
        self.wordpress_strategy = WordPressCommunityStrategy()
        self.ai_strategy = AIStrategy()
        
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

    def measure_execution_time(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time

    async def measure_async_execution_time(self, func, *args, **kwargs):
        """Measure execution time of an async function."""
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time

    @pytest.mark.asyncio
    async def test_01_content_sync_performance(self):
        """Test content syncing performance."""
        # Prepare test data
        videos = [
            dict(self.test_video, video_id=f"test{i}")
            for i in range(10)
        ]
        
        # Measure bulk sync performance
        total_time = 0
        for video in videos:
            _, execution_time = await self.measure_async_execution_time(
                self.manager.sync_content,
                video
            )
            total_time += execution_time
        
        # Assert performance metrics
        average_time = total_time / len(videos)
        assert average_time < 1.0  # Should take less than 1 second per video
        
        # Test parallel sync performance
        start_time = time.time()
        tasks = [self.manager.sync_content(video) for video in videos]
        await asyncio.gather(*tasks)
        parallel_time = time.time() - start_time
        
        # Verify parallel execution is faster
        assert parallel_time < total_time

    @pytest.mark.asyncio
    async def test_02_comment_processing_performance(self):
        """Test comment processing performance."""
        # Prepare test comments
        comments = [
            dict(self.test_comment, id=f"comment{i}")
            for i in range(100)
        ]
        
        # Test batch processing performance
        start_time = time.time()
        processed = 0
        batch_size = 10
        
        for i in range(0, len(comments), batch_size):
            batch = comments[i:i + batch_size]
            await self.manager.process_comments_batch(batch)
            processed += len(batch)
        
        batch_time = time.time() - start_time
        
        # Assert batch processing metrics
        assert batch_time / len(comments) < 0.1  # Less than 100ms per comment
        assert processed == len(comments)

    @pytest.mark.asyncio
    async def test_03_analytics_performance(self):
        """Test analytics performance."""
        # Prepare test data
        video_ids = [f"video{i}" for i in range(50)]
        platforms = ["youtube", "wordpress"]
        
        # Measure analytics collection performance
        start_time = time.time()
        analytics = []
        
        for video_id in video_ids:
            for platform in platforms:
                result = await self.manager.get_platform_analytics(
                    video_id,
                    platform
                )
                analytics.append(result)
        
        sequential_time = time.time() - start_time
        
        # Test parallel analytics collection
        start_time = time.time()
        tasks = [
            self.manager.get_platform_analytics(vid, platform)
            for vid in video_ids
            for platform in platforms
        ]
        await asyncio.gather(*tasks)
        parallel_time = time.time() - start_time
        
        # Verify performance
        assert parallel_time < sequential_time
        assert sequential_time / len(video_ids) < 0.5  # Less than 500ms per video

    def test_04_memory_usage_performance(self):
        """Test memory usage performance."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        large_dataset = [
            dict(self.test_video, video_id=f"test{i}")
            for i in range(1000)
        ]
        
        self.manager.load_bulk_data(large_dataset)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Assert memory usage
        assert memory_increase < 100  # Should use less than 100MB additional memory

    @pytest.mark.asyncio
    async def test_05_concurrent_operations_performance(self):
        """Test performance under concurrent operations."""
        # Prepare concurrent operations
        operations = [
            self.manager.sync_content(self.test_video),
            self.manager.process_comments([self.test_comment]),
            self.manager.get_analytics(self.test_video["video_id"]),
            self.manager.generate_engagement_report(self.test_video["video_id"])
        ]
        
        # Measure concurrent execution time
        start_time = time.time()
        results = await asyncio.gather(*operations)
        concurrent_time = time.time() - start_time
        
        # Measure sequential execution time
        start_time = time.time()
        for operation in operations:
            await operation
        sequential_time = time.time() - start_time
        
        # Verify concurrent execution is faster
        assert concurrent_time < sequential_time
        assert all(results)  # All operations should succeed

    @pytest.mark.asyncio
    async def test_06_data_persistence_performance(self):
        """Test data persistence performance."""
        # Prepare test data
        test_data = [
            dict(self.test_video, video_id=f"test{i}")
            for i in range(100)
        ]
        
        # Measure save performance
        _, save_time = self.measure_execution_time(
            self.manager.save_bulk_state,
            test_data
        )
        
        # Measure load performance
        _, load_time = self.measure_execution_time(
            self.manager.load_bulk_state
        )
        
        # Assert persistence performance
        assert save_time < 1.0  # Save should take less than 1 second
        assert load_time < 1.0  # Load should take less than 1 second

    @pytest.mark.asyncio
    async def test_07_ai_response_performance(self):
        """Test AI response generation performance."""
        # Prepare test comments
        comments = [
            dict(self.test_comment, id=f"comment{i}", content=f"Test content {i}")
            for i in range(10)
        ]
        
        # Test batch response generation
        start_time = time.time()
        responses = await asyncio.gather(*[
            self.ai_strategy.generate_comment_response(
                comment["content"],
                {"platform": "youtube"}
            )
            for comment in comments
        ])
        batch_time = time.time() - start_time
        
        # Assert AI performance
        assert len(responses) == len(comments)
        assert batch_time / len(comments) < 2.0  # Less than 2 seconds per response

    @pytest.mark.asyncio
    async def test_08_scheduler_performance(self):
        """Test scheduler performance."""
        # Prepare scheduled tasks
        tasks = []
        base_time = datetime.now()
        
        for i in range(100):
            schedule_time = base_time + timedelta(minutes=i)
            task = {
                "content": dict(self.test_video, video_id=f"test{i}"),
                "schedule_time": schedule_time.isoformat(),
                "platforms": ["youtube", "wordpress"]
            }
            tasks.append(task)
        
        # Measure scheduling performance
        start_time = time.time()
        for task in tasks:
            self.manager.schedule_content(
                task["content"],
                task["schedule_time"],
                task["platforms"]
            )
        scheduling_time = time.time() - start_time
        
        # Assert scheduling performance
        assert scheduling_time / len(tasks) < 0.01  # Less than 10ms per task
        
        # Test task retrieval performance
        _, retrieval_time = self.measure_execution_time(
            self.manager.get_scheduled_content
        )
        assert retrieval_time < 0.1  # Less than 100ms to retrieve all tasks

    def test_09_cache_performance(self):
        """Test cache performance."""
        # Prepare test data
        cache_keys = [f"test_key_{i}" for i in range(1000)]
        cache_data = {key: f"test_value_{i}" for i, key in enumerate(cache_keys)}
        
        # Test cache write performance
        start_time = time.time()
        for key, value in cache_data.items():
            self.manager.cache.set(key, value)
        write_time = time.time() - start_time
        
        # Test cache read performance
        start_time = time.time()
        for key in cache_keys:
            self.manager.cache.get(key)
        read_time = time.time() - start_time
        
        # Assert cache performance
        assert write_time / len(cache_keys) < 0.001  # Less than 1ms per write
        assert read_time / len(cache_keys) < 0.001  # Less than 1ms per read
