#!/usr/bin/env python3
"""
Task Queue System Demo
=====================

This demo script shows how all components of the new task queue system work together.
It demonstrates:

1. Creating and managing tasks with PriorityTaskQueue
2. Validating tasks with TaskSchema
3. Executing tasks in parallel with CursorExecutor
4. Logging structured data with StructuredLogger
5. Using lifecycle hooks for task customization
"""

import os
import sys
import time
import json
import random
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import our components
from core.task_queue_manager import PriorityTaskQueue
from core.task_schema import (
    TaskType, Priority, create_task, create_code_generation_task,
    create_test_generation_task, create_refactoring_task
)
from core.cursor_executor import CursorExecutor
from core.structured_logger import StructuredLogger
from core.lifecycle_hooks_loader import LifecycleHooksLoader, HookType

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create hooks directory if it doesn't exist
hooks_dir = project_root / "hooks"
hooks_dir.mkdir(exist_ok=True)

# Create a demo hook module
def create_demo_hooks():
    """Create demo hook modules for testing"""
    hook_code = """#!/usr/bin/env python3
\"\"\"
Task Queue Demo Hooks
====================

Demo hook module for the task queue system.
\"\"\"

# Hook module metadata
HOOK_METADATA = {
    "name": "demo_hooks",
    "version": "0.1.0",
    "description": "Demo hooks for the task queue system",
    "author": "Cursor AI",
    "task_types": []  # Empty means all task types
}

def on_pre_task(task):
    \"\"\"
    Called before task execution. Return False to prevent execution.
    
    Args:
        task: The task to be executed
        
    Returns:
        True to allow execution, False to prevent it
    \"\"\"
    print(f"PRE_TASK hook: Task {task.get('task_id')} is about to be executed")
    return True

def on_post_task(task, result):
    \"\"\"
    Called after task execution with the task result.
    
    Args:
        task: The executed task
        result: The task result
    \"\"\"
    print(f"POST_TASK hook: Task {task.get('task_id')} has completed with result: {result}")

def on_task_error(task, error):
    \"\"\"
    Called when task execution fails with the error.
    
    Args:
        task: The failed task
        error: The error that occurred
    \"\"\"
    print(f"TASK_ERROR hook: Task {task.get('task_id')} failed with error: {error}")
"""
    with open(hooks_dir / "demo_hooks.py", "w") as f:
        f.write(hook_code)
    
    logger.info(f"Created demo hook module at {hooks_dir / 'demo_hooks.py'}")

# Example task functions
def example_task_success(task_id: str, sleep_time: float = 1.0) -> Dict[str, Any]:
    """Example task that succeeds after sleeping"""
    time.sleep(sleep_time)
    return {
        "task_id": task_id,
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "execution_time": sleep_time,
        "message": f"Task {task_id} completed successfully"
    }

def example_task_failure(task_id: str, sleep_time: float = 1.0) -> Dict[str, Any]:
    """Example task that fails after sleeping"""
    time.sleep(sleep_time)
    raise ValueError(f"Task {task_id} failed intentionally")

def example_task_long_running(task_id: str, iterations: int = 5) -> Dict[str, Any]:
    """Example task that runs for a long time with progress updates"""
    results = []
    for i in range(iterations):
        time.sleep(1.0)
        results.append({
            "iteration": i + 1,
            "timestamp": datetime.now().isoformat(),
            "progress": (i + 1) / iterations * 100
        })
    
    return {
        "task_id": task_id,
        "status": "success",
        "iterations": iterations,
        "iteration_results": results,
        "message": f"Task {task_id} completed all {iterations} iterations"
    }

