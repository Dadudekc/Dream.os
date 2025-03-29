# Logging System

A flexible, extensible logging system that supports multiple logging handlers with asynchronous dispatch.

## Features

- Multiple logging handlers (Console, File, Discord)
- Asynchronous log dispatch
- Log rotation for file logging
- Metrics collection
- Error handling and fallback mechanisms
- Configuration-based setup

## Components

### AsyncDispatcher
Handles asynchronous dispatch of logging operations using a queue-based approach.

```python
from core.logging.utils.AsyncDispatcher import AsyncDispatcher

dispatcher = AsyncDispatcher(max_queue_size=1000)
dispatcher.dispatch(callback, *args, **kwargs)
```

### CompositeLogger
Manages multiple logging handlers and dispatches logs to all registered handlers.

```python
from core.logging.CompositeLogger import CompositeLogger

composite = CompositeLogger([console_logger, file_logger])
composite.log("Message", domain="Test")
```

### LoggerFactory
Creates and configures logger instances based on configuration.

```python
from core.logging.factories.LoggerFactory import LoggerFactory

logger = LoggerFactory.create_logger(config_manager)
```

## Configuration

Example configuration in `unified_config.yaml`:

```yaml
logging:
  types: ["console", "file", "discord"]
  debug_mode: false
  file:
    max_size_mb: 10
    max_files: 5
```

## Usage Examples

### Basic Logging
```python
logger.log("Info message", domain="App")
logger.log_error("Error message", domain="App")
logger.log_debug("Debug message", domain="App")
```

### Event Logging
```python
logger.log_event("user_action", {"action": "login", "user_id": 123})
```

### System Events
```python
logger.log_system_event("App", "startup", "Application starting")
```

## Metrics

The AsyncDispatcher provides metrics about logging operations:

```python
metrics = dispatcher.get_metrics()
print(f"Total dispatches: {metrics['total_dispatches']}")
print(f"Success rate: {metrics['successful_dispatches'] / metrics['total_dispatches']}")
```

## Error Handling

- Failed loggers are reported to the fallback logger
- Queue full conditions trigger synchronous logging
- Log rotation errors are caught and reported

## Best Practices

1. Always use appropriate log levels
2. Include domain information for better categorization
3. Use structured logging for events
4. Monitor metrics for performance issues
5. Configure log rotation based on your needs

## Testing

Run the test suite:

```bash
python -m unittest discover tests/test_logging
```

## Contributing

1. Follow PEP8 standards
2. Add tests for new features
3. Update documentation
4. Submit pull requests

## License

MIT License 