import unittest
import os
import shutil
import tempfile
from core.TemplateManager import TemplateManager
from core.PathManager import PathManager
from unittest.mock import patch, MagicMock

class TestTemplateManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a temporary directory for testing
        cls.temp_dir = tempfile.mkdtemp()
        cls.original_base_dir = PathManager.base_dir
        PathManager.base_dir = cls.temp_dir

        # Create template directories
        cls.template_dirs = {
            'discord_templates': os.path.join(cls.temp_dir, 'templates', 'discord_templates'),
            'message_templates': os.path.join(cls.temp_dir, 'templates', 'message_templates'),
            'templates': os.path.join(cls.temp_dir, 'templates')
        }
        
        for path in cls.template_dirs.values():
            os.makedirs(path, exist_ok=True)

        # Create some test templates
        cls._create_test_templates()

    @classmethod
    def tearDownClass(cls):
        # Restore original base directory
        PathManager.base_dir = cls.original_base_dir
        # Clean up the temporary directory
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    @classmethod
    def _create_test_templates(cls):
        # Discord template
        discord_template = """
        Hello {{ username }}!
        Welcome to the {{ server_name }} server.
        {% if is_admin %}
        You have admin privileges.
        {% endif %}
        """
        with open(os.path.join(cls.template_dirs['discord_templates'], 'welcome.j2'), 'w') as f:
            f.write(discord_template)

        # Message template
        message_template = """
        Dear {{ name }},
        Your account status is: {{ status }}
        """
        with open(os.path.join(cls.template_dirs['message_templates'], 'status.j2'), 'w') as f:
            f.write(message_template)

        # General template
        general_template = """
        Report for {{ date }}:
        Total users: {{ user_count }}
        """
        with open(os.path.join(cls.template_dirs['templates'], 'report.j2'), 'w') as f:
            f.write(general_template)

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.template_manager = TemplateManager()

    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test template manager initialization"""
        self.assertIsNotNone(self.template_manager)

    @patch('core.TemplateManager.write_json_log')
    def test_render_discord_template(self, mock_write_log):
        """Test rendering a Discord template"""
        data = {
            "quest_name": "Test Quest",
            "reward": "100 XP",
            "completion_time": "2024-03-20"
        }
        rendered = self.template_manager.render_discord_template("quest_complete.j2", data)
        self.assertIn("Test Quest", rendered)
        self.assertIn("100 XP", rendered)

    @patch('core.TemplateManager.write_json_log')
    def test_render_message_template(self, mock_write_log):
        """Test rendering a message template"""
        data = {
            "quest_name": "Test Quest",
            "reward": "100 XP",
            "completion_time": "2024-03-20"
        }
        rendered = self.template_manager.render_message_template("quest_complete.j2", data)
        self.assertIn("Test Quest", rendered)
        self.assertIn("100 XP", rendered)

    def test_render_general_template(self):
        """Test rendering a general template"""
        data = {
            "quest_name": "Test Quest",
            "reward": "100 XP"
        }
        rendered = self.template_manager.render_general_template("quest_complete.j2", data)
        self.assertIn("not found in category 'general'", rendered)

    def test_invalid_category(self):
        """Test handling of invalid template category"""
        data = {"test": "data"}
        rendered = self.template_manager.render_discord_template("invalid.j2", data)
        self.assertIn("not found in category 'discord'", rendered)

    @patch('core.TemplateManager.write_json_log')
    def test_invalid_template_data(self, mock_write_log):
        """Test handling of invalid template data"""
        data = {}  # Missing required variables
        rendered = self.template_manager.render_discord_template("quest_complete.j2", data)
        # The template handles missing data gracefully by using empty strings
        self.assertIn("Quest Completed", rendered)
        self.assertIn("Reward:", rendered)

    def test_list_templates(self):
        """Test listing available templates in a category"""
        discord_templates = self.template_manager.list_templates("discord")
        self.assertIn("quest_complete.j2", discord_templates)
        self.assertIn("episode_release.j2", discord_templates)

    def test_template_not_found(self):
        """Test handling of non-existent template"""
        data = {"test": "data"}
        rendered = self.template_manager.render_discord_template("nonexistent.j2", data)
        self.assertIn("not found in category 'discord'", rendered)

if __name__ == '__main__':
    unittest.main() 