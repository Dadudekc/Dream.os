import os
import sys
import unittest
import json
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ThreadPoolManager import ThreadPoolManager

class TestThreadPoolManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test output directory
        self.test_output_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Initialize ThreadPoolManager
        self.pool_manager = ThreadPoolManager(
            max_workers=3,
            output_dir=self.test_output_dir,
            log_level="DEBUG"
        )
        
        # Test data
        self.test_task = {
            "id": "test_task_1",
            "type": "processing",
            "data": {
                "input": "test input",
                "parameters": {"param1": "value1"}
            }
        }
    
    def test_initialization(self):
        """Test if ThreadPoolManager initializes correctly."""
        self.assertIsNotNone(self.pool_manager)
        self.assertEqual(self.pool_manager.max_workers, 3)
        self.assertTrue(os.path.exists(self.pool_manager.output_dir))
        self.assertIsNotNone(self.pool_manager.logger)
    
    def test_submit_task(self):
        """Test task submission functionality."""
        # Define test function
        def test_function(task_data):
            return {"result": f"Processed {task_data['input']}"}
        
        # Submit task
        future = self.pool_manager.submit_task(test_function, self.test_task)
        
        # Get result
        result = future.result()
        
        # Verify execution
        self.assertEqual(result["result"], "Processed test input")
    
    def test_submit_multiple_tasks(self):
        """Test submitting multiple tasks."""
        # Define test function
        def test_function(task_data):
            time.sleep(0.1)  # Simulate work
            return {"result": f"Processed {task_data['input']}"}
        
        # Submit multiple tasks
        tasks = []
        for i in range(5):
            task = self.test_task.copy()
            task["id"] = f"test_task_{i}"
            task["data"]["input"] = f"input_{i}"
            tasks.append(self.pool_manager.submit_task(test_function, task))
        
        # Get results
        results = [task.result() for task in tasks]
        
        # Verify execution
        self.assertEqual(len(results), 5)
        for i, result in enumerate(results):
            self.assertEqual(result["result"], f"Processed input_{i}")
    
    def test_task_priority(self):
        """Test task priority handling."""
        # Define test function
        def test_function(task_data):
            return {"result": f"Processed {task_data['input']}"}
        
        # Submit tasks with different priorities
        low_priority = self.test_task.copy()
        low_priority["priority"] = 1
        high_priority = self.test_task.copy()
        high_priority["id"] = "high_priority"
        high_priority["priority"] = 2
        
        # Submit tasks
        low_future = self.pool_manager.submit_task(test_function, low_priority)
        high_future = self.pool_manager.submit_task(test_function, high_priority)
        
        # Get results
        low_result = low_future.result()
        high_result = high_future.result()
        
        # Verify execution
        self.assertEqual(low_result["result"], "Processed test input")
        self.assertEqual(high_result["result"], "Processed test input")
    
    def test_task_cancellation(self):
        """Test task cancellation functionality."""
        # Define long-running test function
        def long_running_function(task_data):
            time.sleep(1)  # Simulate long-running task
            return {"result": "Completed"}
        
        # Submit task
        future = self.pool_manager.submit_task(long_running_function, self.test_task)
        
        # Cancel task
        future.cancel()
        
        # Verify cancellation
        with self.assertRaises(Exception):
            future.result()
    
    def test_task_timeout(self):
        """Test task timeout handling."""
        # Define timeout test function
        def timeout_function(task_data):
            time.sleep(2)  # Simulate timeout
            return {"result": "Completed"}
        
        # Submit task with timeout
        future = self.pool_manager.submit_task(timeout_function, self.test_task, timeout=1)
        
        # Verify timeout
        with self.assertRaises(TimeoutError):
            future.result(timeout=1)
    
    def test_task_error_handling(self):
        """Test task error handling."""
        # Define error test function
        def error_function(task_data):
            raise ValueError("Test error")
        
        # Submit task
        future = self.pool_manager.submit_task(error_function, self.test_task)
        
        # Verify error handling
        with self.assertRaises(ValueError):
            future.result()
    
    def test_pool_shutdown(self):
        """Test thread pool shutdown."""
        # Submit some tasks
        def test_function(task_data):
            return {"result": "Completed"}
        
        futures = []
        for i in range(3):
            task = self.test_task.copy()
            task["id"] = f"test_task_{i}"
            futures.append(self.pool_manager.submit_task(test_function, task))
        
        # Shutdown pool
        self.pool_manager.shutdown()
        
        # Verify shutdown
        self.assertTrue(self.pool_manager.pool._shutdown)
        
        # Verify completed tasks
        for future in futures:
            self.assertEqual(future.result()["result"], "Completed")
    
    def test_task_metrics(self):
        """Test task metrics collection."""
        # Submit multiple tasks
        def test_function(task_data):
            time.sleep(0.1)  # Simulate work
            return {"result": "Completed"}
        
        for i in range(3):
            task = self.test_task.copy()
            task["id"] = f"test_task_{i}"
            self.pool_manager.submit_task(test_function, task)
        
        # Get metrics
        metrics = self.pool_manager.get_metrics()
        
        # Verify metrics
        self.assertIn("total_tasks", metrics)
        self.assertIn("completed_tasks", metrics)
        self.assertIn("failed_tasks", metrics)
        self.assertIn("average_execution_time", metrics)
    
    def test_task_logging(self):
        """Test task logging functionality."""
        # Submit task
        def test_function(task_data):
            return {"result": "Completed"}
        
        self.pool_manager.submit_task(test_function, self.test_task)
        
        # Verify logging
        log_file = os.path.join(self.test_output_dir, "thread_pool.log")
        self.assertTrue(os.path.exists(log_file))
        
        with open(log_file, 'r') as f:
            log_content = f.read()
            self.assertIn("test_task_1", log_content)
            self.assertIn("Completed", log_content)
    
    def tearDown(self):
        """Clean up after each test."""
        # Shutdown pool
        self.pool_manager.shutdown()
        
        # Remove test output directory
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)

if __name__ == '__main__':
    unittest.main() 
