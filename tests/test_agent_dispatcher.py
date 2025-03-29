import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from core.AgentDispatcher import AgentDispatcher, Task, TaskPriority, TaskStatus

# -------------------------
# FIXTURES
# -------------------------

@pytest.fixture
def dispatcher():
    with patch("core.AgentDispatcher.UnifiedLoggingAgent") as mock_logger, \
         patch("core.AgentDispatcher.UnifiedFeedbackMemory") as mock_feedback, \
         patch("core.AgentDispatcher.config") as mock_config:

        # Mock the config values
        mock_config.get.side_effect = lambda key, default=None: {
            "dispatcher.max_workers": 1,
            "dispatcher.batch_size": 5,
            "dispatcher.min_batch_interval": 1.0,
            "dispatcher.resource_limits": {},
            "dispatcher.priority_weights": {
                "CRITICAL": 0,
                "HIGH": 1,
                "MEDIUM": 2,
                "LOW": 3,
                "BACKGROUND": 4
            }
        }.get(key, default)

        # Instantiate dispatcher (starts worker thread automatically)
        disp = AgentDispatcher()

        # Stop the thread immediately to isolate tests from workers
        disp.shutdown()

        return disp

@pytest.fixture
def dummy_task():
    return Task(
        id="test_agent_type_test_task_type_20250321_120000_000000",
        agent_type="chat",
        task_type="test_task_type",
        payload={"data": "test"},
        priority=TaskPriority.MEDIUM,
        dependencies=[],
        created_at=datetime.now(),
        metadata={}
    )

# -------------------------
# TEST CASES
# -------------------------

def test_dispatcher_initialization(dispatcher):
    assert dispatcher.config["max_workers"] == 1
    assert dispatcher.performance_metrics["total_tasks"] == 0
    assert len(dispatcher.worker_threads) == 1  # 1 worker thread started

def test_add_task_to_queue(dispatcher):
    task_id = dispatcher.add_task(
        agent_type="chat",
        task_type="test_task_type",
        payload={"message": "Hello World"},
        priority=TaskPriority.CRITICAL
    )

    assert task_id.startswith("chat_test_task_type_")
    queue = dispatcher.task_queues[TaskPriority.CRITICAL]
    assert not queue.empty()

def test_get_next_task_ready(dispatcher, dummy_task):
    # Place task directly into queue
    dispatcher.task_queues[TaskPriority.MEDIUM].put(
        (dispatcher.config["priority_weights"]["MEDIUM"], dummy_task)
    )

    # Should return the task (dependencies are resolved, no scheduling delay)
    next_task = dispatcher._get_next_task()

    assert next_task is not None
    assert next_task.id == dummy_task.id

def test_get_next_task_blocked_dependency(dispatcher, dummy_task):
    dummy_task.dependencies = ["missing_task"]
    
    dispatcher.task_queues[TaskPriority.MEDIUM].put(
        (dispatcher.config["priority_weights"]["MEDIUM"], dummy_task)
    )

    next_task = dispatcher._get_next_task()

    # Should return None because dependency is unresolved
    assert next_task is None

def test_can_execute_task_dependency_check(dispatcher, dummy_task):
    dummy_task.dependencies = ["missing_task"]

    assert dispatcher._can_execute_task(dummy_task) is False

    # Complete the dependency
    dispatcher.completed_tasks["missing_task"] = dummy_task
    dummy_task.dependencies = ["missing_task"]

    assert dispatcher._can_execute_task(dummy_task) is True

def test_can_execute_task_scheduled_time(dispatcher, dummy_task):
    dummy_task.scheduled_for = datetime.now() + timedelta(seconds=5)

    assert dispatcher._can_execute_task(dummy_task) is False

def test_execute_task_success(dispatcher, dummy_task):
    dispatcher._dispatch_to_agent = MagicMock(return_value={"result": "ok"})
    dispatcher._allocate_resources = MagicMock()
    dispatcher._release_resources = MagicMock()

    dispatcher._execute_task(dummy_task)

    # Task completed successfully
    assert dummy_task.status == TaskStatus.COMPLETED
    assert dummy_task.execution_time is not None
    assert dummy_task.id in dispatcher.completed_tasks

def test_execute_task_retry(dispatcher, dummy_task):
    dispatcher._dispatch_to_agent = MagicMock(side_effect=Exception("Execution Failed"))
    dispatcher._allocate_resources = MagicMock()
    dispatcher._release_resources = MagicMock()

    dummy_task.max_retries = 2

    dispatcher._execute_task(dummy_task)

    # Task retried once (still in queue, RETRYING status)
    assert dummy_task.status in [TaskStatus.RETRYING, TaskStatus.FAILED]

def test_retry_task(dispatcher, dummy_task):
    dummy_task.retries = 1
    dispatcher._retry_task(dummy_task)

    queue = dispatcher.task_queues[dummy_task.priority]
    assert not queue.empty()

def test_allocate_and_release_resources(dispatcher, dummy_task):
    dummy_task.metadata["required_resources"] = {"cpu": 2}

    dispatcher._allocate_resources(dummy_task)
    assert dispatcher.resource_usage["cpu"] == 2

    dispatcher._release_resources(dummy_task)
    assert dispatcher.resource_usage["cpu"] == 0

def test_cancel_task(dispatcher, dummy_task):
    # Add to active tasks and cancel
    dummy_task.status = TaskStatus.PENDING
    dispatcher.active_tasks[dummy_task.id] = dummy_task

    result = dispatcher.cancel_task(dummy_task.id)

    assert result is True
    assert dummy_task.status == TaskStatus.CANCELLED
    assert dummy_task.id in dispatcher.completed_tasks

def test_cancel_task_failure(dispatcher, dummy_task):
    # Only COMPLETED task
    dummy_task.status = TaskStatus.COMPLETED
    dispatcher.completed_tasks[dummy_task.id] = dummy_task

    result = dispatcher.cancel_task(dummy_task.id)
    assert result is False

def test_get_task_status(dispatcher, dummy_task):
    dispatcher.completed_tasks[dummy_task.id] = dummy_task

    result = dispatcher.get_task_status(dummy_task.id)

    assert result == dummy_task

def test_update_performance_metrics(dispatcher, dummy_task):
    dummy_task.execution_time = 2.0
    dispatcher.performance_metrics["total_tasks"] = 1

    dispatcher._update_performance_metrics(dummy_task, success=True)

    assert dispatcher.performance_metrics["successful_tasks"] == 1
    assert dispatcher.performance_metrics["avg_execution_time"] > 0

def test_shutdown(dispatcher):
    dispatcher.shutdown()

    assert dispatcher.stop_event.is_set()

def test_context_manager(dispatcher):
    with patch("core.AgentDispatcher.AgentDispatcher.shutdown") as mock_shutdown:
        with dispatcher as disp:
            assert isinstance(disp, AgentDispatcher)
        mock_shutdown.assert_called_once()