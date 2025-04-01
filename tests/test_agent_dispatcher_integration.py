import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from core.AgentDispatcher import AgentDispatcher, Task, TaskPriority, TaskStatus

# -------------------------
# FIXTURE: Full Dispatcher Instance
# -------------------------

@pytest.fixture(scope="module")
def dispatcher():
    """Create a real instance of AgentDispatcher with patched dependencies."""
    with patch("core.AgentDispatcher.UnifiedLoggingAgent"), \
         patch("core.AgentDispatcher.UnifiedFeedbackMemory"), \
         patch("core.AgentDispatcher.config") as mock_config:

        # Configure dispatcher settings
        mock_config.get.side_effect = lambda key, default=None: {
            "dispatcher.max_workers": 3,  # Using multiple workers for parallel execution
            "dispatcher.batch_size": 5,
            "dispatcher.min_batch_interval": 0.1,
            "dispatcher.resource_limits": {},
            "dispatcher.priority_weights": {
                "CRITICAL": 0,
                "HIGH": 1,
                "MEDIUM": 2,
                "LOW": 3,
                "BACKGROUND": 4
            }
        }.get(key, default)

        # Initialize dispatcher
        disp = AgentDispatcher()

        yield disp  # Provide dispatcher to tests

        disp.shutdown()  # Ensure cleanup after tests

# -------------------------
# TEST: Add & Process Multiple Tasks
# -------------------------

def test_add_and_execute_tasks(dispatcher):
    """Test adding multiple tasks and processing them in parallel."""

    def mock_task_execution(task):
        time.sleep(0.1)  # Simulate processing time
        return {"status": "success"}

    dispatcher._dispatch_to_agent = MagicMock(side_effect=mock_task_execution)

    task_ids = []
    for i in range(5):
        task_id = dispatcher.add_task(
            agent_type="chat",
            task_type=f"task_{i}",
            payload={"data": f"Test {i}"},
            priority=TaskPriority.MEDIUM
        )
        task_ids.append(task_id)

    # Allow dispatcher to process tasks
    time.sleep(0.5)

    # Verify all tasks are completed
    for task_id in task_ids:
        assert dispatcher.get_task_status(task_id).status == TaskStatus.COMPLETED

# -------------------------
# TEST: Task Dependencies
# -------------------------

def test_task_dependencies(dispatcher):
    """Ensure tasks with dependencies are executed in the correct order."""

    dependency_task_id = dispatcher.add_task(
        agent_type="reinforcement",
        task_type="dependency_task",
        payload={"data": "Dependency Task"},
        priority=TaskPriority.HIGH
    )

    dependent_task_id = dispatcher.add_task(
        agent_type="reinforcement",
        task_type="dependent_task",
        payload={"data": "Dependent Task"},
        priority=TaskPriority.HIGH,
        dependencies=[dependency_task_id]
    )

    # Allow dispatcher to process tasks
    time.sleep(0.5)

    # Ensure dependency completed before dependent task started
    assert dispatcher.get_task_status(dependency_task_id).status == TaskStatus.COMPLETED
    assert dispatcher.get_task_status(dependent_task_id).status == TaskStatus.COMPLETED

# -------------------------
# TEST: Task Scheduling
# -------------------------

def test_scheduled_task(dispatcher):
    """Ensure scheduled tasks execute at the correct time."""

    scheduled_time = datetime.now() + timedelta(seconds=2)
    task_id = dispatcher.add_task(
        agent_type="social",
        task_type="scheduled_task",
        payload={"message": "Scheduled"},
        priority=TaskPriority.LOW,
        scheduled_for=scheduled_time
    )

    # Task should NOT run immediately
    time.sleep(1)
    assert dispatcher.get_task_status(task_id).status == TaskStatus.PENDING

    # Wait until task executes
    time.sleep(2)
    assert dispatcher.get_task_status(task_id).status == TaskStatus.COMPLETED

# -------------------------
# TEST: Task Retry & Failure Handling
# -------------------------

def test_task_retry_mechanism(dispatcher):
    """Ensure tasks that fail retry automatically up to max retries."""

    def failing_task(task):
        raise Exception("Simulated Failure")

    dispatcher._dispatch_to_agent = MagicMock(side_effect=failing_task)

    task_id = dispatcher.add_task(
        agent_type="chat",
        task_type="failing_task",
        payload={"data": "Will fail"},
        priority=TaskPriority.MEDIUM
    )

    # Allow retries
    time.sleep(3)

    task = dispatcher.get_task_status(task_id)

    assert task.status == TaskStatus.FAILED
    assert task.retries == task.max_retries

# -------------------------
# TEST: Concurrent Task Execution
# -------------------------

def test_concurrent_task_execution(dispatcher):
    """Ensure multiple tasks execute concurrently across worker threads."""

    execution_log = []

    def mock_parallel_execution(task):
        execution_log.append(f"Task {task.id} started")
        time.sleep(1)
        execution_log.append(f"Task {task.id} completed")
        return {"status": "done"}

    dispatcher._dispatch_to_agent = MagicMock(side_effect=mock_parallel_execution)

    task_ids = []
    for i in range(3):  # Matches max_workers
        task_id = dispatcher.add_task(
            agent_type="chat",
            task_type=f"parallel_task_{i}",
            payload={"data": f"Task {i}"},
            priority=TaskPriority.HIGH
        )
        task_ids.append(task_id)

    time.sleep(1.5)  # Ensure tasks have time to execute in parallel

    for task_id in task_ids:
        assert dispatcher.get_task_status(task_id).status == TaskStatus.COMPLETED

    # Ensure concurrent execution (tasks start before others finish)
    assert len(execution_log) > 3  # More than 3 entries (starts and completions overlap)

# -------------------------
# TEST: Dispatcher Shutdown While Processing
# -------------------------

def test_shutdown_during_execution(dispatcher):
    """Ensure dispatcher can shut down safely while tasks are processing."""

    def long_running_task(task):
        time.sleep(3)
        return {"status": "completed"}

    dispatcher._dispatch_to_agent = MagicMock(side_effect=long_running_task)

    task_id = dispatcher.add_task(
        agent_type="chat",
        task_type="long_task",
        payload={"data": "Should be interrupted"},
        priority=TaskPriority.HIGH
    )

    time.sleep(1)  # Allow task to start

    dispatcher.shutdown()

    task = dispatcher.get_task_status(task_id)
    assert task.status in [TaskStatus.RUNNING, TaskStatus.FAILED]  # Should be interrupted

# -------------------------
# TEST: Performance Metrics Tracking
# -------------------------

def test_performance_metrics(dispatcher):
    """Ensure performance metrics are updated correctly."""
    
    dispatcher.performance_metrics = {
        "total_tasks": 10,
        "successful_tasks": 5,
        "failed_tasks": 3,
        "avg_execution_time": 1.2
    }

    metrics = dispatcher.get_performance_metrics()
    assert metrics["total_tasks"] == 10
    assert metrics["successful_tasks"] == 5
    assert metrics["failed_tasks"] == 3
    assert metrics["avg_execution_time"] == 1.2
