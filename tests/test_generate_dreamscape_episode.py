import unittest
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.services.dreamscape_generator_service import DreamscapeGenerationService
from core.PathManager import PathManager
from core.TemplateManager import TemplateManager


class TestDreamscapeEpisodeGeneration(unittest.TestCase):
    """Test suite for the dreamscape episode generation functionality."""

    def setUp(self):
        """Set up test fixtures, including mock objects and test data."""
        # Create a temporary directory for outputs
        self.temp_dir = Path("test_outputs/dreamscape")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock PathManager
        self.path_manager_mock = MagicMock(spec=PathManager)
        self.path_manager_mock.get_path.return_value = self.temp_dir
        
        # Mock TemplateManager
        self.template_manager_mock = MagicMock(spec=TemplateManager)
        self.template_manager_mock.render_general_template.return_value = """
# Digital Dreamscape Chronicles: Test Episode

> *Generated on 2025-03-30 12:34 from chat: "Test Chat"*

## 🔮 Dream Fragment Summary
This is a test summary.

## 📖 Episode Narrative
This is a test narrative generated from chat history.

## 🧠 Memory Convergence
**New Knowledge Integrated:**
- Test update 1
- Test update 2

## 📌 Convergence Tags
#dreamscape #test #digitalchronicles
"""
        
        # Create test chat history
        self.test_chat_history = [
            "Hello, how can I help you today?",
            "I need to develop a system for generating dreamscape episodes.",
            "That's an interesting project! Let me help you design that system.",
            "The system should take chat history and generate a narrative episode.",
            "I've created a template for the episodes with a specific structure."
        ]
        
        # Initialize the service with mocks
        self.dreamscape_service = DreamscapeGenerationService(
            path_manager=self.path_manager_mock,
            template_manager=self.template_manager_mock,
            logger=MagicMock()
        )

    def tearDown(self):
        """Clean up any created test files."""
        # Remove test files created during testing
        for file in self.temp_dir.glob("*"):
            try:
                file.unlink()
            except:
                pass
        
        # Try to remove the test directory
        try:
            self.temp_dir.rmdir()
            Path("test_outputs").rmdir()
        except:
            pass

    def test_generate_dreamscape_episode(self):
        """Test that a dreamscape episode can be generated from chat history."""
        # Generate an episode
        result = self.dreamscape_service.generate_dreamscape_episode(
            chat_title="Test Chat",
            chat_history=self.test_chat_history
        )
        
        # Verify that the episode was created
        self.assertIsNotNone(result)
        self.assertTrue(result.exists())
        
        # Check that the template manager was called correctly
        self.template_manager_mock.render_general_template.assert_called_once()
        _, args, _ = self.template_manager_mock.render_general_template.mock_calls[0]
        self.assertEqual(args[0], "dreamscape_episode.j2")
        
        # Verify the context contains expected keys
        context = args[1]
        self.assertEqual(context["chat_title"], "Test Chat")
        self.assertIn("episode_title", context)
        self.assertIn("raw_response", context)
        self.assertIn("tags", context)

    def test_extract_episode_title(self):
        """Test that an episode title can be extracted from content."""
        # Test with markdown title
        content = "# The Test Title\nSome content here."
        title = self.dreamscape_service._extract_episode_title(content, "Fallback")
        self.assertEqual(title, "The Test Title")
        
        # Test with fallback
        content = "No title pattern here."
        title = self.dreamscape_service._extract_episode_title(content, "Fallback")
        self.assertTrue("Fallback" in title)

    def test_slugify(self):
        """Test that text is properly converted to a slug format."""
        # Test basic slugification
        slug = self.dreamscape_service._slugify("Test Chat Title")
        self.assertEqual(slug, "test_chat_title")
        
        # Test with special characters
        slug = self.dreamscape_service._slugify("Test: Chat & Title!")
        self.assertEqual(slug, "test_chat_title")


if __name__ == "__main__":
    unittest.main() 
