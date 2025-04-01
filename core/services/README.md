# Core Services

This directory contains service classes that provide core functionality for the prompt orchestration system.

## CursorUIService

The `CursorUIService` class provides modular UI interaction capabilities for automating Cursor interactions. It replaces the monolithic approach in the old `cursor_automation.py` script with a more maintainable, modular design.

### Key Features

- **Browser Interaction**: Start browser, locate and click UI elements
- **Screenshot Capabilities**: Take and save screenshots for debugging and validation
- **Keyboard Actions**: Type text, trigger hotkeys, and perform keyboard shortcuts
- **Clipboard Management**: Get and set clipboard content for reliable text handling
- **Task Execution**: Execute prompt tasks with full lifecycle management
- **Result Validation**: Validate task results against criteria with requeue support
- **Event-based Callbacks**: Trigger callbacks for various events during execution

### Factory Pattern

The `CursorUIServiceFactory` provides a clean interface for creating properly configured `CursorUIService` instances with dependency injection support.

## Backward Compatibility

The old `cursor_automation.py` script has been maintained as a backward compatibility layer that redirects all calls to the new modular implementation, with deprecation notices to guide users toward the new API.

## Integration with Orchestration System

The `CursorUIService` is designed to integrate with the orchestration system:

1. It can be used directly by the `PromptExecutionService` for task execution
2. It supports dependency injection via a service registry
3. It provides event callbacks for integration with task history and validation

## Usage Example

```python
from core.services.cursor_ui_service import CursorUIService, CursorUIServiceFactory

# Create service using factory
service = CursorUIServiceFactory.create(
    browser_path="/path/to/browser",
    debug_mode=True
)

# Execute a task
task = {
    "id": "task_123",
    "rendered_prompt": "Generate a Python class that..."
}
result = service.execute_task(task)

# Validate result
validation = service.validate_task_result(
    result,
    {"expected_content": ["class"], "min_length": 100}
)

print(f"Task execution: {result['status']}")
print(f"Validation passed: {validation['passed']}")
```

## Design Principles

The refactoring from monolithic script to service class followed these principles:

1. **Separation of Concerns**: Each component handles a specific aspect of UI automation
2. **Dependency Injection**: Services can be injected and configured at runtime
3. **Event-based Architecture**: Callbacks enable loose coupling between components
4. **Progressive Deprecation**: Legacy code is maintained but clearly marked as deprecated
5. **Graceful Fallbacks**: Services check for dependencies and provide meaningful errors

This modular approach makes the system more testable, maintainable, and extensible. 