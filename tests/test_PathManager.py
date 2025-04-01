import unittest
import os
import shutil
import tempfile
from core.PathManager import PathManager

class TestPathManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory on the same drive as the workspace
        workspace_drive = os.path.splitdrive(os.getcwd())[0]
        self.temp_dir = os.path.abspath(os.path.join(workspace_drive, "temp_test_dir"))
        os.makedirs(self.temp_dir, exist_ok=True)

        # Store original paths
        self.original_paths = PathManager._paths_registry.copy()

        # Set up test paths
        PathManager.base_dir = self.temp_dir
        PathManager.outputs_dir = os.path.abspath(os.path.join(self.temp_dir, "outputs"))
        PathManager.memory_dir = os.path.abspath(os.path.join(self.temp_dir, "memory"))
        PathManager.templates_dir = os.path.abspath(os.path.join(self.temp_dir, "templates"))
        PathManager.drivers_dir = os.path.abspath(os.path.join(self.temp_dir, "drivers"))
        PathManager.configs_dir = os.path.abspath(os.path.join(self.temp_dir, "configs"))
        PathManager.logs_dir = os.path.abspath(os.path.join(PathManager.outputs_dir, "logs"))
        PathManager.cycles_dir = os.path.abspath(os.path.join(PathManager.outputs_dir, "cycles"))
        PathManager.dreamscape_dir = os.path.abspath(os.path.join(PathManager.cycles_dir, "dreamscape"))
        PathManager.workflow_audit_dir = os.path.abspath(os.path.join(PathManager.cycles_dir, "workflow_audits"))
        PathManager.discord_exports_dir = os.path.abspath(os.path.join(PathManager.outputs_dir, "discord_exports"))
        PathManager.reinforcement_logs_dir = os.path.abspath(os.path.join(PathManager.outputs_dir, "reinforcement_logs"))
        PathManager.discord_templates_dir = os.path.abspath(os.path.join(PathManager.templates_dir, "discord_templates"))
        PathManager.message_templates_dir = os.path.abspath(os.path.join(PathManager.templates_dir, "message_templates"))
        PathManager.engagement_templates_dir = os.path.abspath(os.path.join(PathManager.templates_dir, "engagement_templates"))
        PathManager.report_templates_dir = os.path.abspath(os.path.join(PathManager.templates_dir, "report_templates"))
        PathManager.strategies_dir = os.path.abspath(os.path.join(self.temp_dir, "chat_mate", "social", "strategies"))
        PathManager.context_db_path = os.path.abspath(os.path.join(PathManager.strategies_dir, "context_db.json"))
 
        # Update the paths registry
        PathManager._paths_registry.update({
            "base": PathManager.base_dir,
            "outputs": PathManager.outputs_dir,
            "memory": PathManager.memory_dir,
            "templates": PathManager.templates_dir,
            "drivers": PathManager.drivers_dir,
            "configs": PathManager.configs_dir,
            "logs": PathManager.logs_dir,
            "cycles": PathManager.cycles_dir,
            "dreamscape": PathManager.dreamscape_dir,
            "workflow_audits": PathManager.workflow_audit_dir,
            "discord_exports": PathManager.discord_exports_dir,
            "reinforcement_logs": PathManager.reinforcement_logs_dir,
            "discord_templates": PathManager.discord_templates_dir,
            "message_templates": PathManager.message_templates_dir,
            "engagement_templates": PathManager.engagement_templates_dir,
            "report_templates": PathManager.report_templates_dir,
            "strategies": PathManager.strategies_dir,
            "context_db": PathManager.context_db_path
        })

    def tearDown(self):
        """Clean up test environment"""
        # Restore original paths
        for key, path in self.original_paths.items():
            setattr(PathManager, key + "_dir" if not key.endswith("_path") else key, path)

        # Update the paths registry
        PathManager._paths_registry = self.original_paths.copy()

        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_ensure_directories(self):
        """Test directory creation"""
        PathManager.ensure_directories()
        self.assertTrue(os.path.exists(PathManager.outputs_dir))
        self.assertTrue(os.path.exists(PathManager.memory_dir))
        self.assertTrue(os.path.exists(PathManager.templates_dir))
        self.assertTrue(os.path.exists(PathManager.drivers_dir))
        self.assertTrue(os.path.exists(PathManager.configs_dir))

    def test_get_path(self):
        """Test retrieving paths from the registry"""
        # Test getting existing paths
        self.assertEqual(PathManager.get_path("base"), self.temp_dir)
        self.assertEqual(PathManager.get_path("outputs"), os.path.abspath(os.path.join(self.temp_dir, "outputs")))
        self.assertEqual(PathManager.get_path("memory"), os.path.abspath(os.path.join(self.temp_dir, "memory")))

        # Test getting nonexistent path
        with self.assertRaises(ValueError):
            PathManager.get_path("nonexistent")

    def test_register_path(self):
        """Test registering new paths"""
        test_path = os.path.abspath(os.path.join(self.temp_dir, "test"))
        PathManager.register_path("test", test_path)
        self.assertEqual(PathManager.get_path("test"), test_path)

    def test_list_paths(self):
        """Test listing all registered paths"""
        paths = PathManager.list_paths()

        # Verify it's a dictionary
        self.assertIsInstance(paths, dict)

        # Verify it contains the base paths
        self.assertIn("base", paths)
        self.assertIn("outputs", paths)
        self.assertIn("memory", paths)
        self.assertIn("templates", paths)

        # Verify the values are correct
        self.assertEqual(paths["base"], self.temp_dir)
        self.assertEqual(paths["outputs"], os.path.abspath(os.path.join(self.temp_dir, "outputs")))
        self.assertEqual(paths["memory"], os.path.abspath(os.path.join(self.temp_dir, "memory")))

    def test_path_consistency(self):
        """Test that all paths are consistent with the base directory"""
        paths = PathManager.list_paths()
        for key, path in paths.items():
            if not path.endswith('.json'):  # Skip JSON files
                self.assertTrue(
                    os.path.abspath(os.path.commonpath([path, self.temp_dir])) == os.path.abspath(self.temp_dir),
                    f"Path '{key}' is not within base directory"
                )

if __name__ == "__main__":
    unittest.main() 
