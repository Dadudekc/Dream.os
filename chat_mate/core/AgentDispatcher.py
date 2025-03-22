import threading
import queue
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum, auto
import asyncio
import json

from core.UnifiedLoggingAgent import UnifiedLoggingAgent
from core.UnifiedFeedbackMemory import UnifiedFeedbackMemory
from core.config import config
from core.PathManager import PathManager

class TaskPriority(Enum):
    """Task priority levels for intelligent dispatching."""
    CRITICAL = auto()    # Immediate execution required
    HIGH = auto()        # Execute as soon as possible
    MEDIUM = auto()      # Normal execution priority
    LOW = auto()         # Execute when resources available
    BACKGROUND = auto()  # Execute during low-load periods

class TaskStatus(Enum):
    """Possible states for a task in the system."""
    PENDING = auto()     # Awaiting execution
    RUNNING = auto()     # Currently executing
    COMPLETED = auto()   # Successfully completed
    FAILED = auto()      # Failed to execute
    RETRYING = auto()    # Being retried after failure
    CANCELLED = auto()   # Cancelled before completion
    BLOCKED = auto()     # Blocked by dependencies

@dataclass
class Task:
    """Represents a task in the system with metadata."""
    id: str
    agent_type: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority
    dependencies: List[str]
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    retries: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = None

