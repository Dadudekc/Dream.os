# Code Metrics Visualization and Priority Configuration

## Overview

This module provides powerful visualization and configuration tools for the StatefulCursorManager system. It consists of two main components:

1. **Metrics Dashboard**: A web-based dashboard for visualizing code metrics, improvement history, and tracking progress over time.
2. **Priority Weighting Configuration**: A system for customizing how modules are prioritized for improvement.
3. **Auto-Queue Improvements**: A tool to automatically queue top-priority modules for improvement.

These tools work together to provide insights into your codebase's quality evolution and to customize the AI-driven improvement process.

## Metrics Dashboard

The dashboard provides an intuitive interface to monitor code quality metrics, visualize improvements, and identify areas needing attention.

### Features

- **Summary Statistics**: Overview of total improvements, metrics snapshots, and module counts
- **Improvement History**: Timeline of code changes with before/after metrics
- **Module Details**: Detailed metrics for each module with time-series visualizations
- **Top Candidates**: Displays modules most in need of improvement
- **Interactive Charts**: Visual representation of metrics trends over time

### Running the Dashboard

```bash
# Start the dashboard on the default port (5050)
python metrics_dashboard.py

# Specify a custom port
python metrics_dashboard.py --port 8080

# Specify a custom state file
python metrics_dashboard.py --state-file path/to/state.json
```

### Dashboard Screenshots

#### Summary View
Shows overall statistics and recent improvements.

#### Module Details
Displays time-series data of complexity, coverage, and maintainability for specific modules.

#### Improvement Candidates
Lists modules recommended for improvement based on the current scoring algorithm.

## Priority Weighting Configuration

The priority weighting system allows you to customize how modules are selected for improvement by adjusting the weights of different metrics.

### Available Weights

- **complexity** (default: 2.0): Higher complexity = higher priority
- **coverage_deficit** (default: 1.5): Lower coverage = higher priority
- **maintainability_deficit** (default: 1.0): Lower maintainability = higher priority
- **days_since_improvement** (default: 0.5): More days = higher priority
- **days_max_value** (default: 50.0): Maximum value for days factor
- **size_factor** (default: 0.8): Larger files get higher priority
- **churn_factor** (default: 1.2): Frequently changed files get higher priority
- **error_prone_factor** (default: 2.5): Files with many bug fixes get higher priority

### Using the Configuration CLI

```bash
# List all current weights
python priority_weighting_config.py list

# Update a specific weight
python priority_weighting_config.py update complexity 3.0

# Reset weights to defaults
python priority_weighting_config.py reset
```

### Programmatic Usage

```python
from priority_weighting_config import PriorityWeightingConfig

# Initialize the config
config = PriorityWeightingConfig()

# Get current weights
weights = config.get_all_weights()

# Update weights
config.update_weight("complexity", 3.0)
config.update_weights({
    "coverage_deficit": 2.0,
    "maintainability_deficit": 1.5
})

# Calculate a score for a module
score = config.calculate_module_score({
    "complexity": 15,
    "coverage_percentage": 70,
    "maintainability_index": 65,
    "days_since_improvement": 30
})
```

## Auto-Queue Improvements

The auto-queue tool identifies the top N modules according to your priority configuration and automatically queues them for improvement. This is ideal for overnight processing or batch improvements without manual intervention.

### Features

- **Priority-Based Selection**: Uses the same priority scoring as the dashboard
- **Context-Aware Prompts**: Generates improvement prompts based on module context and history
- **Configurable Queue Size**: Choose how many modules to queue at once
- **Dry Run Mode**: Test which modules would be selected without actually queuing them
- **Delay Controls**: Add delays between queuing to manage system resources

### Using the Auto-Queue Tool

```bash
# Queue the top 3 modules for improvement (default)
python auto_queue_improvements.py

# Queue the top 5 modules with a 5-minute delay between each
python auto_queue_improvements.py --count 5 --delay 300

# See which modules would be queued without actually queueing them
python auto_queue_improvements.py --dry-run

# Customize timeout for each improvement task (default: 30 minutes)
python auto_queue_improvements.py --timeout 3600  # 1 hour timeout
```

### Integration with Overnight Processing

You can combine the auto-queue tool with cron jobs or scheduled tasks to automatically improve your codebase overnight:

```bash
# Example cron entry for nightly improvements at 1 AM
# 0 1 * * * cd /path/to/project && python auto_queue_improvements.py --count 10 --delay 300 >> logs/nightly_improvements.log 2>&1
```

## Integration Script

The `metrics_dashboard_integration.py` script provides an easy way to run both the dashboard and apply custom weights to your cursor manager.

```bash
# Start dashboard and apply custom weights
python metrics_dashboard_integration.py --dashboard --apply-weights-to-cursor

# Update weights and apply them
python metrics_dashboard_integration.py --update-weights complexity=3.0 coverage_deficit=2.0 --apply-weights-to-cursor

# Show top 10 candidates with custom weights
python metrics_dashboard_integration.py --apply-weights-to-cursor --max-candidates 10
```

## Installation Requirements

The metrics dashboard requires the following packages:

```
flask>=2.0.0
plotly>=5.0.0
pandas>=1.3.0
```

You can install them using pip:

```bash
pip install flask plotly pandas
```

## Customization

### Dashboard Appearance

The dashboard uses a basic CSS file located in the `metrics_dashboard_static` directory. You can modify this file to customize the appearance of the dashboard.

### Custom Metrics

To add custom metrics to the dashboard, update the `StatefulCursorManager` and `CodeMetricsAnalyzer` classes to collect and store the new metrics, then update the dashboard to display them.

### Custom Prompts

You can modify the auto-queue improvement prompts by extending the `AutoImprovementQueue` class and overriding the `generate_improvement_prompt` method:

```python
from auto_queue_improvements import AutoImprovementQueue

class CustomImprovementQueue(AutoImprovementQueue):
    def generate_improvement_prompt(self, module: str) -> str:
        # Get context using parent method
        context = self.cursor_manager.get_latest_prompt_context(module)
        
        # Custom prompt logic here
        return f"Custom prompt for {module} with context: {context}"
```

## Troubleshooting

### Dashboard Not Showing Data

1. Ensure the state file exists and contains valid JSON data
2. Check that the `memory` directory exists and is writable
3. Verify that the StatefulCursorManager is properly saving state

### Priority Weights Not Taking Effect

1. Check the log files for errors (logs/metrics_integration.log)
2. Ensure the weight names match exactly
3. Verify that the StatefulCursorManager can find the priority config

### Auto-Queue Not Working

1. Verify that the StatefulCursorManager is registered in the system
2. Check the logs for more detailed error information (logs/auto_queue.log)
3. Ensure your system has permissions to create and write to log files

## Contributing

To extend the dashboard or priority weighting system:

1. For new metrics, update both the metrics collection and visualization components
2. For new charts, add them to the relevant endpoints in the dashboard
3. For new weighting factors, add them to the PriorityWeightingConfig class 