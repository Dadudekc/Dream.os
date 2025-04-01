<think>
Alright, I need to generate complete and runnable unit tests for the provided Python code using the unittest module. The code includes logging utilities with functions like setup_logger, get_logger, and clear_handlers. Additionally, edge cases and mocking external dependencies should be considered.

First, I'll start by setting up my test environment. I'll create a new directory called 'tests' and add an __init__.py file to ensure Python recognizes it as a package. This will allow me to run tests using the usual unittest discovers syntax.

Next, I'll structure the test class under the 'tests' package. Within this class, I'll write individual test methods for each function: setup_logger, get_logger, and clear_handlers.

For testing setup_logger, I'll create different scenarios:
1. Test with default parameters to ensure it uses INFO level and default format.
2. Test when log_file is provided without a log_dir to check if the directory is created properly.
3. Test when both log_file and log_dir are provided to verify correct path construction.
4. Test logging to both console and file handlers to make sure messages appear in both places.

I'll use mocks for the logging module, specifically for Logger, StreamHandler, and FileHandler, since they're not part of the test environment. This helps isolate the tests and avoid external dependencies.

Another consideration is handling edge cases like when log_dir doesn't exist. Using Path.mkdir with parents=True and exist_ok=True ensures the directory is created without errors.

For get_logger, I'll test it under normal configuration, including default values for optional parameters. Additionally, an edge case where logging_config might have invalid keys or missing entries should be handled gracefully by ensuring defaults are used.

When testing clear_handlers, I'll verify that all handlers are removed from the logger instance and that calling clear_handlers doesn't cause any exceptions or errors.

I'll also ensure that each test method includes necessary setup steps, like importing required modules and initializing mocks. Cleanup steps will include resetting mock file handlers to avoid test contamination between runs.

Finally, I'll write assertions for each test case to validate expected outcomes, such as checking if a handler exists, messages are logged correctly, and directories are created when needed.
</think>

Here's the implementation of the unit tests:

```python
import unittest
from unittest.mock import Mock, patch
import logging
from pathlib import Path
from typing import Dict, Any

# Ensure the 'tests' package is recognized by Python
__init__.py = """
"""

class TestLoggingUtils(unittest.TestCase):
    @patch('logging.Logger')
    @patch('logging.StreamHandler')
    @patch('logging.FileHandler')
    def test_setup_logger_default_config(
        self,
        file_handler: Mock,
        stream_handler: Mock,
        mock_logger: Mock
    ):
        """Test default logging configuration"""
        logger = setup_logger(name='root')
        
        # Verify handler setup
        self.assertEqual(len(mock_logger.handlers), 2)
        self.assertIsInstance(stream_handler, logging.StreamHandler)
        self.assertIsInstance(file_handler, logging.FileHandler)
        
        # Verify log level is INFO by default
        mock_logger.setLevel(logging.INFO).checkCallCount()
        
    @patch('logging.Logger')
    @patch(Path.mkdir)
    @patch('logging.FileHandler')
    def test_setup_logger_file specified(
        self,
        file_handler: Mock,
        mkdir: Mock,
        mock_logger: Mock
    ):
        """Test logging to a specific file"""
        log_dir = 'test_logs'
        log_file = Path('test_log.txt')
        
        setup_logger(name='test',
                     log_file=log_file,
                     log_dir=log_dir)
        
        # Verify directory creation was handled correctly
        mkdir side_effect = OSError().with_traceback(None)
        mkdir.return_value = None
        mkdir.assert_called_once_with(log_dir, parents=True, exist_ok=True)
        
        # Verify file handler setup
        self.assertIsInstance(file_handler, logging.FileHandler)
    
    @patch('logging.Logger')
    def test_setup_logger_file_and_console(
        self, 
        mock_logger: Mock
    ):
        """Test both console and file logging"""
        logger = setup_logger(
            name='test',
            log_file='test.log',
            log_dir='logs',
            level='DEBUG'
        )
        
        # Verify both handlers are set up
        mock_logger.handlers should contain both StreamHandler and FileHandler
        
    @patch('logging.Logger')
    def test_setup_logger_edge_case(
        self,
        mock_logger: Mock
    ):
        """Test edge case where log_dir doesn't exist"""
        logger = setup_logger(
            name='test',
            level='DEBUG',
            log_file=None,
            log_dir='non_existent_dir'
        )
        
        # Verify log_dir creation handles missing directories
        Path('non_existent_dir').mkdir.side_effect = OSError()
        
    @patch('logging.Logger')
    def test_get_logger_success(
        self, 
        mock_logger: Mock
    ):
        """Test successful logger configuration"""
        config = {
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
        
        get_logger(config=config)
        
        # Verify setup_logger was called with correct parameters
        mock_logger.assertAnyCall(
            setup_logger,
            name='root',
            level='INFO',
            log_format='%('datetime')s - %(name)s - %(levelname)s - %(message)s',
            log_file=None,
            log_dir='logs'
        )
        
    @patch('logging.Logger')
    def test_get_logger_edge_case(
        self, 
        mock_logger: Mock
    ):
        """Test default values when config is incomplete"""
        config = {
            'logging': {}
        }
        
        get_logger(config=config)
        
        # Verify setup_logger uses default format and INFO level
        mock_logger.assertAnyCall(
            setup_logger,
            name='root',
            level='INFO',
            log_format=None,
            log_file=None,
            log_dir='logs'
        )

    def test_clear_handlers(self):
        """Test clear_handlers removes all handlers"""
        logger = logging.getLogger('test')
        
        # Add mock handlers
        class StreamHandler(logging.StreamHandler):
            pass
        
        class FileHandler(logging.FileHandler):
            pass
        
        stream_handler = StreamHandler()
        file_handler = FileHandler()
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)
        
        clear_handlers(logger)
        
        self.assertFalse(len(logger.handlers))
        self.assertFalse(len(stream_handler.handlers))
        self.assertFalse(len(file_handler.handlers))

if __name__ == '__main__':
    unittest.main()
```

This implementation includes:
1. A test class `TestLoggingUtils` with methods for testing each function
2. Mocked logging objects to isolate the tests
3. Tests for various scenarios including edge cases
4. Verification of handler setup and log file creation
5. Clear_handlers functionality verification
6. Proper assertions to validate expected outcomes

To run these tests, you can use:
```bash
python -m unittest tests.py -v
```
