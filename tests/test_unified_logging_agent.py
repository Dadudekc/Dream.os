import os
import sys
import unittest
import json
import logging
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.UnifiedLoggingAgent import UnifiedLoggingAgent

class TestUnifiedLoggingAgent(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test log directory
        self.test_log_dir = os.path.join(os.path.dirname(__file__), "test_logs")
        os.makedirs(self.test_log_dir, exist_ok=True)
        
        # Test log file path
        self.test_log_file = os.path.join(self.test_log_dir, "test.log")
        
        # Initialize UnifiedLoggingAgent
        self.logging_agent = UnifiedLoggingAgent(
            log_file=self.test_log_file,
            log_level=logging.DEBUG,
            max_log_size=1024,  # 1KB for testing
            backup_count=2
        )
        
        # Test data
        self.test_log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": "Test log message",
            "context": {
                "user_id": "test_user",
                "action": "test_action"
            }
        }
    
    def test_initialization(self):
        """Test if UnifiedLoggingAgent initializes correctly."""
        self.assertIsNotNone(self.logging_agent)
        self.assertEqual(self.logging_agent.log_level, logging.DEBUG)
        self.assertEqual(self.logging_agent.max_log_size, 1024)
        self.assertEqual(self.logging_agent.backup_count, 2)
        self.assertTrue(os.path.exists(self.test_log_file))
    
    def test_log_message(self):
        """Test basic log message functionality."""
        # Test logging with different levels
        self.logging_agent.debug("Debug message")
        self.logging_agent.info("Info message")
        self.logging_agent.warning("Warning message")
        self.logging_agent.error("Error message")
        
        # Verify log file content
        with open(self.test_log_file, 'r') as f:
            log_content = f.read()
            self.assertIn("Debug message", log_content)
            self.assertIn("Info message", log_content)
            self.assertIn("Warning message", log_content)
            self.assertIn("Error message", log_content)
    
    def test_log_with_context(self):
        """Test logging with context data."""
        # Log with context
        self.logging_agent.info("Test message", context=self.test_log_data["context"])
        
        # Verify log file content
        with open(self.test_log_file, 'r') as f:
            log_content = f.read()
            self.assertIn("Test message", log_content)
            self.assertIn("user_id", log_content)
            self.assertIn("test_action", log_content)
    
    def test_log_rotation(self):
        """Test log file rotation."""
        # Fill log file beyond max size
        large_message = "x" * 1000  # 1KB message
        for _ in range(2):  # Write 2KB of data
            self.logging_agent.info(large_message)
        
        # Verify rotation
        log_files = [f for f in os.listdir(self.test_log_dir) if f.startswith("test.log")]
        self.assertTrue(len(log_files) > 1)  # Should have rotated files
    
    def test_log_analysis(self):
        """Test log analysis functionality."""
        # Generate test logs
        self.logging_agent.info("Success message", context={"status": "success"})
        self.logging_agent.error("Error message", context={"status": "error"})
        
        # Analyze logs
        analysis = self.logging_agent.analyze_logs()
        
        # Verify analysis
        self.assertIn("total_entries", analysis)
        self.assertIn("error_count", analysis)
        self.assertIn("warning_count", analysis)
        self.assertIn("info_count", analysis)
        self.assertIn("debug_count", analysis)
    
    def test_log_filtering(self):
        """Test log filtering functionality."""
        # Generate test logs
        self.logging_agent.info("User action", context={"user_id": "user1"})
        self.logging_agent.info("System action", context={"user_id": "system"})
        
        # Filter logs
        user_logs = self.logging_agent.filter_logs(lambda x: x.get("context", {}).get("user_id") == "user1")
        
        # Verify filtering
        self.assertEqual(len(user_logs), 1)
        self.assertEqual(user_logs[0]["message"], "User action")
    
    def test_log_export(self):
        """Test log export functionality."""
        # Generate test logs
        self.logging_agent.info("Test message 1")
        self.logging_agent.info("Test message 2")
        
        # Export logs
        export_file = os.path.join(self.test_log_dir, "exported_logs.json")
        self.logging_agent.export_logs(export_file)
        
        # Verify export
        self.assertTrue(os.path.exists(export_file))
        with open(export_file, 'r') as f:
            exported_logs = json.load(f)
            self.assertEqual(len(exported_logs), 2)
    
    def test_log_cleanup(self):
        """Test log cleanup functionality."""
        # Generate test logs
        for i in range(5):
            self.logging_agent.info(f"Test message {i}")
        
        # Cleanup old logs
        self.logging_agent.cleanup_old_logs(days=0)
        
        # Verify cleanup
        log_files = [f for f in os.listdir(self.test_log_dir) if f.startswith("test.log")]
        self.assertEqual(len(log_files), 1)  # Only current log file should remain
    
    def test_log_metrics(self):
        """Test log metrics collection."""
        # Generate test logs
        self.logging_agent.info("Message 1")
        self.logging_agent.error("Message 2")
        self.logging_agent.warning("Message 3")
        
        # Get metrics
        metrics = self.logging_agent.get_log_metrics()
        
        # Verify metrics
        self.assertIn("total_logs", metrics)
        self.assertIn("error_rate", metrics)
        self.assertIn("warning_rate", metrics)
        self.assertIn("average_log_size", metrics)
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test log directory
        if os.path.exists(self.test_log_dir):
            for file in os.listdir(self.test_log_dir):
                os.remove(os.path.join(self.test_log_dir, file))
            os.rmdir(self.test_log_dir)

if __name__ == '__main__':
    unittest.main() 