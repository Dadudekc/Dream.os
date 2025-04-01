#!/usr/bin/env python3
"""
CursorExecutor - Isolated task execution with parallel processing
================================================================

Provides an isolated lifecycle and parallel execution environment for tasks,
particularly for test generation and code manipulation tasks that need
controlled execution contexts.

Features:
- Execute tasks in isolated processes to prevent interference
- Support for parallel execution of multiple tasks
- Task lifecycle management (setup, execute, cleanup)
- Result collection and error handling
- Support for timeout and cancellation
"""

import os
import sys
import time
import uuid
import signal
import logging
import threading
import multiprocessing
from queue import Empty
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future, as_completed
from datetime import datetime, timedelta

# Local imports
from core.structured_logger import StructuredLogger

# Configure logging
logger = logging.getLogger(__name__)

class TaskExecutionError(Exception):
    """Exception raised when task execution fails"""
    def __init__(self, message: str, task_id: str = None, error_type: str = None, details: Any = None):
        self.message = message
        self.task_id = task_id
        self.error_type = error_type
        self.details = details
        super().__init__(self.message)

class TaskTimeoutError(TaskExecutionError):
    """Exception raised when task execution times out"""
    def __init__(self, task_id: str, timeout_seconds: int):
        super().__init__(
            message=f"Task {task_id} timed out after {timeout_seconds} seconds",
            task_id=task_id,
            error_type="timeout"
        )
        self.timeout_seconds = timeout_seconds

class TaskCancelledError(TaskExecutionError):
    """Exception raised when task execution is cancelled"""
    def __init__(self, task_id: str, reason: str = None):
        super().__init__(
            message=f"Task {task_id} was cancelled" + (f": {reason}" if reason else ""),
            task_id=task_id,
            error_type="cancelled"
        )
        self.reason = reason

class ExecutionStats:
    """Statistics for task execution"""
    def __init__(self):
        self.task_count = 0
        self.successful_count = 0
        self.failed_count = 0
        self.timeout_count = 0
        self.cancelled_count = 0
        self.total_execution_time = 0.0
        self.min_execution_time = float('inf')
        self.max_execution_time = 0.0
        self.avg_execution_time = 0.0
        self.start_time = None
        self.end_time = None
    
    def record_start(self):
        """Record execution start time"""
        self.start_time = time.time()
    
    def record_end(self):
        """Record execution end time"""
        self.end_time = time.time()
    
    def record_task_execution(self, success: bool, execution_time: float, error_type: str = None):
        """Record statistics for a task execution"""
        self.task_count += 1
        self.total_execution_time += execution_time
        
        if execution_time < self.min_execution_time:
            self.min_execution_time = execution_time
        
        if execution_time > self.max_execution_time:
            self.max_execution_time = execution_time
        
        if success:
            self.successful_count += 1
        else:
            self.failed_count += 1
            if error_type == "timeout":
                self.timeout_count += 1
            elif error_type == "cancelled":
                self.cancelled_count += 1
        
        if self.task_count > 0:
            self.avg_execution_time = self.total_execution_time / self.task_count
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            "task_count": self.task_count,
            "successful_count": self.successful_count,
            "failed_count": self.failed_count,
            "timeout_count": self.timeout_count,
            "cancelled_count": self.cancelled_count,
            "total_execution_time": self.total_execution_time,
            "min_execution_time": self.min_execution_time if self.min_execution_time != float('inf') else 0,
            "max_execution_time": self.max_execution_time,
            "avg_execution_time": self.avg_execution_time,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_elapsed_time": (self.end_time - self.start_time) if self.end_time and self.start_time else None
        }
    
    def __str__(self) -> str:
        """String representation of stats"""
        if self.task_count == 0:
            return "No tasks executed"
        
        success_rate = (self.successful_count / self.task_count) * 100 if self.task_count > 0 else 0
        
        return (
            f"Tasks: {self.task_count} total, {self.successful_count} successful ({success_rate:.1f}%), "
            f"{self.failed_count} failed, {self.timeout_count} timeout, {self.cancelled_count} cancelled\n"
            f"Execution time: {self.avg_execution_time:.2f}s avg, {self.min_execution_time:.2f}s min, "
            f"{self.max_execution_time:.2f}s max, {self.total_execution_time:.2f}s total\n"
            f"Wall clock time: {(self.end_time - self.start_time):.2f}s"
        )

