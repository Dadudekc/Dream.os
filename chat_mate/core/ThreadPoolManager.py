import threading
import logging
import queue
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError
from typing import Any, Dict, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum, auto

from core.UnifiedLoggingAgent import UnifiedLoggingAgent
from core.ConfigManager import ConfigManager

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """Task priority levels for the thread pool."""
    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    BACKGROUND = auto()

@dataclass
class Task:
    """Represents a task to be executed by the thread pool."""
    id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    timeout: Optional[float]
    retries: int
    created_at: datetime
    future: Optional[Future] = None
    completed_at: Optional[datetime] = None
    error: Optional[Exception] = None

class ThreadPoolManager:
    """
    Enhanced thread pool manager with priority queuing and task management.
    Features:
    - Priority-based task scheduling
    - Task timeout management
    - Automatic retries with exponential backoff
    - Resource monitoring
    - Task statistics and metrics
    """

    def __init__(self, max_workers: int = 5, task_timeout: float = 300, config=None):
        """
        Initialize the ThreadPoolManager.
        
        Args:
            max_workers: Maximum number of worker threads
            task_timeout: Default timeout for tasks in seconds
            config: Optional ConfigManager instance. If not provided, a new one will be created.
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.default_timeout = task_timeout
        
        # Initialize config manager if not provided
        self.config = config or ConfigManager()
        
        # Initialize logger with config manager
        self.logger = UnifiedLoggingAgent(self.config)
        
        # Task management
        self.tasks: Dict[str, Task] = {}
        self.priority_queues: Dict[TaskPriority, queue.PriorityQueue] = {
            priority: queue.PriorityQueue() for priority in TaskPriority
        }
        
        # Thread synchronization
        self._lock = threading.Lock()
        self._shutdown = threading.Event()
        
        # Metrics
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0.0,
            "avg_execution_time": 0.0
        }
        
        # Start scheduler thread
        self._scheduler_thread = threading.Thread(target=self._task_scheduler, daemon=True)
        self._scheduler_thread.start()

    def submit_task(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        timeout: Optional[float] = None,
        retries: int = 3,
        **kwargs
    ) -> Future:
        """
        Submit a task for execution.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            task_id: Optional unique identifier for the task
            priority: Task priority level
            timeout: Optional timeout in seconds
            retries: Number of retry attempts
            **kwargs: Keyword arguments for the function
            
        Returns:
            Future object representing the task
        """
        task_id = task_id or f"task_{len(self.tasks)}_{datetime.now().timestamp()}"
        timeout = timeout or self.default_timeout
        
        task = Task(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            retries=retries,
            created_at=datetime.now()
        )
        
        with self._lock:
            self.tasks[task_id] = task
            self.priority_queues[priority].put((priority.value, task))
            
        self.logger.log_system_event(
            event_type="task_submitted",
            message=f"Task {task_id} submitted with priority {priority.name}",
            metadata={
                "task_id": task_id,
                "priority": priority.name,
                "timeout": timeout,
                "retries": retries
            }
        )
        
        return task.future

    def _task_scheduler(self) -> None:
        """Background thread that schedules tasks based on priority."""
        while not self._shutdown.is_set():
            try:
                # Check each priority queue in order
                for priority in TaskPriority:
                    queue = self.priority_queues[priority]
                    while not queue.empty():
                        _, task = queue.get_nowait()
                        
                        if task.id not in self.tasks:
                            continue  # Task was cancelled
                            
                        self._execute_task(task)
                        
                # Small sleep to prevent busy waiting
                self._shutdown.wait(timeout=0.1)
                
            except Exception as e:
                self.logger.log_system_event(
                    event_type="scheduler_error",
                    message=f"Error in task scheduler: {str(e)}",
                    level="error"
                )

    def _execute_task(self, task: Task) -> None:
        """Execute a task with retry logic and timeout."""
        def wrapped_func():
            start_time = datetime.now()
            remaining_retries = task.retries
            
            while remaining_retries >= 0:
                try:
                    result = task.func(*task.args, **task.kwargs)
                    
                    execution_time = (datetime.now() - start_time).total_seconds()
                    with self._lock:
                        self.metrics["tasks_completed"] += 1
                        self.metrics["total_execution_time"] += execution_time
                        self.metrics["avg_execution_time"] = (
                            self.metrics["total_execution_time"] / 
                            self.metrics["tasks_completed"]
                        )
                    
                    task.completed_at = datetime.now()
                    return result
                    
                except Exception as e:
                    remaining_retries -= 1
                    if remaining_retries < 0:
                        task.error = e
                        with self._lock:
                            self.metrics["tasks_failed"] += 1
                        raise
                    
                    # Exponential backoff
                    retry_delay = 2 ** (task.retries - remaining_retries)
                    self.logger.log_system_event(
                        event_type="task_retry",
                        message=f"Retrying task {task.id} after {retry_delay}s",
                        metadata={
                            "task_id": task.id,
                            "remaining_retries": remaining_retries,
                            "delay": retry_delay
                        }
                    )
                    self._shutdown.wait(timeout=retry_delay)

        # Submit to thread pool
        task.future = self.executor.submit(wrapped_func)
        
        # Add timeout if specified
        if task.timeout:
            try:
                task.future.result(timeout=task.timeout)
            except TimeoutError:
                task.error = TimeoutError(f"Task {task.id} timed out after {task.timeout}s")
                self.logger.log_system_event(
                    event_type="task_timeout",
                    message=f"Task {task.id} timed out",
                    level="error",
                    metadata={"task_id": task.id, "timeout": task.timeout}
                )

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending or running task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if task was cancelled successfully
        """
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.future and not task.future.done():
                    cancelled = task.future.cancel()
                    if cancelled:
                        del self.tasks[task_id]
                        self.logger.log_system_event(
                            event_type="task_cancelled",
                            message=f"Task {task_id} cancelled",
                            metadata={"task_id": task_id}
                        )
                    return cancelled
        return False

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the current status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary containing task status information
        """
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                return {
                    "id": task.id,
                    "status": "completed" if task.completed_at else "running",
                    "priority": task.priority.name,
                    "created_at": task.created_at.isoformat(),
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "error": str(task.error) if task.error else None
                }
        return {"error": "Task not found"}

    def get_metrics(self) -> Dict[str, Any]:
        """Get current thread pool metrics."""
        with self._lock:
            return {
                **self.metrics,
                "active_tasks": len(self.tasks),
                "queue_sizes": {
                    priority.name: queue.qsize()
                    for priority, queue in self.priority_queues.items()
                }
            }

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the thread pool manager.
        
        Args:
            wait: If True, wait for all tasks to complete
        """
        self._shutdown.set()
        self.executor.shutdown(wait=wait)
        self.logger.log_system_event(
            event_type="threadpool_shutdown",
            message="ThreadPoolManager shutdown complete",
            metadata=self.get_metrics()
        ) 