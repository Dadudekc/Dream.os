import unittest
import os
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from social.strategies.ai_strategy import AIStrategy

class TestAIStrategy(unittest.TestCase):
    """Unit tests for AIStrategy class."""

    def setUp(self):
        """Set up test environment."""
        self.ai_strategy = AIStrategy()
        self.ai_strategy.ai_agent = MagicMock()
        
        # Test data
        self.test_comment = "This is a great video! How do you make these?"
        self.test_content = {
            "title": "Test Video",
            "description": "Test description for optimization",
            "tags": ["test", "video"],
            "video_id": "test123"
        }
        self.test_metrics = {
            "engagement_rate": 0.2,
            "active_members": 50,
            "total_posts": 100
        }

    def tearDown(self):
        """Clean up after tests."""
        # Clean up test files
        test_files = [
            "ai_response_templates.json",
            "ai_response_history.json"
        ]
        for file in test_files:
            file_path = os.path.join(os.getenv("DATA_DIR", "./data"), file)
            if os.path.exists(file_path):
                os.remove(file_path)

    async def test_generate_comment_response(self):
        """Test comment response generation."""
        # Mock AI response
        self.ai_strategy.ai_agent.ask.return_value = "Thank you for your question! Here's how we make our videos..."
        
        # Test context
        context = {
            "type": "question",
            "user_type": "new_user",
            "content_type": "video",
            "platform": "wordpress"
        }
        
        # Generate response
        response = await self.ai_strategy.generate_comment_response(
            self.test_comment,
            context
        )
        
        # Verify response
        self.assertIsNotNone(response)
        self.assertTrue(len(response) > 0)
        self.ai_strategy.ai_agent.ask.assert_called_once()

    async def test_generate_engagement_prompt(self):
        """Test engagement prompt generation."""
        # Mock AI response
        self.ai_strategy.ai_agent.ask.return_value = "What's your favorite part of this video?"
        
        # Generate prompt
        prompt = await self.ai_strategy.generate_engagement_prompt(
            self.test_metrics,
            [self.test_content]
        )
        
        # Verify prompt
        self.assertIsNotNone(prompt)
        self.assertTrue(len(prompt) > 0)

    async def test_optimize_content(self):
        """Test content optimization."""
        # Mock AI response with optimized content
        optimized = {
            "title": "Improved Test Video",
            "description": "Enhanced test description",
            "tags": ["test", "video", "tutorial"]
        }
        self.ai_strategy.ai_agent.ask.return_value = json.dumps(optimized)
        
        # Optimize content
        result = await self.ai_strategy.optimize_content(self.test_content)
        
        # Verify optimization
        self.assertIsNotNone(result)
        self.assertIn("title", result)
        self.assertIn("description", result)
        self.assertNotEqual(result["title"], self.test_content["title"])

    def test_analyze_sentiment(self):
        """Test sentiment analysis."""
        # Mock sentiment analysis
        self.ai_strategy.ai_agent.analyze_sentiment.return_value = 0.8
        
        # Analyze sentiment
        result = self.ai_strategy.analyze_sentiment(
            self.test_comment,
            {"is_first_time": True}
        )
        
        # Verify analysis
        self.assertIn("score", result)
        self.assertIn("label", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["label"], "very_positive")

    def test_response_templates(self):
        """Test response template handling."""
        # Test default templates
        template = self.ai_strategy._get_response_template("question")
        self.assertIsNotNone(template)
        
        # Test custom template
        custom_templates = {
            "custom": "Custom template: {text}"
        }
        with open(self.ai_strategy.response_templates_file, 'w') as f:
            json.dump(custom_templates, f)
        
        # Reload templates
        self.ai_strategy.response_templates = self.ai_strategy._load_templates()
        template = self.ai_strategy._get_response_template("custom")
        self.assertEqual(template, "Custom template: {text}")

    def test_fallback_responses(self):
        """Test fallback response handling."""
        # Test various fallback types
        comment_fallback = self.ai_strategy._get_fallback_response("comment")
        engagement_fallback = self.ai_strategy._get_fallback_response("engagement")
        general_fallback = self.ai_strategy._get_fallback_response("unknown")
        
        # Verify fallbacks
        self.assertIsNotNone(comment_fallback)
        self.assertIsNotNone(engagement_fallback)
        self.assertIsNotNone(general_fallback)
        self.assertNotEqual(comment_fallback, engagement_fallback)

    def test_response_tracking(self):
        """Test response tracking functionality."""
        # Track a test response
        self.ai_strategy._track_response(
            "comment",
            "test input",
            "test output",
            {"context": "test"}
        )
        
        # Get analytics
        analytics = self.ai_strategy.get_response_analytics()
        
        # Verify tracking
        self.assertIsInstance(analytics, dict)
        self.assertIn("total_responses", analytics)
        self.assertEqual(analytics["total_responses"], 1)
        self.assertIn("response_types", analytics)
        self.assertIn("comment", analytics["response_types"])

    def test_error_handling(self):
        """Test error handling in AI strategy."""
        # Test invalid sentiment analysis
        self.ai_strategy.ai_agent.analyze_sentiment.side_effect = Exception("API Error")
        result = self.ai_strategy.analyze_sentiment("test")
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["label"], "neutral")
        
        # Test invalid template
        template = self.ai_strategy._get_response_template("nonexistent")
        self.assertEqual(template, self.ai_strategy.response_templates["general"])

if __name__ == '__main__':
    unittest.main() 
