import os
import sys
import unittest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test config directory
        self.test_config_dir = os.path.join(os.path.dirname(__file__), "test_config")
        os.makedirs(self.test_config_dir, exist_ok=True)
        
        # Create test config files
        self.test_config = {
            "system": {
                "name": "Test System",
                "version": "1.0.0",
                "environment": "test"
            },
            "api": {
                "openai": {
                    "api_key": "test_key",
                    "model": "gpt-4"
                }
            },
            "logging": {
                "level": "DEBUG",
                "file": "test.log"
            }
        }
        
        self.test_config_path = os.path.join(self.test_config_dir, "config.json")
        with open(self.test_config_path, 'w') as f:
            json.dump(self.test_config, f)
        
        # Initialize ConfigManager
        self.config_manager = ConfigManager(
            config_path=self.test_config_path,
            environment="test"
        )
    
    def test_initialization(self):
        """Test if ConfigManager initializes correctly."""
        self.assertIsNotNone(self.config_manager)
        self.assertEqual(self.config_manager.environment, "test")
        self.assertEqual(self.config_manager.config["system"]["name"], "Test System")
        self.assertEqual(self.config_manager.config["api"]["openai"]["model"], "gpt-4")
    
    def test_load_config(self):
        """Test configuration loading."""
        # Test loading from file
        config = self.config_manager._load_config(self.test_config_path)
        self.assertEqual(config["system"]["name"], "Test System")
        
        # Test loading with environment override
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            config = self.config_manager._load_config(self.test_config_path)
            self.assertEqual(config["system"]["environment"], "production")
    
    def test_get_config(self):
        """Test configuration retrieval."""
        # Test getting entire config
        config = self.config_manager.get_config()
        self.assertEqual(config["system"]["name"], "Test System")
        
        # Test getting specific section
        api_config = self.config_manager.get_config("api")
        self.assertEqual(api_config["openai"]["model"], "gpt-4")
        
        # Test getting nested value
        model = self.config_manager.get_config("api.openai.model")
        self.assertEqual(model, "gpt-4")
    
    def test_update_config(self):
        """Test configuration updates."""
        # Test updating entire config
        new_config = self.test_config.copy()
        new_config["system"]["version"] = "2.0.0"
        self.config_manager.update_config(new_config)
        self.assertEqual(self.config_manager.get_config("system.version"), "2.0.0")
        
        # Test updating specific section
        self.config_manager.update_config({"api": {"new_key": "value"}}, "api")
        self.assertEqual(self.config_manager.get_config("api.new_key"), "value")
        
        # Test updating nested value
        self.config_manager.update_config("gpt-3.5", "api.openai.model")
        self.assertEqual(self.config_manager.get_config("api.openai.model"), "gpt-3.5")
    
    def test_save_config(self):
        """Test configuration saving."""
        # Update config
        self.config_manager.update_config("2.0.0", "system.version")
        
        # Save config
        self.config_manager.save_config()
        
        # Verify saved file
        with open(self.test_config_path, 'r') as f:
            saved_config = json.load(f)
            self.assertEqual(saved_config["system"]["version"], "2.0.0")
    
    def test_validate_config(self):
        """Test configuration validation."""
        # Test valid config
        self.assertTrue(self.config_manager._validate_config(self.test_config))
        
        # Test invalid config
        invalid_config = {"system": None}
        self.assertFalse(self.config_manager._validate_config(invalid_config))
    
    def test_get_environment_config(self):
        """Test environment-specific configuration."""
        # Test getting environment config
        env_config = self.config_manager.get_environment_config()
        self.assertEqual(env_config["environment"], "test")
        
        # Test environment override
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            env_config = self.config_manager.get_environment_config()
            self.assertEqual(env_config["environment"], "production")
    
    def test_merge_configs(self):
        """Test configuration merging."""
        base_config = {"system": {"name": "Base"}}
        override_config = {"system": {"name": "Override"}}
        
        merged = self.config_manager._merge_configs(base_config, override_config)
        self.assertEqual(merged["system"]["name"], "Override")
    
    def test_handle_config_error(self):
        """Test configuration error handling."""
        # Test invalid file path
        with self.assertRaises(FileNotFoundError):
            self.config_manager._load_config("nonexistent.json")
        
        # Test invalid JSON
        invalid_json_path = os.path.join(self.test_config_dir, "invalid.json")
        with open(invalid_json_path, 'w') as f:
            f.write("invalid json")
        
        with self.assertRaises(json.JSONDecodeError):
            self.config_manager._load_config(invalid_json_path)
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test config directory
        if os.path.exists(self.test_config_dir):
            for file in os.listdir(self.test_config_dir):
                os.remove(os.path.join(self.test_config_dir, file))
            os.rmdir(self.test_config_dir)

if __name__ == '__main__':
    unittest.main() 
