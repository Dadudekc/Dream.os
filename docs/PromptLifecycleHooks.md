# Prompt Lifecycle Hooks

The Prompt Lifecycle Hooks system provides a structured, extensible framework for processing tasks as they move through their lifecycle from queue to execution. This document describes the system, its stages, and how to extend it with custom hooks.

## Overview

Tasks processed by the CursorSessionManager now go through five distinct lifecycle stages:

1. **Queue**: When a task is first added to the queue
2. **Inject**: When system context is injected before processing
3. **Validate**: Validation of task content/structure before execution 
4. **Approve**: Final approval check before dispatch
5. **Dispatch**: Just before execution

At each stage, registered hooks can:
- Validate the task (and reject it if invalid)
- Modify the task (e.g., normalize values, enrich with data)
- Log or monitor task processing

All modifications are tracked and can be displayed in the UI.

## Lifecycle Stages in Detail

### 1. Queue Stage

Called when `queue_task()` is first invoked. Hooks registered for this stage can:
- Sanitize inputs (e.g., trimming whitespace from prompts)
- Normalize priorities (e.g., mapping "highest" to "critical")
- Add default values for missing fields
- Log or monitor incoming tasks

### 2. Inject Stage 

Called during task acceptance before execution. Hooks can:
- Inject system context (current file, editor state, etc.)
- Add memory snapshots or relevant history
- Fetch content from target files
- Add environment variables or configuration

### 3. Validate Stage

Called after injection to validate the task. Hooks can:
- Check for required fields
- Validate field values
- Ensure prompt quality/format
- Perform security checks
- Reject invalid tasks

### 4. Approve Stage

Final approval before execution. Hooks can:
- Apply rate limiting
- Check permissions
- Apply policy rules
- Format the final prompt text

### 5. Dispatch Stage

Called just before execution. Hooks can:
- Log the final task state
- Create audit records
- Apply last-minute transformations
- Cancel based on system conditions

## Using the System

### Basic Usage with CursorSessionManager

The lifecycle hooks are automatically integrated into the `CursorSessionManager`. By default, it:

1. Applies basic validation at the validate stage 
2. Normalizes priorities at the queue stage
3. Sanitizes prompts at the queue stage

No action is required to benefit from these basic hooks.

### Adding Custom Hooks

To add custom hooks to the system:

```python
from core.services.PromptLifecycleHooksService import PromptLifecycleHooksService

# Create a custom hook function
def my_validation_hook(task):
    """Custom validation hook for tasks."""
    if "sensitive_operation" in task.get("prompt", "").lower():
        # Reject the task
        return None
    return task  # Accept the task

# Get the hooks service from manager
hooks_service = cursor_manager.lifecycle_hooks

# Register your hook
hooks_service.register_validate_hook(my_validation_hook)
```

### Creating Hooks

Hook functions take a single argument (the task dictionary) and return:
- The modified task dictionary if accepted
- None if rejected

```python
def example_hook(task):
    # Validate, modify, or reject the task
    if not task.get("source"):
        task["source"] = "auto"  # Add a default
    
    if task.get("priority") == "emergency":
        # Check for authorization
        if not is_authorized(task):
            return None  # Reject
    
    return task  # Accept with modifications
```

## UI Integration

The AIDE UI has been enhanced to display:
- Lifecycle stage indicators in the task list
- Detailed lifecycle timeline on task double-click
- Tooltips with lifecycle stage information

Tasks rejected by the hook system will be shown with appropriate error messages.

## Advanced Features

### Hook Statistics

The PromptLifecycleHooksService tracks statistics about hook executions:

```python
# Get statistics
stats = cursor_manager.lifecycle_hooks.get_stats()
print(f"Hooks run: {stats['queue_hooks_run']}")
print(f"Tasks rejected: {stats['tasks_rejected']}")
```

### Processing Tasks Through the Full Lifecycle

To manually process a task through all stages:

```python
from core.services.PromptLifecycleHooksService import PromptLifecycleHooksService

hooks = PromptLifecycleHooksService()
# ... register hooks ...

task = {"prompt": "Example task", "task_id": "123"}
processed_task, messages = hooks.process_lifecycle(task)

if processed_task:
    print(f"Task processed successfully: {messages}")
else:
    print(f"Task rejected: {messages}")
```

## Best Practices

1. **Order Matters**: Hooks are executed in registration order within each stage. 
2. **Keep Hooks Small**: Each hook should do one specific thing.
3. **Handle Exceptions**: Hooks should catch their own exceptions to avoid disrupting the chain.
4. **Don't Modify Critical Fields**: Avoid changing `task_id` or similar identity fields.
5. **Preserve Structure**: Don't remove required fields from the task.

## Extending the System

The system can be extended in several ways:

- Create domain-specific hooks (e.g., for TDD mode, refactoring)
- Add hooks that integrate with external services
- Implement metrics and monitoring hooks
- Add security and compliance hooks 