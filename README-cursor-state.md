# Stateful Cursor Manager for ChatMate

## Overview

The StatefulCursorManager provides persistent state management for cursor sessions in the ChatMate project. It enables context-aware AI-assisted development by maintaining history and metrics across sessions. This system is designed to support overnight self-improvement of code through targeted refactoring and optimization.

## Features

- **Persistent session state**: Saves and loads session state between runs
- **Context management**: Maintains relevant context for each module
- **Improvement tracking**: Records code improvements and their impact on metrics
- **Metrics history**: Tracks code quality metrics over time
- **Improvement candidate selection**: Identifies modules that would benefit most from refactoring

## Components

### 1. StatefulCursorManager

Located in `core/StatefulCursorManager.py`, this class extends the base cursor session manager with persistent state capabilities. Key methods include:

- `load_state()` / `save_state()`: Manage state persistence
- `update_context()` / `get_context()`: Handle context values
- `add_improvement_record()`: Records improvements made to code
- `get_improvement_candidates()`: Identifies modules needing improvement
- `queue_stateful_prompt()`: Executes context-aware prompts

### 2. Overnight Improvements Script

Located in `overnight_improvements.py`, this script runs automated code improvements using the StatefulCursorManager. Features:

- Metrics collection and analysis
- Target module selection based on complexity and coverage
- AI-assisted improvement generation
- Test validation of changes
- Git integration for committing successful improvements

## Usage

### Setting Up

1. Ensure the StatefulCursorManager is properly registered in your system loader:

```python
# In your initialization code
from core.StatefulCursorManager import StatefulCursorManager

# Initialize the manager
cursor_manager = StatefulCursorManager(
    config_manager=system_loader.get_service('config_manager'),
    state_file_path="memory/cursor_state.json"
)

# Register the service
system_loader.register_service("stateful_cursor_manager", cursor_manager)
```

2. Create a `memory` directory to store state files:

```bash
mkdir -p memory
```

### Running Overnight Improvements

The overnight improvements script can be run manually or scheduled:

```bash
# Run with default settings
python overnight_improvements.py

# Specify modules to improve
python overnight_improvements.py --modules core/module1.py core/module2.py

# Run in dry-run mode (no actual changes)
python overnight_improvements.py --dry-run

# Run and commit changes if tests pass
python overnight_improvements.py --commit
```

### Scheduling Overnight Runs

To schedule regular overnight runs, you can use cron (Linux/Mac) or Task Scheduler (Windows):

#### Linux/Mac (cron):
```bash
# Edit crontab
crontab -e

# Add line to run at 1 AM every day
0 1 * * * cd /path/to/chat_mate && python overnight_improvements.py --commit >> logs/nightly_run.log 2>&1
```

#### Windows (PowerShell):
```powershell
# Create a scheduled task
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-Command `"cd D:\overnight_scripts\chat_mate; python overnight_improvements.py --commit`""
$trigger = New-ScheduledTaskTrigger -Daily -At 1am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "ChatMate Overnight Improvements" -Description "Run code improvements overnight"
```

## Development

### Adding New Context Types

To add new types of context for the state manager:

1. Update the context schema in `StatefulCursorManager.__init__`
2. Add getter/setter methods for the new context type
3. Update any prompt generation to use the new context

### Customizing Improvement Selection

The candidate selection algorithm can be modified in the `get_improvement_candidates` method to prioritize different metrics or use different selection criteria.

## Troubleshooting

### State File Issues

If the state file becomes corrupted or causes issues:

```bash
# Backup the current state
cp memory/cursor_state.json memory/cursor_state.json.bak

# Create a new state file
echo '{"session_history": [], "metrics_history": {}, "improvement_history": {}, "context": {}}' > memory/cursor_state.json
```

### Logging

The overnight improvements script logs detailed information in `logs/overnight_improvements.log` for debugging. 