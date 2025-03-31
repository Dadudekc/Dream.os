#!/usr/bin/env python3
"""
TaskQueueManager - Priority queue with persistence and dependency resolution
===========================================================================

Replaces the standard Queue with a PriorityQueue implementation that supports:
1. Task prioritization (high/medium/low)
2. Persistence to disk (save/load)
3. Dependency resolution (tasks wait for dependencies to complete)
4. Task status tracking

This enables more sophisticated task management for the cursor session.
"""

import os
import json
import time
import heapq
import logging
import threading
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from datetime import datetime
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Status of a task in the queue"""
    PENDING = "pending"           # Task waiting to be executed
    BLOCKED = "blocked"           # Task waiting for dependencies
    RUNNING = "running"           # Task currently being executed
    COMPLETED = "completed"       # Task completed successfully
    FAILED = "failed"             # Task failed
    CANCELLED = "cancelled"       # Task cancelled by user


class TaskPriority(Enum):
    """Priority levels for tasks"""
    HIGH = 0       # High priority (0 = highest in heapq)
    MEDIUM = 50    # Medium priority
    LOW = 100      # Low priority
    
    @classmethod
    def from_string(cls, priority_str: str) -> 'TaskPriority':
        """Convert string priority to enum value"""
        priority_map = {
            "high": cls.HIGH,
            "medium": cls.MEDIUM,
            "low": cls.LOW
        }
        return priority_map.get(priority_str.lower(), cls.MEDIUM)


class PriorityTaskQueue:
    """
    A priority queue for tasks with persistence and dependency management.
    
    Features:
    - Tasks are prioritized based on priority field
    - Queue can be saved to disk and loaded to recover state
    - Tasks with dependencies are blocked until dependencies complete
    - Supports task status tracking
    """
    
    def __init__(self, queue_file_path: str = None):
        """
        Initialize the priority task queue.
        
        Args:
            queue_file_path: Path to file for persisting queue state
        """
        self._queue = []  # heap queue [(priority_value, timestamp, task_id, task), ...]
        self._tasks = {}  # map of task_id to task dict
        self._lock = threading.RLock()
        self._queue_file_path = queue_file_path or "task_queue.json"
        
        # Status tracking
        self._pending = set()    # task_ids that are pending
        self._blocked = set()    # task_ids that are blocked by dependencies
        self._running = set()    # task_ids that are currently running
        self._completed = set()  # task_ids that have completed successfully
        self._failed = set()     # task_ids that have failed
        
        # Try to load existing queue from disk
        self.load_queue()
        
        logger.info(f"PriorityTaskQueue initialized with {len(self._tasks)} tasks")
    
    def put(self, task: Dict[str, Any]) -> str:
        """
        Add a task to the queue with the specified priority.
        Assigns a task_id if not present. Updates status based on dependencies.
        
        Args:
            task: Task dictionary with optional 'priority' field
            
        Returns:
            The task_id
        """
        with self._lock:
            # Ensure task has required fields
            if "task_id" not in task:
                task["task_id"] = f"task_{int(time.time() * 1000)}"
            
            task_id = task["task_id"]
            
            # Set creation timestamp if not present
            if "created_at" not in task:
                task["created_at"] = datetime.now().isoformat()
                
            # Convert string priority to enum value and get numeric priority
            priority_str = task.get("priority", "medium")
            priority = TaskPriority.from_string(priority_str)
            priority_value = priority.value
            
            # Get submission timestamp for tiebreaker
            timestamp = time.time()
            
            # Set initial status
            depends_on = task.get("depends_on", [])
            if depends_on and not all(dep_id in self._completed for dep_id in depends_on):
                task["status"] = TaskStatus.BLOCKED.value
                self._blocked.add(task_id)
            else:
                task["status"] = TaskStatus.PENDING.value
                self._pending.add(task_id)
            
            # Store task in tasks dict and push to queue
            self._tasks[task_id] = task
            heapq.heappush(self._queue, (priority_value, timestamp, task_id, task))
            
            # Save queue state
            self.save_queue()
            
            logger.info(f"Added task {task_id} with priority {priority_str}")
            return task_id
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Get the next available task with the highest priority.
        Only returns tasks that are PENDING (not blocked by dependencies).
        
        Args:
            block: If True, block until a task is available
            timeout: Timeout in seconds if blocking
            
        Returns:
            The next task or None if the queue is empty or timeout occurs
        """
        start_time = time.time()
        while True:
            with self._lock:
                # Find the first pending task (not blocked)
                for i, (_, _, task_id, task) in enumerate(self._queue):
                    if task_id in self._pending:
                        # Remove task from queue and update status
                        self._queue.pop(i)
                        heapq.heapify(self._queue)  # Reheapify after removal
                        
                        # Update status
                        task["status"] = TaskStatus.RUNNING.value
                        self._pending.remove(task_id)
                        self._running.add(task_id)
                        
                        # Save queue state
                        self.save_queue()
                        
                        logger.info(f"Retrieved task {task_id} from queue")
                        return task
            
            # If not blocking or timeout, return None
            if not block:
                return None
            
            # Check timeout
            if timeout is not None and time.time() - start_time > timeout:
                return None
            
            # Sleep a bit before trying again
            time.sleep(0.1)
    
    def task_completed(self, task_id: str, success: bool = True) -> None:
        """
        Mark a task as completed and resolve dependencies.
        
        Args:
            task_id: ID of the completed task
            success: Whether the task completed successfully
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"Cannot complete unknown task {task_id}")
                return
            
            task = self._tasks[task_id]
            
            # Update status
            if success:
                task["status"] = TaskStatus.COMPLETED.value
                self._completed.add(task_id)
                logger.info(f"Task {task_id} completed successfully")
            else:
                task["status"] = TaskStatus.FAILED.value
                self._failed.add(task_id)
                logger.info(f"Task {task_id} failed")
            
            # Remove from running set
            if task_id in self._running:
                self._running.remove(task_id)
            
            # Set completion timestamp
            task["completed_at"] = datetime.now().isoformat()
            
            # Resolve dependencies
            if success:
                self._resolve_dependencies(task_id)
            
            # Save queue state
            self.save_queue()
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending or blocked task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"Cannot cancel unknown task {task_id}")
                return False
            
            task = self._tasks[task_id]
            
            # Can only cancel pending or blocked tasks
            if task_id not in self._pending and task_id not in self._blocked:
                logger.warning(f"Cannot cancel task {task_id} with status {task['status']}")
                return False
            
            # Update status
            task["status"] = TaskStatus.CANCELLED.value
            
            # Remove from pending or blocked set
            if task_id in self._pending:
                self._pending.remove(task_id)
            if task_id in self._blocked:
                self._blocked.remove(task_id)
            
            # Remove from queue (more complex since we need to find it)
            for i, (_, _, queue_task_id, _) in enumerate(self._queue):
                if queue_task_id == task_id:
                    self._queue.pop(i)
                    heapq.heapify(self._queue)  # Reheapify after removal
                    break
            
            # Set cancellation timestamp
            task["cancelled_at"] = datetime.now().isoformat()
            
            # Save queue state
            self.save_queue()
            
            logger.info(f"Task {task_id} cancelled")
            return True
    
    def update_priority(self, task_id: str, priority: Union[str, TaskPriority]) -> bool:
        """
        Update the priority of a pending or blocked task.
        
        Args:
            task_id: ID of the task to update
            priority: New priority (string or enum)
            
        Returns:
            True if the priority was updated, False otherwise
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"Cannot update priority of unknown task {task_id}")
                return False
            
            task = self._tasks[task_id]
            
            # Can only update pending or blocked tasks
            if task_id not in self._pending and task_id not in self._blocked:
                logger.warning(f"Cannot update priority of task {task_id} with status {task['status']}")
                return False
            
            # Convert priority to enum if string
            if isinstance(priority, str):
                priority = TaskPriority.from_string(priority)
            
            # Update task priority
            task["priority"] = priority.name.lower()
            
            # Remove and re-add to queue with new priority
            for i, (_, _, queue_task_id, _) in enumerate(self._queue):
                if queue_task_id == task_id:
                    self._queue.pop(i)
                    heapq.heapify(self._queue)  # Reheapify after removal
                    break
            
            # Re-add to queue with new priority
            heapq.heappush(self._queue, (priority.value, time.time(), task_id, task))
            
            # Save queue state
            self.save_queue()
            
            logger.info(f"Updated priority of task {task_id} to {priority.name.lower()}")
            return True
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            The task or None if not found
        """
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all tasks, sorted by priority.
        
        Returns:
            List of all tasks
        """
        with self._lock:
            # Sort tasks by priority and timestamp
            sorted_tasks = sorted(
                self._tasks.values(),
                key=lambda t: (
                    TaskPriority.from_string(t.get("priority", "medium")).value,
                    t.get("created_at", "")
                )
            )
            return sorted_tasks
    
    def get_status_counts(self) -> Dict[str, int]:
        """
        Get counts of tasks by status.
        
        Returns:
            Dict mapping status names to counts
        """
        with self._lock:
            return {
                TaskStatus.PENDING.value: len(self._pending),
                TaskStatus.BLOCKED.value: len(self._blocked),
                TaskStatus.RUNNING.value: len(self._running),
                TaskStatus.COMPLETED.value: len(self._completed),
                TaskStatus.FAILED.value: len(self._failed),
                TaskStatus.CANCELLED.value: len(self._tasks) - (
                    len(self._pending) + len(self._blocked) + 
                    len(self._running) + len(self._completed) + 
                    len(self._failed)
                )
            }
    
    def save_queue(self) -> bool:
        """
        Save the queue state to disk.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            queue_dir = os.path.dirname(self._queue_file_path)
            if queue_dir and not os.path.exists(queue_dir):
                os.makedirs(queue_dir, exist_ok=True)
            
            # Save tasks dict (not the queue itself)
            with open(self._queue_file_path, "w") as f:
                json.dump(list(self._tasks.values()), f, indent=2)
            
            logger.debug(f"Saved task queue to {self._queue_file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save task queue: {e}")
            return False
    
    def load_queue(self) -> bool:
        """
        Load the queue state from disk.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if not os.path.exists(self._queue_file_path):
            logger.info(f"No saved queue found at {self._queue_file_path}")
            return False
        
        try:
            with open(self._queue_file_path, "r") as f:
                tasks = json.load(f)
            
            # Clear existing data
            self._queue = []
            self._tasks = {}
            self._pending.clear()
            self._blocked.clear()
            self._running.clear()
            self._completed.clear()
            self._failed.clear()
            
            # Add each task
            for task in tasks:
                task_id = task["task_id"]
                self._tasks[task_id] = task
                
                # Update status sets
                status = task.get("status", TaskStatus.PENDING.value)
                if status == TaskStatus.PENDING.value:
                    self._pending.add(task_id)
                    # Add to queue with priority
                    priority = TaskPriority.from_string(task.get("priority", "medium"))
                    timestamp = time.time()  # Use current time as tiebreaker
                    heapq.heappush(self._queue, (priority.value, timestamp, task_id, task))
                elif status == TaskStatus.BLOCKED.value:
                    self._blocked.add(task_id)
                    # Add to queue with priority
                    priority = TaskPriority.from_string(task.get("priority", "medium"))
                    timestamp = time.time()  # Use current time as tiebreaker
                    heapq.heappush(self._queue, (priority.value, timestamp, task_id, task))
                elif status == TaskStatus.RUNNING.value:
                    self._running.add(task_id)
                elif status == TaskStatus.COMPLETED.value:
                    self._completed.add(task_id)
                elif status == TaskStatus.FAILED.value:
                    self._failed.add(task_id)
            
            logger.info(f"Loaded {len(self._tasks)} tasks from {self._queue_file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load task queue: {e}")
            return False
    
    def _resolve_dependencies(self, completed_task_id: str) -> None:
        """
        Resolve dependencies for all tasks that depend on the completed task.
        
        Args:
            completed_task_id: ID of the completed task
        """
        for task_id, task in self._tasks.items():
            # Skip non-blocked tasks
            if task_id not in self._blocked:
                continue
            
            # Check if the task depends on the completed task
            depends_on = task.get("depends_on", [])
            if completed_task_id in depends_on:
                # Check if all dependencies are now satisfied
                all_deps_completed = all(
                    dep_id in self._completed
                    for dep_id in depends_on
                )
                
                if all_deps_completed:
                    # Update status
                    task["status"] = TaskStatus.PENDING.value
                    self._blocked.remove(task_id)
                    self._pending.add(task_id)
                    
                    logger.info(f"Unblocked task {task_id} after {completed_task_id} completed")
    
    def clear_completed(self, clear_failed: bool = False) -> int:
        """
        Clear completed tasks from the task dictionary.
        
        Args:
            clear_failed: Whether to also clear failed tasks
            
        Returns:
            Number of tasks cleared
        """
        with self._lock:
            to_clear = set(self._completed)
            if clear_failed:
                to_clear.update(self._failed)
            
            # Clear tasks
            for task_id in to_clear:
                if task_id in self._tasks:
                    del self._tasks[task_id]
            
            # Update sets
            count = len(to_clear)
            self._completed.clear()
            if clear_failed:
                self._failed.clear()
            
            # Save queue state
            self.save_queue()
            
            logger.info(f"Cleared {count} completed/failed tasks")
            return count
    
    def __len__(self) -> int:
        """
        Get the number of tasks in the queue (pending + blocked).
        
        Returns:
            Number of tasks in the queue
        """
        with self._lock:
            return len(self._pending) + len(self._blocked)
    
    def is_empty(self) -> bool:
        """
        Check if the queue is empty (no pending or blocked tasks).
        
        Returns:
            True if the queue is empty, False otherwise
        """
        with self._lock:
            return len(self._pending) + len(self._blocked) == 0
    
    def peek(self) -> Optional[Dict[str, Any]]:
        """
        Peek at the next task that would be returned by get().
        Does not remove the task from the queue.
        
        Returns:
            The next task or None if the queue is empty
        """
        with self._lock:
            # Find the first pending task (not blocked)
            for _, _, task_id, task in self._queue:
                if task_id in self._pending:
                    return task
            return None 