def run_demo():
    """Run the task queue system demo"""
    
    print("=================================================================")
    print("              TASK QUEUE SYSTEM DEMO")
    print("=================================================================")
    print()
    
    # Create output directory
    output_dir = project_root / "demo_output"
    output_dir.mkdir(exist_ok=True)
    
    # 1. Initialize structured logger
    print("[1] Initializing StructuredLogger...")
    logger_path = output_dir / "demo_task_queue.jsonl"
    structured_logger = StructuredLogger(
        log_file_path=str(logger_path),
        app_name="task_queue_demo",
        console_logging=True
    )
    structured_logger.info("Demo started")
    print(f"    - Logs will be written to {logger_path}")
    print()
    
    # 2. Load lifecycle hooks
    print("[2] Initializing LifecycleHooksLoader...")
    create_demo_hooks()
    hooks_loader = LifecycleHooksLoader(hook_paths=[str(hooks_dir)])
    hooks_loader.load_hooks()
    
    hook_types = hooks_loader.get_hook_types()
    print(f"    - Loaded hooks for types: {', '.join(hook_types)}")
    print()
    
    # 3. Initialize task queue
    print("[3] Initializing PriorityTaskQueue...")
    queue_file = output_dir / "demo_task_queue.json"
    task_queue = PriorityTaskQueue(queue_file=str(queue_file))
    print(f"    - Task queue initialized with storage at {queue_file}")
    print()
    
    # 4. Create and validate tasks
    print("[4] Creating tasks with different priorities and types...")
    
    # Create some code generation tasks
    code_gen_task_ids = []
    for i in range(3):
        priority = random.choice([Priority.HIGH, Priority.MEDIUM, Priority.LOW])
        task = create_code_generation_task(
            description=f"Generate utility function #{i+1}",
            language="python",
            target_file=f"utils/utility_{i+1}.py",
            requirements=[f"Requirement {j+1}" for j in range(3)],
            priority=priority
        )
        task_id = task["task_id"]
        code_gen_task_ids.append(task_id)
        task_queue.put(task_id, task, priority=task["priority"])
        print(f"    - Added code generation task {task_id} with {task['priority']} priority")
    
    # Create some test generation tasks
    test_gen_task_ids = []
    for i in range(2):
        task = create_test_generation_task(
            description=f"Generate tests for module #{i+1}",
            source_file=f"modules/module_{i+1}.py",
            test_framework="pytest",
            coverage_target=85.0
        )
        task_id = task["task_id"]
        test_gen_task_ids.append(task_id)
        task_queue.put(task_id, task)
        print(f"    - Added test generation task {task_id}")
    
    # Create a refactoring task with dependencies
    refactoring_task = create_refactoring_task(
        description="Refactor utility functions",
        target_files=[f"utils/utility_{i+1}.py" for i in range(3)],
        refactoring_type="extract_common_functionality",
        dependencies=code_gen_task_ids  # Depends on code generation tasks
    )
    refactoring_task_id = refactoring_task["task_id"]
    task_queue.put(refactoring_task_id, refactoring_task)
    print(f"    - Added refactoring task {refactoring_task_id} with dependencies")
    
    # Print the full queue status
    print("\n    Current Queue Status:")
    queue_status = task_queue.get_queue_status()
    for priority, count in queue_status.items():
        print(f"    - {priority}: {count} tasks")
    print()
    
    # 5. Initialize task executor
    print("[5] Initializing CursorExecutor...")
    executor = CursorExecutor(
        max_workers=3,  # Limit to 3 concurrent tasks
        use_processes=True,  # Use process isolation
        structured_logger=structured_logger
    )
    print(f"    - Executor initialized with {executor.max_workers} workers")
    print()
    
    # 6. Execute some example tasks
    print("[6] Executing example tasks...")
    
    # Create a mix of tasks
    task_ids = []
    
    # Success task
    success_task_id = executor.create_task(
        function=example_task_success,
        args=(f"success-{random.randint(1000, 9999)}", 2.0),
        task_type="example",
        metadata={"category": "success", "priority": "high"}
    )
    task_ids.append(success_task_id)
    print(f"    - Created success task: {success_task_id}")
    
    # Failure task
    failure_task_id = executor.create_task(
        function=example_task_failure,
        args=(f"failure-{random.randint(1000, 9999)}", 1.0),
        task_type="example",
        max_retries=1,  # Allow one retry
        metadata={"category": "failure", "priority": "medium"}
    )
    task_ids.append(failure_task_id)
    print(f"    - Created failure task: {failure_task_id}")
    
    # Long-running task
    long_task_id = executor.create_task(
        function=example_task_long_running,
        args=(f"long-{random.randint(1000, 9999)}", 3),
        task_type="example",
        timeout_seconds=5,  # Should complete within 5 seconds
        metadata={"category": "long_running", "priority": "low"}
    )
    task_ids.append(long_task_id)
    print(f"    - Created long-running task: {long_task_id}")
    
    # Execute all tasks in parallel
    print("\n    Executing tasks in parallel...")
    try:
        results = executor.execute_tasks(task_ids)
        print(f"    - Successfully executed {len(results)} tasks")
    except Exception as e:
        print(f"    - Error executing tasks: {e}")
    
    # 7. Execute lifecycle hooks
    print("\n[7] Executing lifecycle hooks...")
    # Create a sample task for hook execution
    sample_task = create_task(
        task_type=TaskType.CODE_GENERATION,
        description="Sample task for hook execution"
    )
    
    # Execute pre-task hooks
    print("    - Executing PRE_TASK hooks...")
    pre_task_results = hooks_loader.execute_hook(HookType.PRE_TASK, task=sample_task)
    print(f"      Hook results: {pre_task_results}")
    
    # Execute post-task hooks
    print("    - Executing POST_TASK hooks...")
    sample_result = {"status": "success", "output": "Sample output"}
    hooks_loader.execute_hook(HookType.POST_TASK, task=sample_task, result=sample_result)
    
    # 8. View execution statistics
    print("\n[8] Task execution statistics:")
    stats = executor.get_stats()
    print(f"    - Total tasks: {stats['task_count']}")
    print(f"    - Successful: {stats['successful_count']}")
    print(f"    - Failed: {stats['failed_count']}")
    print(f"    - Average execution time: {stats['avg_execution_time']:.2f}s")
    
    # 9. Check task results
    print("\n[9] Task results:")
    for task_id in task_ids:
        try:
            status = executor.get_task_status(task_id)
            print(f"    - Task {task_id}: {status['status']}")
            if status['has_result']:
                try:
                    result = executor.get_task_result(task_id)
                    print(f"      Result: {result.get('message') if isinstance(result, dict) else result}")
                except Exception as e:
                    print(f"      Error: {str(e)}")
        except Exception as e:
            print(f"    - Error getting status for task {task_id}: {e}")
    
    # 10. Task queue operations
    print("\n[10] Task queue operations:")
    
    # Get highest priority task
    print("    - Getting highest priority task from queue...")
    task_id, task = task_queue.get()
    if task:
        print(f"      Got task {task_id} with priority {task['priority']}")
        
        # Mark it as completed
        print("    - Marking task as completed...")
        task_queue.task_completed(task_id)
        print(f"      Task {task_id} marked as completed")
    else:
        print("      No tasks in queue")
    
    # 11. Clean up
    print("\n[11] Cleaning up...")
    executor.cleanup()
    print("    - Executor resources cleaned up")
    
    structured_logger.info("Demo completed")
    print("\nDemo completed! Check the output files in the demo_output directory.")

if __name__ == "__main__":
    run_demo() 
