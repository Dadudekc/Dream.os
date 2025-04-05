# Debugging Guide for Metrics Dashboard & Auto-Queue System

This guide explains how to test, run, and debug the Metrics Dashboard and Auto-Queue Improvements system using the provided debugging tools.

## Quick Start

To run the application with all debugging features enabled:

```bash
python debug_app.py --dashboard --auto-queue --dry-run
```

This will:
1. Start the metrics dashboard on port 5050
2. Run the auto-queue system in dry-run mode (no actual queueing)
3. Display detailed logs in the console and in `logs/debug.log`

## Command-Line Options

The debug script supports the following options:

```
usage: debug_app.py [-h] [--dashboard] [--port PORT] [--auto-queue] [--count COUNT] 
                    [--delay DELAY] [--dry-run] [--integration] [--apply-weights]
```

| Option | Description |
|--------|-------------|
| `--dashboard` | Run the metrics dashboard |
| `--port PORT` | Set the dashboard port (default: 5050) |
| `--auto-queue` | Run auto-queue improvements |
| `--count COUNT` | Number of modules to queue (default: 3) |
| `--delay DELAY` | Delay between queuing modules in seconds (default: 0) |
| `--dry-run` | Show modules that would be queued without actually queuing them |
| `--integration` | Run the integration script |
| `--apply-weights` | Apply priority weights to cursor manager |

## Common Use Cases

### Running Just the Dashboard

```bash
python debug_app.py --dashboard --port 8080
```

The dashboard will be available at http://localhost:8080.

### Testing Auto-Queue in Dry Run Mode

```bash
python debug_app.py --auto-queue --dry-run --count 5
```

This will identify the top 5 modules that would be queued for improvement without actually queuing them.

### Running the Integration Script

```bash
python debug_app.py --integration --dashboard --auto-queue --dry-run
```

This runs the integrated script that combines both dashboard and auto-queue functionality.

### Applying Custom Priority Weights

```bash
python debug_app.py --integration --apply-weights --auto-queue --dry-run
```

This will apply priority weights from the config to the cursor manager when determining candidates for improvement.

## Debugging Process

### 1. Verify Dependencies

The script automatically checks for required dependencies (Flask, Plotly, Pandas) and directories. If any are missing, it will attempt to create them or provide clear error messages.

### 2. Check Configuration

The script verifies essential config files and creates default versions if they're missing:
- `config/system_config.yml`: System configuration
- `memory/cursor_state.json`: State persistence file
- `metrics_dashboard_static/dashboard.css`: Dashboard styling

### 3. Diagnosing Issues

#### Dashboard Issues

If the dashboard fails to start, check:
- Look at `logs/debug.log` for detailed error messages
- Verify port availability (try a different port with `--port`)
- Ensure the state file contains valid JSON data

#### Auto-Queue Issues

If auto-queue functionality fails, check:
- Look at `logs/auto_queue.log` for specific errors
- Verify that the `StatefulCursorManager` is properly registered in the system config
- Run with `--dry-run` to verify module identification works

#### Integration Issues

If the integration script fails, check:
- Look at `logs/metrics_integration.log` for detailed error messages
- Ensure that all components can be initialized independently first

## Troubleshooting Common Issues

### "Module Not Found" Errors

These usually indicate a missing Python module or incorrect import path. Make sure:
- All dependencies are installed (`pip install flask plotly pandas`)
- Your current directory is the project root
- The `core` directory contains the expected modules

### "Permission Denied" Errors

These can occur when trying to write to log files or state files. Ensure:
- You have write permission to the `logs` and `memory` directories
- No other process is locking these files

### Dashboard Not Showing Data

If the dashboard runs but doesn't display any data:
- Check that `memory/cursor_state.json` contains valid metrics data
- Verify that the dashboard can access the state file
- Try restarting with `--dashboard --port 5051` to use a different port

### Auto-Queue Not Finding Modules

If auto-queue doesn't find any modules to improve:
- Check that metrics exist in the state file
- Verify that the priority calculation is working correctly
- Try modifying the priority weights to include more modules

## Logs and Debugging Output

The debug app generates detailed logs in several locations:
- `logs/debug.log`: Main debugging log
- `logs/system.log`: System-level logging
- `logs/auto_queue.log`: Auto-queue specific logs
- `logs/metrics_integration.log`: Integration specific logs

You can increase verbosity by setting the logging level to DEBUG in the system config file.

## Advanced Debugging

For more advanced debugging needs:

### Running with Python Debugger

```bash
python -m pdb debug_app.py --dashboard
```

### Debugging With Visual Studio Code

1. Open the project in VS Code
2. Set breakpoints in the code
3. Create a launch configuration:
   ```json
   {
     "name": "Debug App",
     "type": "python",
     "request": "launch",
     "program": "${workspaceFolder}/debug_app.py",
     "args": ["--dashboard", "--auto-queue", "--dry-run"],
     "console": "integratedTerminal",
     "justMyCode": false
   }
   ```
4. Press F5 to start debugging 