import unittest
import os
import shutil
import json
import yaml
from unittest.mock import patch, MagicMock
from core.FileManager import FileManager


class TestFileManager(unittest.TestCase):

    def setUp(self):
        # Create a temp test directory structure
        self.test_root = os.path.join(os.getcwd(), "test_environment")
        os.makedirs(self.test_root, exist_ok=True)

        # Patch PathManager to point to test directories
        patcher_path_manager = patch('core.FileManager.PathManager')
        self.mock_path_manager = patcher_path_manager.start()
        self.addCleanup(patcher_path_manager.stop)

        self.mock_path_manager.cycles_dir = os.path.join(self.test_root, "cycles")
        self.mock_path_manager.memory_dir = os.path.join(self.test_root, "memory")
        self.mock_path_manager.logs_dir = os.path.join(self.test_root, "logs")
        self.mock_path_manager.outputs_dir = os.path.join(self.test_root, "outputs")

        # Ensure directories exist
        os.makedirs(self.mock_path_manager.cycles_dir, exist_ok=True)
        os.makedirs(self.mock_path_manager.memory_dir, exist_ok=True)
        os.makedirs(self.mock_path_manager.logs_dir, exist_ok=True)
        os.makedirs(self.mock_path_manager.outputs_dir, exist_ok=True)

        # Initialize FileManager
        self.manager = FileManager()

    def tearDown(self):
        # Clean up the test environment
        shutil.rmtree(self.test_root)

    # ------------------------
    # SAVE RESPONSE
    # ------------------------
    def test_save_response_creates_file(self):
        content = "Test response content."
        prompt_type = "dreamscape"
        chat_title = "Victor's Chat"

        filepath = self.manager.save_response(content, prompt_type, chat_title)
        self.assertTrue(os.path.exists(filepath))

        with open(filepath, "r", encoding="utf-8") as f:
            file_content = f.read()
        self.assertEqual(file_content, content)

    def test_save_response_creates_correct_path(self):
        content = "Another response."
        prompt_type = "ideas"
        chat_title = "Test Chat Title"

        filepath = self.manager.save_response(content, prompt_type, chat_title)
        self.assertTrue(prompt_type in filepath)
        self.assertTrue("test_chat_title" in filepath)

    # ------------------------
    # SAVE MEMORY STATE
    # ------------------------
    def test_save_memory_state_creates_json_file(self):
        data = {"version": 1, "data": {"memory": "test"}}
        filepath = self.manager.save_memory_state(data, "test_memory")

        self.assertTrue(os.path.exists(filepath))

        with open(filepath, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        self.assertEqual(file_data, data)

    # ------------------------
    # SAVE LOG
    # ------------------------
    def test_save_log_creates_log_file(self):
        log_text = "This is a log entry."
        log_type = "execution"

        filepath = self.manager.save_log(log_text, log_type)
        self.assertTrue(os.path.exists(filepath))

        with open(filepath, "r", encoding="utf-8") as f:
            file_content = f.read()
        self.assertEqual(file_content, log_text)

    # ------------------------
    # ARCHIVE FILE
    # ------------------------
    def test_archive_file_moves_file(self):
        # Create a dummy file to archive
        test_file = os.path.join(self.test_root, "dummy.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Archive me.")

        archived_path = self.manager.archive_file(test_file, "test_archive")
        self.assertTrue(os.path.exists(archived_path))
        self.assertFalse(os.path.exists(test_file))

    # ------------------------
    # SAVE FILE INTERNALLY
    # ------------------------
    def test_save_file_json_and_yaml(self):
        json_data = {"json_key": "json_value"}
        yaml_data = {"yaml_key": "yaml_value"}

        json_file = os.path.join(self.test_root, "data.json")
        yaml_file = os.path.join(self.test_root, "data.yaml")

        self.manager._save_file(json_data, json_file, file_type="json")
        self.manager._save_file(yaml_data, yaml_file, file_type="yaml")

        with open(json_file, "r", encoding="utf-8") as f:
            loaded_json = json.load(f)
        self.assertEqual(loaded_json, json_data)

        with open(yaml_file, "r", encoding="utf-8") as f:
            loaded_yaml = yaml.safe_load(f)
        self.assertEqual(loaded_yaml, yaml_data)

    def test_save_file_handles_exceptions(self):
        # Try to save file in non-writable location
        with patch('builtins.open', side_effect=Exception("Permission denied")):
            result = self.manager._save_file("fail", "non_writable/file.txt")
            self.assertIsNone(result)

    # ------------------------
    # LOAD FILE
    # ------------------------
    def test_load_file_json_and_yaml(self):
        json_data = {"load_test": "json"}
        yaml_data = {"load_test": "yaml"}

        json_file = os.path.join(self.test_root, "load.json")
        yaml_file = os.path.join(self.test_root, "load.yaml")
        text_file = os.path.join(self.test_root, "load.txt")

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f)

        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f)

        with open(text_file, "w", encoding="utf-8") as f:
            f.write("Plain text content.")

        loaded_json = self.manager.load_file(json_file, file_type="json")
        loaded_yaml = self.manager.load_file(yaml_file, file_type="yaml")
        loaded_text = self.manager.load_file(text_file, file_type="text")

        self.assertEqual(loaded_json, json_data)
        self.assertEqual(loaded_yaml, yaml_data)
        self.assertEqual(loaded_text, "Plain text content.")

    def test_load_file_handles_exceptions(self):
        result = self.manager.load_file("nonexistent_file.txt")
        self.assertIsNone(result)

    # ------------------------
    # SANITIZE FILENAME
    # ------------------------
    def test_sanitize_filename_strips_and_replaces(self):
        dirty_name = "Invalid/File:Name*With|Chars"
        clean_name = self.manager.sanitize_filename(dirty_name)
        self.assertEqual(clean_name, "invalid_file_name_with_chars")

        dirty_name_spaces = "   Weird  Name  "
        clean_spaces = self.manager.sanitize_filename(dirty_name_spaces)
        self.assertEqual(clean_spaces, "weird__name")