class Task:
    """Representation of a task to be executed"""
    def __init__(self, 
                task_id: str,
                task_type: str,
                function: Callable,
                args: tuple = None,
                kwargs: dict = None,
                max_retries: int = 0,
                timeout_seconds: int = None,
                metadata: Dict[str, Any] = None):
        """
        Initialize a task.
        
        Args:
            task_id: Unique identifier for the task
            task_type: Type of task (e.g., "test_generation")
            function: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            max_retries: Maximum number of retries if task fails
            timeout_seconds: Maximum execution time in seconds
            metadata: Additional metadata for the task
        """
        self.task_id = task_id
        self.task_type = task_type
        self.function = function
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.metadata = metadata or {}
        
        self.result = None
        self.error = None
        self.retry_count = 0
        self.start_time = None
        self.end_time = None
        self.execution_time = None
        self.status = "pending"  # pending, running, completed, failed, cancelled
    
    def execute(self) -> Any:
        """Execute the task function"""
        self.start_time = time.time()
        self.status = "running"
        
        try:
            self.result = self.function(*self.args, **self.kwargs)
            self.status = "completed"
        except Exception as e:
            self.error = e
            self.status = "failed"
        finally:
            self.end_time = time.time()
            self.execution_time = self.end_time - self.start_time
        
        return self.result
    
    def can_retry(self) -> bool:
        """Check if the task can be retried"""
        return self.status == "failed" and self.retry_count < self.max_retries
    
    def reset(self):
        """Reset the task for retry"""
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.execution_time = None
        self.status = "pending"
        self.retry_count += 1
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
            "retry_count": self.retry_count,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "execution_time": self.execution_time,
            "status": self.status,
            "has_error": self.error is not None,
            "error_type": type(self.error).__name__ if self.error else None,
            "error_message": str(self.error) if self.error else None
        }

