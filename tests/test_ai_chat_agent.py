import unittest
import os
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from social.ai.chat_agent import AIChatAgent

class TestAIChatAgent(unittest.TestCase):
    """Unit tests for AIChatAgent class."""

    def setUp(self):
        """Set up test environment."""
        self.chat_agent = AIChatAgent()
        
        # Test data
        self.test_prompt = "How do you create those amazing effects in your videos?"
        self.test_context = {
            "video_title": "Special Effects Tutorial",
            "channel_name": "TestChannel",
            "previous_interactions": [],
            "user_type": "new_user"
        }
        self.test_history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]
        
        # Ensure data directory exists
        os.makedirs(os.getenv("DATA_DIR", "./data"), exist_ok=True)

    def tearDown(self):
        """Clean up after tests."""
        # Clean up test files
        test_files = [
            "chat_history.json",
            "response_cache.json",
            "conversation_analytics.json",
            "prompt_templates.json"
        ]
        for file in test_files:
            file_path = os.path.join(os.getenv("DATA_DIR", "./data"), file)
            if os.path.exists(file_path):
                os.remove(file_path)

    @patch('social.ai.chat_agent.openai')
    async def test_01_generate_response_should_return_valid_response(self, mock_openai):
        """Test that generate_response returns a valid response."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Here's how we create those effects..."
        mock_openai.ChatCompletion.create.return_value = mock_response
        
        # Generate response
        response = await self.chat_agent.generate_response(
            self.test_prompt,
            self.test_context
        )
        
        # Verify response
        self.assertIsNotNone(response)
        self.assertTrue(len(response) > 0)
        mock_openai.ChatCompletion.create.assert_called_once()

    def test_02_conversation_history_should_maintain_correct_order(self):
        """Test that conversation history maintains correct message order."""
        # Add messages to history
        self.chat_agent.add_to_history(
            "user",
            self.test_prompt,
            self.test_context
        )
        self.chat_agent.add_to_history(
            "assistant",
            "Test response",
            self.test_context
        )
        
        # Verify history
        history = self.chat_agent.get_conversation_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[0]["content"], self.test_prompt)

    def test_03_context_management_should_update_and_retrieve_correctly(self):
        """Test that context is properly updated and retrieved."""
        # Set context
        self.chat_agent.update_context(self.test_context)
        
        # Verify context
        current_context = self.chat_agent.get_current_context()
        self.assertEqual(current_context["video_title"], self.test_context["video_title"])
        self.assertEqual(current_context["user_type"], self.test_context["user_type"])
        self.assertEqual(current_context["channel_name"], self.test_context["channel_name"])

    def test_04_response_cache_should_store_and_retrieve_correctly(self):
        """Test that response caching works correctly."""
        # Add response to cache
        test_response = "Cached response"
        self.chat_agent.cache_response(
            self.test_prompt,
            test_response,
            self.test_context
        )
        
        # Verify cache
        cached_response = self.chat_agent.get_cached_response(
            self.test_prompt,
            self.test_context
        )
        self.assertIsNotNone(cached_response)
        self.assertEqual(cached_response, test_response)
        
        # Test cache miss
        missing_response = self.chat_agent.get_cached_response(
            "different prompt",
            self.test_context
        )
        self.assertIsNone(missing_response)

    def test_05_conversation_analytics_should_track_correctly(self):
        """Test that conversation analytics are tracked correctly."""
        # Add test interactions
        expected_interactions = 3
        for _ in range(expected_interactions):
            self.chat_agent.add_to_history(
                "user",
                self.test_prompt,
                self.test_context
            )
            self.chat_agent.add_to_history(
                "assistant",
                "Test response",
                self.test_context
            )
        
        # Get analytics
        analytics = self.chat_agent.get_conversation_analytics()
        
        # Verify analytics
        self.assertIsInstance(analytics, dict)
        self.assertIn("total_interactions", analytics)
        self.assertEqual(analytics["total_interactions"], expected_interactions)
        self.assertIn("user_messages", analytics)
        self.assertIn("assistant_messages", analytics)
        self.assertEqual(analytics["user_messages"], expected_interactions)
        self.assertEqual(analytics["assistant_messages"], expected_interactions)

    def test_06_prompt_templates_should_manage_correctly(self):
        """Test that prompt templates are managed correctly."""
        # Test default templates
        default_template = self.chat_agent.get_prompt_template("general")
        self.assertIsNotNone(default_template)
        
        # Test custom template
        template_name = "custom"
        custom_template = "Custom response for {user_type} about {video_title}"
        self.chat_agent.add_prompt_template(template_name, custom_template)
        
        # Verify template
        saved_template = self.chat_agent.get_prompt_template(template_name)
        self.assertEqual(saved_template, custom_template)
        
        # Test template formatting
        formatted = self.chat_agent.format_prompt_template(
            template_name,
            self.test_context
        )
        expected = custom_template.format(**self.test_context)
        self.assertEqual(formatted, expected)

    def test_07_error_handling_should_handle_invalid_inputs(self):
        """Test that error handling works correctly for invalid inputs."""
        # Test invalid context
        with self.assertRaises(ValueError):
            self.chat_agent.update_context(None)
        
        # Test invalid prompt template
        template = self.chat_agent.get_prompt_template("nonexistent")
        self.assertEqual(template, self.chat_agent.default_prompt_template)
        
        # Test invalid history access
        with self.assertRaises(ValueError):
            self.chat_agent.add_to_history("invalid_role", "test", {})
        
        # Test invalid template formatting
        with self.assertRaises(KeyError):
            self.chat_agent.format_prompt_template("custom", {})

    def test_08_persistence_should_save_and_load_state(self):
        """Test that state persistence works correctly."""
        # Add test data
        self.chat_agent.add_to_history(
            "user",
            self.test_prompt,
            self.test_context
        )
        
        # Add custom template
        custom_template = "Custom template"
        self.chat_agent.add_prompt_template("custom", custom_template)
        
        # Save state
        self.chat_agent.save_state()
        
        # Create new agent and load state
        new_agent = AIChatAgent()
        new_agent.load_state()
        
        # Verify persistence
        history = new_agent.get_conversation_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["content"], self.test_prompt)
        
        # Verify template persistence
        loaded_template = new_agent.get_prompt_template("custom")
        self.assertEqual(loaded_template, custom_template)

    @patch('social.ai.chat_agent.openai')
    async def test_09_streaming_response_should_yield_chunks(self, mock_openai):
        """Test that streaming response yields correct chunks."""
        # Mock streaming response
        mock_response = MagicMock()
        chunks = ["Part 1", "Part 2"]
        mock_response.__aiter__.return_value = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content=chunk))])
            for chunk in chunks
        ]
        mock_openai.ChatCompletion.create.return_value = mock_response
        
        # Test streaming
        response_stream = self.chat_agent.generate_streaming_response(
            self.test_prompt,
            self.test_context
        )
        
        # Collect streaming response
        full_response = ""
        async for chunk in response_stream:
            full_response += chunk
        
        # Verify streaming response
        self.assertTrue(len(full_response) > 0)
        for chunk in chunks:
            self.assertIn(chunk, full_response)
        mock_openai.ChatCompletion.create.assert_called_once()

if __name__ == '__main__':
    unittest.main() 
