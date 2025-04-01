import unittest
from unittest.mock import Mock, patch
from core.logging.factories.LoggerFactory import LoggerFactory
from core.config.config_manager import ConfigManager
from core.ConsoleLogger import ConsoleLogger
from core.FileLogger import FileLogger
from core.DiscordLogger import DiscordLogger
from core.logging.CompositeLogger import CompositeLogger

class TestLoggerFactory(unittest.TestCase):
    def setUp(self):
        self.config_manager = Mock(spec=ConfigManager)
        
    def test_create_console_logger(self):
        """Test creation of console logger."""
        self.config_manager.get.return_value = {'types': ['console']}
        logger = LoggerFactory.create_logger(self.config_manager)
        self.assertIsInstance(logger, ConsoleLogger)
        
    def test_create_file_logger(self):
        """Test creation of file logger."""
        self.config_manager.get.return_value = {'types': ['file']}
        logger = LoggerFactory.create_logger(self.config_manager)
        self.assertIsInstance(logger, FileLogger)
        
    def test_create_discord_logger(self):
        """Test creation of discord logger."""
        self.config_manager.get.return_value = {'types': ['discord']}
        logger = LoggerFactory.create_logger(self.config_manager)
        self.assertIsInstance(logger, DiscordLogger)
        
    def test_create_composite_logger(self):
        """Test creation of composite logger with multiple types."""
        self.config_manager.get.return_value = {'types': ['console', 'file']}
        logger = LoggerFactory.create_logger(self.config_manager)
        self.assertIsInstance(logger, CompositeLogger)
        self.assertEqual(len(logger.loggers), 2)
        
    def test_fallback_to_console(self):
        """Test fallback to console logger when no types specified."""
        self.config_manager.get.return_value = {}
        logger = LoggerFactory.create_logger(self.config_manager)
        self.assertIsInstance(logger, ConsoleLogger)
        
    def test_invalid_logger_type(self):
        """Test handling of invalid logger type."""
        self.config_manager.get.return_value = {'types': ['invalid']}
        logger = LoggerFactory.create_logger(self.config_manager)
        self.assertIsInstance(logger, ConsoleLogger)  # Should fallback
        
    def test_logger_initialization_error(self):
        """Test handling of logger initialization errors."""
        with patch('core.FileLogger.FileLogger') as mock_file_logger:
            mock_file_logger.side_effect = Exception("Test error")
            self.config_manager.get.return_value = {'types': ['file']}
            logger = LoggerFactory.create_logger(self.config_manager)
            self.assertIsInstance(logger, ConsoleLogger)  # Should fallback
            
    def test_empty_logger_list(self):
        """Test handling of empty logger list."""
        self.config_manager.get.return_value = {'types': []}
        logger = LoggerFactory.create_logger(self.config_manager)
        self.assertIsInstance(logger, ConsoleLogger)  # Should fallback
        
if __name__ == '__main__':
    unittest.main() 
