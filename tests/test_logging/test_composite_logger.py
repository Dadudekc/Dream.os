import unittest
from unittest.mock import Mock, patch
from core.logging.CompositeLogger import CompositeLogger
from core.ConsoleLogger import ConsoleLogger
from interfaces.pyqt.ILoggingAgent import ILoggingAgent

class MockLogger(ILoggingAgent):
    """Mock logger for testing."""
    def __init__(self):
        self.log_calls = []
        self.error_calls = []
        self.debug_calls = []
        self.event_calls = []
        self.system_calls = []
        
    def log(self, message: str, domain: str = "General", level: str = "INFO") -> None:
        self.log_calls.append((message, domain, level))
        
    def log_error(self, message: str, domain: str = "General") -> None:
        self.error_calls.append((message, domain))
        
    def log_debug(self, message: str, domain: str = "General") -> None:
        self.debug_calls.append((message, domain))
        
    def log_event(self, event_name: str, payload: dict, domain: str = "General") -> None:
        self.event_calls.append((event_name, payload, domain))
        
    def log_system_event(self, domain: str, event: str, message: str) -> None:
        self.system_calls.append((domain, event, message))

class TestCompositeLogger(unittest.TestCase):
    def setUp(self):
        self.logger1 = MockLogger()
        self.logger2 = MockLogger()
        self.fallback_logger = MockLogger()
        self.composite = CompositeLogger(
            [self.logger1, self.logger2],
            fallback_logger=self.fallback_logger
        )
        
    def tearDown(self):
        self.composite.shutdown()
        
    def test_log_distribution(self):
        """Test that logs are distributed to all loggers."""
        self.composite.log("test message", domain="Test", level="INFO")
        time.sleep(0.1)  # Allow async processing
        
        for logger in [self.logger1, self.logger2]:
            self.assertEqual(len(logger.log_calls), 1)
            self.assertEqual(logger.log_calls[0], ("test message", "Test", "INFO"))
            
    def test_error_handling(self):
        """Test error handling when a logger fails."""
        def failing_logger(*args, **kwargs):
            raise ValueError("Test error")
            
        self.logger1.log = failing_logger
        self.composite.log("test message")
        time.sleep(0.1)
        
        # Check fallback logger received error
        self.assertEqual(len(self.fallback_logger.error_calls), 1)
        self.assertIn("Logger MockLogger failed", self.fallback_logger.error_calls[0][0])
        
    def test_logger_management(self):
        """Test adding and removing loggers."""
        new_logger = MockLogger()
        self.composite.add_logger(new_logger)
        self.composite.log("test message")
        time.sleep(0.1)
        
        self.assertEqual(len(new_logger.log_calls), 1)
        
        self.composite.remove_logger(new_logger)
        self.composite.log("another message")
        time.sleep(0.1)
        
        self.assertEqual(len(new_logger.log_calls), 1)  # Should not increase
        
    def test_all_log_types(self):
        """Test all logging methods."""
        self.composite.log("info", domain="Test")
        self.composite.log_error("error", domain="Test")
        self.composite.log_debug("debug", domain="Test")
        self.composite.log_event("event", {"data": "test"}, domain="Test")
        self.composite.log_system_event("Test", "system", "message")
        
        time.sleep(0.1)
        
        for logger in [self.logger1, self.logger2]:
            self.assertEqual(len(logger.log_calls), 1)
            self.assertEqual(len(logger.error_calls), 1)
            self.assertEqual(len(logger.debug_calls), 1)
            self.assertEqual(len(logger.event_calls), 1)
            self.assertEqual(len(logger.system_calls), 1)
            
    def test_shutdown(self):
        """Test graceful shutdown."""
        self.composite.shutdown()
        # Verify dispatcher is shutdown
        self.assertFalse(self.composite.dispatcher.is_running)
        
if __name__ == '__main__':
    unittest.main() 