class AgentDispatcher:
    """
    Enhanced Agent Dispatcher that orchestrates tasks across different engines
    with intelligent prioritization and task management.
    
    Features:
    - Priority-based task scheduling
    - Dependency resolution
    - Automatic retries with backoff
    - Resource management
    - Task batching and optimization
    - Real-time monitoring
    - Performance analytics
    """

    def __init__(self):
        """Initialize the dispatcher with necessary components."""
        self.logger = UnifiedLoggingAgent()
        self.feedback_memory = UnifiedFeedbackMemory()
        
        # Task management
        self.task_queues: Dict[TaskPriority, queue.PriorityQueue] = {
            priority: queue.PriorityQueue() for priority in TaskPriority
        }
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        
        # Thread management
        self.worker_threads: List[threading.Thread] = []
        self.stop_event = threading.Event()
        
        # Performance tracking
        self.performance_metrics: Dict[str, Any] = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "avg_execution_time": 0.0,
            "task_type_stats": {}
        }
        
        # Resource management
        self.resource_locks: Dict[str, threading.Lock] = {}
        self.resource_usage: Dict[str, float] = {}
        
        # Load configuration
        self._load_config()
        
        # Start worker threads
        self._start_workers()
        
        self.logger.log_system_event(
            event_type="dispatcher_init",
            message="Agent Dispatcher initialized",
            level="info"
        )

    def _load_config(self) -> None:
        """Load dispatcher configuration from the unified config."""
        self.config = {
            "max_workers": config.get("dispatcher.max_workers", 5),
            "batch_size": config.get("dispatcher.batch_size", 10),
            "min_batch_interval": config.get("dispatcher.min_batch_interval", 1.0),
            "resource_limits": config.get("dispatcher.resource_limits", {}),
            "priority_weights": config.get("dispatcher.priority_weights", {
                "CRITICAL": 0,
                "HIGH": 1,
                "MEDIUM": 2,
                "LOW": 3,
                "BACKGROUND": 4
            })
        }

    def add_task(
        self,
        agent_type: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: List[str] = None,
        scheduled_for: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new task to the dispatcher.
        
        Args:
            agent_type: Type of agent to execute the task
            task_type: Type of task to execute
            payload: Task data and parameters
            priority: Task priority level
            dependencies: List of task IDs that must complete first
            scheduled_for: Optional future execution time
            metadata: Additional task metadata
            
        Returns:
            str: Task ID
        """
        task_id = f"{agent_type}_{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        task = Task(
            id=task_id,
            agent_type=agent_type,
            task_type=task_type,
            payload=payload,
            priority=priority,
            dependencies=dependencies or [],
            created_at=datetime.now(),
            scheduled_for=scheduled_for,
            metadata=metadata or {}
        )
        
        # Add to appropriate priority queue
        self.task_queues[priority].put((
            self.config["priority_weights"][priority.name],
            task
        ))
        
        self.performance_metrics["total_tasks"] += 1
        
        self.logger.log_system_event(
            event_type="task_added",
            message=f"Task {task_id} added to queue",
            level="info",
            metadata={
                "task_type": task_type,
                "priority": priority.name,
                "agent_type": agent_type
            }
        )
        
        return task_id

    def _start_workers(self) -> None:
        """Start worker threads for task execution."""
        for _ in range(self.config["max_workers"]):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.worker_threads.append(worker)

    def _worker_loop(self) -> None:
        """Main worker loop for processing tasks."""
        while not self.stop_event.is_set():
            try:
                # Try to get tasks from queues in priority order
                task = self._get_next_task()
                if task:
                    self._execute_task(task)
                else:
                    # No tasks available, sleep briefly
                    self.stop_event.wait(0.1)
            except Exception as e:
                self.logger.log_system_event(
                    event_type="worker_error",
                    message=f"Worker error: {str(e)}",
                    level="error"
                )

    def _get_next_task(self) -> Optional[Task]:
        """Get the next task to execute based on priority and dependencies."""
        for priority in TaskPriority:
            queue = self.task_queues[priority]
            if not queue.empty():
                try:
                    _, task = queue.get_nowait()
                    
                    # Check if task is ready to execute
                    if not self._can_execute_task(task):
                        # Put back in queue if not ready
                        queue.put((
                            self.config["priority_weights"][priority.name],
                            task
                        ))
                        continue
                        
                    return task
                except queue.Empty:
                    continue
        return None

    def _can_execute_task(self, task: Task) -> bool:
        """
        Check if a task can be executed based on dependencies,
        scheduling, and resource availability.
        """
        # Check dependencies
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
                
        # Check scheduling
        if task.scheduled_for and datetime.now() < task.scheduled_for:
            return False
            
        # Check resource availability
        required_resources = task.metadata.get("required_resources", {})
        for resource, amount in required_resources.items():
            if self.resource_usage.get(resource, 0) + amount > \
               self.config["resource_limits"].get(resource, float("inf")):
                return False
                
        return True

    def _execute_task(self, task: Task) -> None:
        """Execute a task and handle its result."""
        start_time = datetime.now()
        task.status = TaskStatus.RUNNING
        self.active_tasks[task.id] = task
        
        try:
            # Allocate resources
            self._allocate_resources(task)
            
            # Execute the task
            result = self._dispatch_to_agent(task)
            
            # Record success
            task.status = TaskStatus.COMPLETED
            task.execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update performance metrics
            self._update_performance_metrics(task, success=True)
            
            # Record feedback
            self.feedback_memory.add_feedback(
                context=task.agent_type,
                input_prompt=json.dumps(task.payload),
                output=json.dumps(result),
                result="success",
                metadata=task.metadata
            )
            
        except Exception as e:
            task.last_error = str(e)
            
            if task.retries < task.max_retries:
                # Retry the task
                task.retries += 1
                task.status = TaskStatus.RETRYING
                self._retry_task(task)
            else:
                # Mark as failed
                task.status = TaskStatus.FAILED
                self._update_performance_metrics(task, success=False)
                
                self.logger.log_system_event(
                    event_type="task_failed",
                    message=f"Task {task.id} failed: {str(e)}",
                    level="error",
                    metadata={"task": task.__dict__}
                )
        
        finally:
            # Release resources
            self._release_resources(task)
            
            # Move to completed tasks
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                self.completed_tasks[task.id] = task
                del self.active_tasks[task.id]

    def _dispatch_to_agent(self, task: Task) -> Any:
        """Dispatch task to appropriate agent for execution."""
        agent_type = task.agent_type.lower()
        
        if agent_type == "social":
            return self._execute_social_task(task)
        elif agent_type == "chat":
            return self._execute_chat_task(task)
        elif agent_type == "reinforcement":
            return self._execute_reinforcement_task(task)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    def _execute_social_task(self, task: Task) -> Any:
        """Execute a social media related task."""
        from social.SocialMediaManager import SocialMediaManager
        manager = SocialMediaManager()
        return manager.execute_task(task.task_type, task.payload)

    def _execute_chat_task(self, task: Task) -> Any:
        """Execute a chat engine related task."""
        from core.PromptEngine import PromptEngine
        engine = PromptEngine()
        return engine.execute_prompt(
            prompt_type=task.task_type,
            chat_title=task.payload.get("chat_title", "Untitled"),
            context=task.payload.get("context"),
            metadata=task.metadata
        )

    def _execute_reinforcement_task(self, task: Task) -> Any:
        """Execute a reinforcement learning related task."""
        from core.ReinforcementEngine import ReinforcementEngine
        engine = ReinforcementEngine()
        return engine.process_task(task.task_type, task.payload)

    def _retry_task(self, task: Task) -> None:
        """Retry a failed task with exponential backoff."""
        retry_delay = min(300, 2 ** task.retries)  # Max 5 minutes
        scheduled_time = datetime.now() + timedelta(seconds=retry_delay)
        
        # Re-queue the task
        task.scheduled_for = scheduled_time
        self.task_queues[task.priority].put((
            self.config["priority_weights"][task.priority.name],
            task
        ))
        
        self.logger.log_system_event(
            event_type="task_retry",
            message=f"Task {task.id} scheduled for retry",
            level="info",
            metadata={
                "retry_count": task.retries,
                "retry_delay": retry_delay,
                "scheduled_time": scheduled_time.isoformat()
            }
        )

    def _allocate_resources(self, task: Task) -> None:
        """Allocate resources required by the task."""
        required_resources = task.metadata.get("required_resources", {})
        for resource, amount in required_resources.items():
            if resource not in self.resource_locks:
                self.resource_locks[resource] = threading.Lock()
                
            with self.resource_locks[resource]:
                current_usage = self.resource_usage.get(resource, 0)
                self.resource_usage[resource] = current_usage + amount

    def _release_resources(self, task: Task) -> None:
        """Release resources allocated to the task."""
        required_resources = task.metadata.get("required_resources", {})
        for resource, amount in required_resources.items():
            with self.resource_locks[resource]:
                current_usage = self.resource_usage.get(resource, 0)
                self.resource_usage[resource] = max(0, current_usage - amount)

    def _update_performance_metrics(self, task: Task, success: bool) -> None:
        """Update performance metrics after task execution."""
        with threading.Lock():
            if success:
                self.performance_metrics["successful_tasks"] += 1
            else:
                self.performance_metrics["failed_tasks"] += 1
                
            # Update average execution time
            if task.execution_time:
                current_avg = self.performance_metrics["avg_execution_time"]
                total_tasks = self.performance_metrics["total_tasks"]
                self.performance_metrics["avg_execution_time"] = \
                    (current_avg * (total_tasks - 1) + task.execution_time) / total_tasks
                
            # Update task type stats
            task_stats = self.performance_metrics["task_type_stats"]
            if task.task_type not in task_stats:
                task_stats[task.task_type] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_time": 0.0
                }
            
            stats = task_stats[task.task_type]
            stats["total"] += 1
            if success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
                
            if task.execution_time:
                stats["avg_time"] = \
                    (stats["avg_time"] * (stats["total"] - 1) + task.execution_time) / stats["total"]

    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get the current status of a task."""
        return self.active_tasks.get(task_id) or self.completed_tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        task = self.active_tasks.get(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.RETRYING]:
            task.status = TaskStatus.CANCELLED
            self.completed_tasks[task_id] = task
            del self.active_tasks[task_id]
            
            self.logger.log_system_event(
                event_type="task_cancelled",
                message=f"Task {task_id} cancelled",
                level="info"
            )
            return True
        return False

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.performance_metrics.copy()

    def shutdown(self) -> None:
        """Gracefully shutdown the dispatcher."""
        self.stop_event.set()
        
        # Wait for workers to finish
        for worker in self.worker_threads:
            worker.join(timeout=5.0)
            
        self.logger.log_system_event(
            event_type="dispatcher_shutdown",
            message="Agent Dispatcher shut down",
            level="info"
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown() 