class _TaskWrapper:
    """Wrapper for executing a task in a subprocess with timeout"""
    @staticmethod
    def run_task(task: Task, result_queue: multiprocessing.Queue, log_queue: multiprocessing.Queue = None):
        """
        Execute a task and put the result in the queue.
        
        Args:
            task: Task to execute
            result_queue: Queue to put the result in
            log_queue: Queue to put logs in
        """
        try:
            # Log task start
            if log_queue:
                log_queue.put({
                    "level": "info",
                    "message": f"Starting task {task.task_id} ({task.task_type})",
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Execute the task
            result = task.execute()
            
            # Log task completion
            if log_queue:
                log_queue.put({
                    "level": "info",
                    "message": f"Completed task {task.task_id} in {task.execution_time:.2f}s",
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "status": "completed",
                    "execution_time": task.execution_time,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Put the result in the queue
            result_queue.put({
                "task_id": task.task_id,
                "status": "completed",
                "result": result,
                "execution_time": task.execution_time
            })
        except Exception as e:
            # Log task error
            if log_queue:
                log_queue.put({
                    "level": "error",
                    "message": f"Task {task.task_id} failed: {str(e)}",
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "status": "failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Put the error in the queue
            result_queue.put({
                "task_id": task.task_id,
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_time": time.time() - task.start_time if task.start_time else 0
            })

class CursorExecutor:
    """
    Executor for running tasks in parallel with isolation.
    
    Features:
    - Execute tasks in isolated processes
    - Support for parallel execution
    - Task lifecycle management
    - Result collection and error handling
    - Support for timeout and cancellation
    """
    
    def __init__(self, 
                max_workers: int = None,
                use_processes: bool = True,
                log_file_path: str = None,
                structured_logger: StructuredLogger = None):
        """
        Initialize the executor.
        
        Args:
            max_workers: Maximum number of worker processes/threads
            use_processes: Use processes instead of threads for isolation
            log_file_path: Path to write logs to
            structured_logger: Optional structured logger to use
        """
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.use_processes = use_processes
        self.log_file_path = log_file_path
        self.structured_logger = structured_logger or StructuredLogger(
            log_file_path=log_file_path or "cursor_executor.jsonl",
            app_name="cursor_executor"
        )
        
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, Tuple[multiprocessing.Process, multiprocessing.Queue, datetime]] = {}
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, Exception] = {}
        self.stats = ExecutionStats()
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Setup multiprocessing context
        self.mp_context = multiprocessing.get_context('spawn')
        
        self.structured_logger.info(
            f"CursorExecutor initialized with {self.max_workers} workers "
            f"and {'process' if self.use_processes else 'thread'} isolation"
        )
    
    def create_task(self, 
                   function: Callable, 
                   args: tuple = None, 
                   kwargs: dict = None,
                   task_type: str = "generic",
                   task_id: str = None,
                   max_retries: int = 0,
                   timeout_seconds: int = None,
                   metadata: Dict[str, Any] = None) -> str:
        """
        Create a new task.
        
        Args:
            function: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            task_type: Type of task
            task_id: Optional task ID (generated if not provided)
            max_retries: Maximum number of retries if task fails
            timeout_seconds: Maximum execution time in seconds
            metadata: Additional metadata for the task
            
        Returns:
            Task ID
        """
        task_id = task_id or str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            function=function,
            args=args,
            kwargs=kwargs,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            metadata=metadata
        )
        
        with self._lock:
            self.tasks[task_id] = task
        
        self.structured_logger.task_started(
            task_id=task_id,
            task_type=task_type,
            priority=metadata.get("priority", "medium") if metadata else "medium"
        )
        
        return task_id
    
    def execute_task(self, task_id: str) -> Any:
        """
        Execute a single task and return the result.
        
        Args:
            task_id: ID of the task to execute
            
        Returns:
            Task result
            
        Raises:
            TaskExecutionError: If task execution fails
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
        
        # Start task execution timer
        start_time = time.time()
        
        # Create result queue
        result_queue = self.mp_context.Queue()
        
        # Execute the task
        success = False
        error_type = None
        
        try:
            if self.use_processes:
                self._execute_task_in_process(task, result_queue)
            else:
                self._execute_task_in_thread(task, result_queue)
            
            # Wait for task to complete
            result = self._wait_for_task_result(task, result_queue)
            
            # Set task result
            self.results[task_id] = result
            success = True
            
            # Return the result
            return result
        except TaskTimeoutError as e:
            # Handle timeout
            self.errors[task_id] = e
            error_type = "timeout"
            raise
        except TaskCancelledError as e:
            # Handle cancellation
            self.errors[task_id] = e
            error_type = "cancelled"
            raise
        except Exception as e:
            # Handle other errors
            self.errors[task_id] = e
            error_type = "error"
            raise TaskExecutionError(
                message=f"Task {task_id} failed: {str(e)}",
                task_id=task_id,
                error_type="execution_error",
                details=e
            )
        finally:
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Update statistics
            self.stats.record_task_execution(success, execution_time, error_type)
            
            # Log task completion or failure
            if success:
                self.structured_logger.task_completed(
                    task_id=task_id,
                    success=True,
                    duration_ms=execution_time * 1000
                )
            else:
                self.structured_logger.task_failed(
                    task_id=task_id,
                    error=str(self.errors.get(task_id, "Unknown error")),
                    error_type=error_type,
                    duration_ms=execution_time * 1000
                )
    
    def execute_tasks(self, task_ids: List[str] = None, timeout_seconds: int = None) -> Dict[str, Any]:
        """
        Execute multiple tasks in parallel and return results.
        
        Args:
            task_ids: List of task IDs to execute (all tasks if None)
            timeout_seconds: Maximum execution time for all tasks
            
        Returns:
            Dictionary mapping task IDs to results
        """
        with self._lock:
            if task_ids is None:
                task_ids = list(self.tasks.keys())
            
            # Filter out tasks that don't exist
            task_ids = [task_id for task_id in task_ids if task_id in self.tasks]
            
            if not task_ids:
                return {}
        
        # Record start time
        self.stats.record_start()
        
        # Execute tasks in parallel
        results = {}
        errors = {}
        
        executor_cls = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        with executor_cls(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task_id = {
                executor.submit(self.execute_task, task_id): task_id
                for task_id in task_ids
            }
            
            # Calculate completion deadline
            deadline = time.time() + timeout_seconds if timeout_seconds else None
            
            # Wait for tasks to complete
            for future in as_completed(future_to_task_id, timeout=timeout_seconds):
                task_id = future_to_task_id[future]
                
                try:
                    # Get the result
                    result = future.result()
                    results[task_id] = result
                except Exception as e:
                    # Store the error
                    errors[task_id] = e
                
                # Check if we've reached the deadline
                if deadline and time.time() >= deadline:
                    break
        
        # Record end time
        self.stats.record_end()
        
        # Return results and update instance variables
        with self._lock:
            self.results.update(results)
            self.errors.update(errors)
            return results
    
    def get_task_result(self, task_id: str) -> Any:
        """
        Get the result of a completed task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Task result
            
        Raises:
            KeyError: If task does not exist
            ValueError: If task has not completed
        """
        with self._lock:
            if task_id not in self.tasks:
                raise KeyError(f"Task {task_id} not found")
            
            if task_id not in self.results and task_id not in self.errors:
                raise ValueError(f"Task {task_id} has not completed")
            
            if task_id in self.errors:
                raise self.errors[task_id]
            
            return self.results[task_id]
    
    def wait_for_task(self, task_id: str, timeout_seconds: int = None) -> Any:
        """
        Wait for a task to complete and return the result.
        
        Args:
            task_id: ID of the task
            timeout_seconds: Maximum time to wait
            
        Returns:
            Task result
            
        Raises:
            KeyError: If task does not exist
            TimeoutError: If task does not complete within timeout
        """
        with self._lock:
            if task_id not in self.tasks:
                raise KeyError(f"Task {task_id} not found")
            
            if task_id in self.results:
                return self.results[task_id]
            
            if task_id in self.errors:
                raise self.errors[task_id]
            
            if task_id not in self.running_tasks:
                # Task has not been started, execute it
                return self.execute_task(task_id)
        
        # Wait for task to complete
        start_time = time.time()
        while True:
            with self._lock:
                if task_id in self.results:
                    return self.results[task_id]
                
                if task_id in self.errors:
                    raise self.errors[task_id]
                
                if task_id not in self.running_tasks:
                    # Task has completed but result not set
                    break
            
            # Check if we've reached the timeout
            if timeout_seconds and time.time() - start_time >= timeout_seconds:
                raise TimeoutError(f"Timed out waiting for task {task_id}")
            
            # Sleep briefly to avoid busy waiting
            time.sleep(0.1)
        
        # Should not reach here
        raise RuntimeError(f"Task {task_id} is in an inconsistent state")
    
    def cancel_task(self, task_id: str, reason: str = None) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: ID of the task
            reason: Reason for cancellation
            
        Returns:
            True if task was cancelled, False if it was not running
        """
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            if task_id not in self.running_tasks:
                return False
            
            # Get the process and queue
            process, result_queue, _ = self.running_tasks[task_id]
            
            # Terminate the process
            if process.is_alive():
                process.terminate()
                
                # Wait for process to terminate
                process.join(timeout=5)
                
                # Force kill if still alive
                if process.is_alive():
                    os.kill(process.pid, signal.SIGKILL)
            
            # Remove from running tasks
            del self.running_tasks[task_id]
            
            # Set error
            self.errors[task_id] = TaskCancelledError(task_id, reason)
            
            # Update task status
            self.tasks[task_id].status = "cancelled"
            
            # Log cancellation
            self.structured_logger.task_failed(
                task_id=task_id,
                error=f"Task cancelled: {reason}" if reason else "Task cancelled",
                error_type="cancelled"
            )
            
            return True
    
    def cancel_all_tasks(self, reason: str = None) -> int:
        """
        Cancel all running tasks.
        
        Args:
            reason: Reason for cancellation
            
        Returns:
            Number of tasks cancelled
        """
        with self._lock:
            running_task_ids = list(self.running_tasks.keys())
        
        # Cancel each task
        cancelled_count = 0
        for task_id in running_task_ids:
            if self.cancel_task(task_id, reason):
                cancelled_count += 1
        
        return cancelled_count
    
    def _execute_task_in_process(self, task: Task, result_queue: multiprocessing.Queue):
        """
        Execute a task in a separate process.
        
        Args:
            task: Task to execute
            result_queue: Queue to put the result in
        """
        # Create a process for the task
        process = self.mp_context.Process(
            target=_TaskWrapper.run_task,
            args=(task, result_queue)
        )
        
        # Start the process
        process.start()
        
        # Store the running task
        with self._lock:
            self.running_tasks[task.task_id] = (
                process, result_queue, datetime.now() + timedelta(seconds=task.timeout_seconds)
                if task.timeout_seconds else None
            )
    
    def _execute_task_in_thread(self, task: Task, result_queue: multiprocessing.Queue):
        """
        Execute a task in a separate thread.
        
        Args:
            task: Task to execute
            result_queue: Queue to put the result in
        """
        # Create a thread for the task
        thread = threading.Thread(
            target=_TaskWrapper.run_task,
            args=(task, result_queue)
        )
        
        # Start the thread
        thread.start()
        
        # Store the running task
        with self._lock:
            self.running_tasks[task.task_id] = (
                thread, result_queue, datetime.now() + timedelta(seconds=task.timeout_seconds)
                if task.timeout_seconds else None
            )
    
    def _wait_for_task_result(self, task: Task, result_queue: multiprocessing.Queue) -> Any:
        """
        Wait for a task to complete and return the result.
        
        Args:
            task: Task to wait for
            result_queue: Queue to get the result from
            
        Returns:
            Task result
            
        Raises:
            TaskTimeoutError: If task times out
            TaskExecutionError: If task fails
        """
        # Calculate timeout
        timeout = task.timeout_seconds
        
        try:
            # Wait for result
            result_data = result_queue.get(timeout=timeout)
            
            # Remove from running tasks
            with self._lock:
                if task.task_id in self.running_tasks:
                    del self.running_tasks[task.task_id]
            
            # Check for errors
            if result_data.get("status") == "failed":
                error_message = result_data.get("error", "Unknown error")
                error_type = result_data.get("error_type", "Unknown")
                
                # Update task status
                task.status = "failed"
                task.error = Exception(error_message)
                
                raise TaskExecutionError(
                    message=error_message,
                    task_id=task.task_id,
                    error_type=error_type
                )
            
            # Update task status
            task.status = "completed"
            task.result = result_data.get("result")
            
            return task.result
        except Empty:
            # Task timed out
            # Remove from running tasks
            with self._lock:
                if task.task_id in self.running_tasks:
                    process, _, _ = self.running_tasks[task.task_id]
                    
                    # Terminate the process
                    if hasattr(process, 'terminate') and callable(process.terminate):
                        process.terminate()
                    
                    del self.running_tasks[task.task_id]
            
            # Update task status
            task.status = "failed"
            task.error = TaskTimeoutError(task.task_id, timeout)
            
            raise TaskTimeoutError(task.task_id, timeout)
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Task status dictionary
            
        Raises:
            KeyError: If task does not exist
        """
        with self._lock:
            if task_id not in self.tasks:
                raise KeyError(f"Task {task_id} not found")
            
            task = self.tasks[task_id]
            
            return {
                "task_id": task_id,
                "status": task.status,
                "retries": task.retry_count,
                "execution_time": task.execution_time,
                "has_result": task_id in self.results,
                "has_error": task_id in self.errors
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self.stats.as_dict()
    
    def reset_stats(self):
        """Reset execution statistics"""
        self.stats = ExecutionStats()
    
    def cleanup(self):
        """Clean up resources"""
        # Cancel all running tasks
        self.cancel_all_tasks("Executor cleanup")
        
        # Clear results and errors
        with self._lock:
            self.results.clear()
            self.errors.clear()
            self.tasks.clear()
            self.running_tasks.clear()
    
    def __enter__(self):
        """Context manager enter"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
        return False  # Don't suppress exceptions 
