import os
import sys
import unittest
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.TaskManager import TaskManager

class TestTaskManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test output directory
        self.test_output_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Initialize TaskManager
        self.task_manager = TaskManager(
            output_dir=self.test_output_dir,
            max_tasks=100,
            task_timeout=30
        )
        
        # Test data
        self.test_task = {
            "id": "test_task_1",
            "type": "processing",
            "priority": 1,
            "data": {
                "input": "test input",
                "parameters": {"param1": "value1"}
            },
            "schedule": {
                "start_time": datetime.now().isoformat(),
                "interval": 60  # 1 minute
            }
        }
    
    def test_initialization(self):
        """Test if TaskManager initializes correctly."""
        self.assertIsNotNone(self.task_manager)
        self.assertEqual(self.task_manager.max_tasks, 100)
        self.assertEqual(self.task_manager.task_timeout, 30)
        self.assertTrue(os.path.exists(self.task_manager.output_dir))
        self.assertIsNotNone(self.task_manager.logger)
    
    def test_add_task(self):
        """Test task addition functionality."""
        # Add task
        task_id = self.task_manager.add_task(self.test_task)
        
        # Verify task was added
        self.assertEqual(task_id, "test_task_1")
        self.assertIn(task_id, self.task_manager.tasks)
        self.assertEqual(self.task_manager.tasks[task_id]["type"], "processing")
    
    def test_get_task(self):
        """Test task retrieval functionality."""
        # Add task
        task_id = self.task_manager.add_task(self.test_task)
        
        # Get task
        task = self.task_manager.get_task(task_id)
        
        # Verify task data
        self.assertEqual(task["id"], task_id)
        self.assertEqual(task["type"], "processing")
        self.assertEqual(task["priority"], 1)
    
    def test_update_task(self):
        """Test task update functionality."""
        # Add task
        task_id = self.task_manager.add_task(self.test_task)
        
        # Update task
        update_data = {
            "priority": 2,
            "data": {"input": "updated input"}
        }
        self.task_manager.update_task(task_id, update_data)
        
        # Verify update
        task = self.task_manager.get_task(task_id)
        self.assertEqual(task["priority"], 2)
        self.assertEqual(task["data"]["input"], "updated input")
    
    def test_delete_task(self):
        """Test task deletion functionality."""
        # Add task
        task_id = self.task_manager.add_task(self.test_task)
        
        # Delete task
        self.task_manager.delete_task(task_id)
        
        # Verify deletion
        self.assertNotIn(task_id, self.task_manager.tasks)
        with self.assertRaises(KeyError):
            self.task_manager.get_task(task_id)
    
    def test_list_tasks(self):
        """Test task listing functionality."""
        # Add multiple tasks
        tasks = []
        for i in range(3):
            task = self.test_task.copy()
            task["id"] = f"test_task_{i}"
            task["priority"] = i
            tasks.append(self.task_manager.add_task(task))
        
        # List tasks
        task_list = self.task_manager.list_tasks()
        
        # Verify list
        self.assertEqual(len(task_list), 3)
        self.assertEqual(len(tasks), 3)
    
    def test_schedule_task(self):
        """Test task scheduling functionality."""
        # Create scheduled task
        scheduled_task = self.test_task.copy()
        scheduled_task["schedule"] = {
            "start_time": (datetime.now() + timedelta(seconds=1)).isoformat(),
            "interval": 60
        }
        
        # Schedule task
        task_id = self.task_manager.schedule_task(scheduled_task)
        
        # Wait for task to start
        time.sleep(2)
        
        # Verify task is running
        task = self.task_manager.get_task(task_id)
        self.assertEqual(task["status"], "running")
    
    def test_task_priority_queue(self):
        """Test task priority queue functionality."""
        # Add tasks with different priorities
        tasks = []
        for i in range(3):
            task = self.test_task.copy()
            task["id"] = f"test_task_{i}"
            task["priority"] = 3 - i  # 3, 2, 1
            tasks.append(self.task_manager.add_task(task))
        
        # Get next task
        next_task = self.task_manager.get_next_task()
        
        # Verify priority order
        self.assertEqual(next_task["priority"], 3)
    
    def test_task_timeout(self):
        """Test task timeout handling."""
        # Add task with short timeout
        task = self.test_task.copy()
        task["timeout"] = 1
        task_id = self.task_manager.add_task(task)
        
        # Start task
        self.task_manager.start_task(task_id)
        
        # Wait for timeout
        time.sleep(2)
        
        # Verify timeout
        task = self.task_manager.get_task(task_id)
        self.assertEqual(task["status"], "timeout")
    
    def test_task_retry(self):
        """Test task retry functionality."""
        # Add task with retry configuration
        task = self.test_task.copy()
        task["retry"] = {
            "max_attempts": 3,
            "delay": 1
        }
        task_id = self.task_manager.add_task(task)
        
        # Simulate task failure
        self.task_manager.fail_task(task_id, "Test error")
        
        # Verify retry
        task = self.task_manager.get_task(task_id)
        self.assertEqual(task["attempts"], 1)
        self.assertEqual(task["status"], "retrying")
    
    def test_task_dependencies(self):
        """Test task dependency handling."""
        # Create dependent tasks
        parent_task = self.test_task.copy()
        parent_id = self.task_manager.add_task(parent_task)
        
        child_task = self.test_task.copy()
        child_task["id"] = "child_task"
        child_task["dependencies"] = [parent_id]
        child_id = self.task_manager.add_task(child_task)
        
        # Verify dependency
        child = self.task_manager.get_task(child_id)
        self.assertIn(parent_id, child["dependencies"])
        
        # Complete parent task
        self.task_manager.complete_task(parent_id)
        
        # Verify child task is ready
        child = self.task_manager.get_task(child_id)
        self.assertEqual(child["status"], "ready")
    
    def test_task_metrics(self):
        """Test task metrics collection."""
        # Add and complete multiple tasks
        for i in range(3):
            task = self.test_task.copy()
            task["id"] = f"test_task_{i}"
            task_id = self.task_manager.add_task(task)
            self.task_manager.complete_task(task_id)
        
        # Get metrics
        metrics = self.task_manager.get_metrics()
        
        # Verify metrics
        self.assertIn("total_tasks", metrics)
        self.assertIn("completed_tasks", metrics)
        self.assertIn("failed_tasks", metrics)
        self.assertIn("average_execution_time", metrics)
    
    def test_task_persistence(self):
        """Test task persistence functionality."""
        # Add task
        task_id = self.task_manager.add_task(self.test_task)
        
        # Save tasks
        self.task_manager.save_tasks()
        
        # Create new manager
        new_manager = TaskManager(
            output_dir=self.test_output_dir,
            max_tasks=100,
            task_timeout=30
        )
        
        # Load tasks
        new_manager.load_tasks()
        
        # Verify task persistence
        task = new_manager.get_task(task_id)
        self.assertEqual(task["id"], task_id)
        self.assertEqual(task["type"], "processing")
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test output directory
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)

if __name__ == '__main__':
    unittest.main() 