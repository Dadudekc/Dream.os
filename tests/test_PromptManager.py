# tests/test_PromptManager.py

import unittest
import os
import sys
from unittest.mock import patch, MagicMock
# Ensure the core directory is in the path if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from core.AletheiaPromptManager import AletheiaPromptManager


class TestPromptManager(unittest.TestCase):
    """
    Unit tests for the AletheiaPromptManager class.
    """

    def setUp(self):
        """Set up test environment"""
        self.manager = AletheiaPromptManager()

    def test_get_prompt_devlog(self):
        """Test getting the devlog prompt"""
        with patch('jinja2.environment.Template.render') as mock_render:
            mock_render.return_value = "Test devlog prompt"
            prompt = self.manager.get_prompt("devlog")
            self.assertEqual(prompt, "Test devlog prompt")

    @patch('jinja2.environment.Environment.get_template')
    def test_get_prompt_content_ideas(self, mock_get_template):
        """Test getting the content ideas prompt"""
        mock_template = MagicMock()
        mock_template.render.return_value = "Test content ideas prompt"
        mock_get_template.return_value = mock_template
        prompt = self.manager.get_prompt("content_ideas")
        mock_get_template.assert_called_once_with("content_ideas.j2")
        self.assertEqual(prompt, "Test content ideas prompt")

    @patch('jinja2.environment.Environment.get_template')
    def test_get_prompt_dreamscape(self, mock_get_template):
        """Test getting the dreamscape prompt"""
        mock_template = MagicMock()
        mock_template.render.return_value = "Test dreamscape prompt"
        mock_get_template.return_value = mock_template
        prompt = self.manager.get_prompt("dreamscape")
        mock_get_template.assert_called_once_with("dreamscape.j2")
        self.assertEqual(prompt, "Test dreamscape prompt")

    def test_get_prompt_invalid_type(self):
        """Test getting an invalid prompt type"""
        with self.assertRaises(ValueError):
            self.manager.get_prompt("invalid_type")

    def test_list_available_prompts(self):
        """Test listing available prompts"""
        prompts = self.manager.list_available_prompts()
        self.assertIsInstance(prompts, list)
        self.assertIn("devlog", prompts)
        self.assertIn("dreamscape", prompts)
        self.assertIn("content_ideas", prompts)

    def test_add_prompt(self):
        """Test adding a new prompt"""
        self.manager.add_prompt("test_prompt", "Some text", "gpt-4o-mini")
        self.assertIn("test_prompt", self.manager.list_available_prompts())

    def test_remove_prompt(self):
        """Test removing a prompt"""
        self.manager.add_prompt("remove_me", "Some text", "gpt-4o-mini")
        self.manager.remove_prompt("remove_me")
        self.assertNotIn("remove_me", self.manager.list_available_prompts())

    def test_remove_nonexistent_prompt(self):
        """Test removing a nonexistent prompt"""
        initial_prompts = set(self.manager.list_available_prompts())
        try:
            self.manager.remove_prompt("nonexistent")
        except ValueError:
            pass  # Expected behavior
        final_prompts = set(self.manager.list_available_prompts())
        self.assertEqual(initial_prompts, final_prompts)

if __name__ == "__main__":
    unittest.main()
