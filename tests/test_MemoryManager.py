import unittest
import os
import json
import shutil
from datetime import datetime
from config.MemoryManager import MemoryManager

class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        # Create a test memory file path
        self.test_memory_dir = "test_memory"
        self.test_memory_file = os.path.join(self.test_memory_dir, "test_memory.json")
        os.makedirs(self.test_memory_dir, exist_ok=True)
        self.memory_manager = MemoryManager(self.test_memory_file)

    def tearDown(self):
        # Clean up test files after each test
        if os.path.exists(self.test_memory_dir):
            shutil.rmtree(self.test_memory_dir)

    def test_initialization(self):
        """Test that MemoryManager initializes correctly"""
        self.assertTrue(os.path.exists(self.test_memory_dir))
        self.assertEqual(self.memory_manager.data, {"platforms": {}, "conversations": {}})

    def test_record_interaction(self):
        """Test recording a new interaction"""
        platform = "discord"
        username = "test_user"
        response = "Hello, world!"
        sentiment = "positive"
        success = True
        interaction_id = "test123"

        self.memory_manager.record_interaction(
            platform=platform,
            username=username,
            response=response,
            sentiment=sentiment,
            success=success,
            interaction_id=interaction_id
        )

        # Check platform-user level recording
        self.assertIn(platform, self.memory_manager.data["platforms"])
        self.assertIn(username, self.memory_manager.data["platforms"][platform])
        user_data = self.memory_manager.data["platforms"][platform][username]
        self.assertEqual(len(user_data), 1)
        self.assertEqual(user_data[0]["response"], response)
        self.assertEqual(user_data[0]["sentiment"], sentiment)
        self.assertEqual(user_data[0]["success"], success)

        # Check conversation-level indexing
        self.assertIn(interaction_id, self.memory_manager.data["conversations"])
        conv_data = self.memory_manager.data["conversations"][interaction_id]
        self.assertEqual(len(conv_data), 1)
        self.assertEqual(conv_data[0]["response"], response)

    def test_initialize_conversation(self):
        """Test initializing a new conversation"""
        interaction_id = "conv123"
        metadata = {"user": "test_user", "channel": "general"}
        
        self.memory_manager.initialize_conversation(interaction_id, metadata)
        
        self.assertIn(interaction_id, self.memory_manager.data["conversations"])
        self.assertIn(f"{interaction_id}_metadata", self.memory_manager.data["conversations"])
        self.assertEqual(
            self.memory_manager.data["conversations"][f"{interaction_id}_metadata"]["metadata"],
            metadata
        )

    def test_retrieve_conversation(self):
        """Test retrieving conversation history"""
        interaction_id = "conv123"
        response = "Test response"
        
        # Record an interaction
        self.memory_manager.record_interaction(
            platform="discord",
            username="test_user",
            response=response,
            sentiment="neutral",
            success=True,
            interaction_id=interaction_id
        )
        
        conversation = self.memory_manager.retrieve_conversation(interaction_id)
        self.assertEqual(len(conversation), 1)
        self.assertEqual(conversation[0]["response"], response)

    def test_get_user_history(self):
        """Test retrieving user history"""
        platform = "discord"
        username = "test_user"
        
        # Record multiple interactions
        for i in range(3):
            self.memory_manager.record_interaction(
                platform=platform,
                username=username,
                response=f"Response {i}",
                sentiment="neutral",
                success=True
            )
        
        history = self.memory_manager.get_user_history(platform, username, limit=2)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["response"], "Response 2")

    def test_user_sentiment_summary(self):
        """Test generating user sentiment summary"""
        platform = "discord"
        username = "test_user"
        
        # Record interactions with different sentiments
        sentiments = ["positive", "neutral", "negative", "positive"]
        for i, sentiment in enumerate(sentiments):
            self.memory_manager.record_interaction(
                platform=platform,
                username=username,
                response=f"Response {i}",
                sentiment=sentiment,
                success=True
            )
        
        summary = self.memory_manager.user_sentiment_summary(platform, username)
        self.assertEqual(summary["total_interactions"], 4)
        self.assertEqual(summary["sentiment_distribution"]["positive"], 2)
        self.assertEqual(summary["sentiment_distribution"]["neutral"], 1)
        self.assertEqual(summary["sentiment_distribution"]["negative"], 1)
        self.assertEqual(summary["success_rate_percent"], 100.0)

    def test_clear_user_history(self):
        """Test clearing user history"""
        platform = "discord"
        username = "test_user"
        
        self.memory_manager.record_interaction(
            platform=platform,
            username=username,
            response="Test response",
            sentiment="neutral",
            success=True
        )
        
        self.memory_manager.clear_user_history(platform, username)
        history = self.memory_manager.get_user_history(platform, username)
        self.assertEqual(len(history), 0)

    def test_clear_platform_history(self):
        """Test clearing platform history"""
        platform = "discord"
        username = "test_user"
        
        self.memory_manager.record_interaction(
            platform=platform,
            username=username,
            response="Test response",
            sentiment="neutral",
            success=True
        )
        
        self.memory_manager.clear_platform_history(platform)
        self.assertNotIn(platform, self.memory_manager.data["platforms"])

if __name__ == '__main__':
    unittest.main() 
