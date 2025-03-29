import os
import unittest
import shutil
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from core.FileManager import FileManager

class TestFileManager(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_dreamscape"
        self.manager = FileManager(base_folder=self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_save_and_load_json(self):
        title = "test_json_file"
        data = {"name": "Dreamscape", "version": 1.0, "tags": ["automation", "ai"]}
        self.manager.save_entry(data, title, subfolder="json_files", extension=".json")
        loaded_data = self.manager.load_entry(title, subfolder="json_files", extension=".json")
        self.assertEqual(data, loaded_data)

    def test_save_and_load_yaml(self):
        title = "test_yaml_file"
        data = {"mission": "Expand the Dreamscape", "status": "Active"}
        self.manager.save_entry(data, title, subfolder="yaml_files", extension=".yaml")
        loaded_data = self.manager.load_entry(title, subfolder="yaml_files", extension=".yaml")
        self.assertEqual(data, loaded_data)

    def test_fail_on_invalid_load(self):
        content = self.manager.load_entry("non_existent", subfolder="missing", extension=".txt")
        self.assertIsNone(content)

    def test_save_entry_invalid_json(self):
        def dummy_function(): pass
        title = "invalid_json"
        data = {"invalid": dummy_function}
        path = self.manager.save_entry(data, title, subfolder="errors", extension=".json")
        self.assertIsNone(path)

    def test_load_entry_invalid_json_content(self):
        title = "invalid_json_content"
        folder = os.path.join(self.test_dir, "json_files")
        self.manager.ensure_directory(folder)

        file_path = os.path.join(folder, f"{self.manager.sanitize_filename(title)}.json")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write("{invalid json content")

        result = self.manager.load_entry(title, subfolder="json_files", extension=".json")
        self.assertIsNone(result)

    def test_load_entry_invalid_yaml_content(self):
        title = "invalid_yaml_content"
        folder = os.path.join(self.test_dir, "yaml_files")
        self.manager.ensure_directory(folder)

        file_path = os.path.join(folder, f"{self.manager.sanitize_filename(title)}.yaml")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write("::this is not yaml::")

        result = self.manager.load_entry(title, subfolder="yaml_files", extension=".yaml")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
