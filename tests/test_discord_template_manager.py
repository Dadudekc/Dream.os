import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json

from core.DiscordTemplateManager import DiscordTemplateManager


class TestDiscordTemplateManager(unittest.TestCase):
    def setUp(self):
        # Patch the logger to prevent actual logging during tests
        patcher_logger = patch('core.DiscordTemplateManager.logger')
        self.mock_logger = patcher_logger.start()
        self.addCleanup(patcher_logger.stop)

        # Patch os.makedirs to prevent directory creation
        self.patcher_makedirs = patch('core.DiscordTemplateManager.os.makedirs')
        self.mock_makedirs = self.patcher_makedirs.start()
        self.addCleanup(self.patcher_makedirs.stop)

        # Patch Jinja2 Environment and FileSystemLoader
        patcher_env = patch('core.DiscordTemplateManager.Environment')
        self.mock_env = patcher_env.start()
        self.addCleanup(patcher_env.stop)

        # Patch os.listdir for list_templates
        self.patcher_listdir = patch('core.DiscordTemplateManager.os.listdir')
        self.mock_listdir = self.patcher_listdir.start()
        self.addCleanup(self.patcher_listdir.stop)

        # Provide a mock config file path
        self.mock_config_file = '/fake/path/config.json'

    # ---------- INIT & RESOLUTION ----------
    @patch('core.DiscordTemplateManager.os.getenv')
    @patch('core.DiscordTemplateManager.os.path.isdir')
    def test_resolve_template_dir_env(self, mock_isdir, mock_getenv):
        mock_getenv.return_value = "/env/templates"
        mock_isdir.return_value = True

        manager = DiscordTemplateManager(config_file=self.mock_config_file)
        resolved_dir = manager._resolve_template_dir(self.mock_config_file)

        self.assertEqual(resolved_dir, "/env/templates")
        self.mock_logger.info.assert_called_with(" Loaded template dir from environment: /env/templates")

    @patch('core.DiscordTemplateManager.os.getenv')
    @patch('core.DiscordTemplateManager.os.path.exists')
    @patch('core.DiscordTemplateManager.os.path.isdir')
    @patch('builtins.open', new_callable=mock_open, read_data=json.dumps({"discord_templates_dir": "/json/templates"}))
    def test_resolve_template_dir_json(self, mock_file, mock_isdir, mock_exists, mock_getenv):
        mock_getenv.return_value = None
        mock_exists.return_value = True
        mock_isdir.side_effect = lambda path: path in ["/json/templates"]

        manager = DiscordTemplateManager(config_file=self.mock_config_file)
        resolved_dir = manager._resolve_template_dir(self.mock_config_file)

        self.assertEqual(resolved_dir, "/json/templates")
        self.mock_logger.info.assert_called_with("️ Loaded template dir from config: /json/templates")

    @patch('core.DiscordTemplateManager.os.getenv')
    @patch('core.DiscordTemplateManager.os.path.exists')
    @patch('core.DiscordTemplateManager.Config.DISCORD_TEMPLATE_DIR', '/fallback/templates')
    def test_resolve_template_dir_fallback(self, mock_exists, mock_getenv):
        mock_getenv.return_value = None
        mock_exists.return_value = False

        manager = DiscordTemplateManager(config_file=self.mock_config_file)
        resolved_dir = manager._resolve_template_dir(self.mock_config_file)

        self.assertEqual(resolved_dir, '/fallback/templates')
        self.mock_logger.warning.assert_called_with("️ Falling back to centralized template dir: /fallback/templates")

    # ---------- INIT ----------
    @patch('core.DiscordTemplateManager.os.path.isdir')
    def test_init_creates_directory_if_not_exist(self, mock_isdir):
        mock_isdir.return_value = False
        manager = DiscordTemplateManager(config_file=self.mock_config_file)

        self.mock_makedirs.assert_called()
        self.mock_logger.info.assert_any_call(f" Created template directory at: {manager.template_dir}")

    @patch('core.DiscordTemplateManager.os.path.isdir')
    def test_init_does_not_create_directory_if_exists(self, mock_isdir):
        mock_isdir.return_value = True
        DiscordTemplateManager(config_file=self.mock_config_file)

        self.mock_makedirs.assert_not_called()

    # ---------- RENDER MESSAGE ----------
    def test_render_message_successful(self):
        # Prepare mocks
        mock_template = MagicMock()
        mock_template.render.return_value = "Rendered message"
        mock_env_instance = MagicMock()
        mock_env_instance.get_template.return_value = mock_template

        self.mock_env.return_value = mock_env_instance

        manager = DiscordTemplateManager(config_file=self.mock_config_file)
        message = manager.render_message("test_template", {"key": "value"})

        self.assertEqual(message, "Rendered message")
        mock_template.render.assert_called_with({"key": "value"})
        self.mock_logger.info.assert_any_call(" Rendered template 'test_template.j2' in", unittest.mock.ANY)

    def test_render_message_template_not_found(self):
        mock_env_instance = MagicMock()
        mock_env_instance.get_template.side_effect = Exception("TemplateNotFound")

        self.mock_env.return_value = mock_env_instance

        manager = DiscordTemplateManager(config_file=self.mock_config_file)
        message = manager.render_message("missing_template", {"key": "value"})

        self.assertIn("⚠️ Template 'missing_template' not found.", message)
        self.mock_logger.error.assert_called()

    def test_render_message_general_exception(self):
        mock_env_instance = MagicMock()
        mock_env_instance.get_template.side_effect = Exception("General Error")

        self.mock_env.return_value = mock_env_instance

        manager = DiscordTemplateManager(config_file=self.mock_config_file)
        message = manager.render_message("broken_template", {"key": "value"})

        self.assertIn("⚠️ Error rendering template 'broken_template'", message)
        self.mock_logger.error.assert_called()

    # ---------- LIST TEMPLATES ----------
    def test_list_templates_success(self):
        self.mock_listdir.return_value = ["template1.j2", "template2.j2", "not_a_template.txt"]

        manager = DiscordTemplateManager(config_file=self.mock_config_file)
        templates = manager.list_templates()

        self.assertEqual(templates, ["template1.j2", "template2.j2"])
        self.mock_logger.info.assert_any_call(f" Available templates: {templates}")

    def test_list_templates_error(self):
        self.mock_listdir.side_effect = Exception("List Error")

        manager = DiscordTemplateManager(config_file=self.mock_config_file)
        templates = manager.list_templates()

        self.assertEqual(templates, [])
        self.mock_logger.error.assert_called()

if __name__ == "__main__":
    unittest.main()
