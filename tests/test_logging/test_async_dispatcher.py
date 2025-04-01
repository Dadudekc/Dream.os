import unittest
import threading
import time
from unittest.mock import Mock, patch
from core.logging.utils.AsyncDispatcher import AsyncDispatcher

class TestAsyncDispatcher(unittest.TestCase):
    def setUp(self):
        self.dispatcher = AsyncDispatcher(max_queue_size=10)
        self.mock_callback = Mock()
        
    def tearDown(self):
        self.dispatcher.shutdown()
        
    def test_dispatch_success(self):
        """Test successful dispatch of a callback."""
        self.dispatcher.dispatch(self.mock_callback, "test", arg1="value")
        time.sleep(0.1)  # Allow worker to process
        self.mock_callback.assert_called_once_with("test", arg1="value")
        
    def test_dispatch_queue_full(self):
        """Test dispatch behavior when queue is full."""
        # Fill the queue
        for _ in range(10):
            self.dispatcher.dispatch(self.mock_callback, "test")
            
        # This should execute synchronously
        self.dispatcher.dispatch(self.mock_callback, "overflow")
        self.assertEqual(self.mock_callback.call_count, 11)
        
    def test_shutdown(self):
        """Test graceful shutdown of dispatcher."""
        self.dispatcher.shutdown()
        self.assertFalse(self.dispatcher.is_running)
        self.assertFalse(self.dispatcher.worker_thread.is_alive())
        
    def test_error_handling(self):
        """Test error handling in worker thread."""
        def failing_callback(*args, **kwargs):
            raise ValueError("Test error")
            
        with patch('builtins.print') as mock_print:
            self.dispatcher.dispatch(failing_callback, "test")
            time.sleep(0.1)
            mock_print.assert_called_once()
            
    def test_multiple_dispatches(self):
        """Test handling multiple dispatches."""
        for i in range(5):
            self.dispatcher.dispatch(self.mock_callback, f"test_{i}")
            
        time.sleep(0.1)
        self.assertEqual(self.mock_callback.call_count, 5)
        
if __name__ == '__main__':
    unittest.main() 
