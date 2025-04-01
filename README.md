# Chat Mate - AI Content Generation Studio

A powerful PyQt5-based desktop application for AI-assisted content generation and management.

## Features

- Cursor execution and prompt management
- Task board and project management
- Metrics visualization and monitoring
- Recovery and self-healing capabilities
- Integrated testing and validation

## Installation

```bash
# Clone the repository
git clone https://github.com/dreamos/chat_mate.git
cd chat_mate

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Running the Application

```bash
python -m interfaces.pyqt.DreamOsMainWindow
```

## Development

```bash
# Run tests
pytest

# Run with debug logging
python -m interfaces.pyqt.DreamOsMainWindow --debug
```

## License

MIT License - See LICENSE file for details.

# Dream.OS

A modular extensible platform for AI task automation and productivity enhancement.

## Full Sync Execution Core

The Full Sync Execution Core is a powerful system that turns Dream.OS into a perpetual output engine. It enables seamless integration with Cursor's AI capabilities while providing enhanced task management, template support, and memory synchronization.

### Key Features

#### 1. Template Library
A comprehensive Jinja template system that provides structured instructions for common code generation tasks:
- Located in `templates/cursor_templates/`
- Templates for services, tests, UI tabs, factories, and refactoring
- Structured with clear sections for requirements, context, dependencies, and output specifications

#### 2. Auto-Sync Mode
Enables tasks to be automatically executed without requiring manual approval:
- Toggle option in the Cursor Task Injection tab
- Background task watcher script (`scripts/task_watcher.py`) monitors and processes auto-execution tasks
- Real-time status updates in the Task History tab

#### 3. Task History Viewer
Comprehensive task tracking and management interface:
- Filters for status, template type, and search queries
- Color-coded status indicators
- Detailed task viewer for reviewing prompts, context, and output
- Actions for viewing, deleting, and marking tasks as complete

#### 4. Memory Synchronization
Persistent storage of task history for analysis and reference:
- Centralized task history in JSON format
- Consistent schema for all tasks
- Support for tracking status changes and results

#### 5. Unified Task Object Schema
Standardized data model for task representation:
- TaskManager for enforcing schema consistency
- Support for queued and executed tasks
- Comprehensive metadata including status, timestamps, and execution results

### Usage

#### Creating Tasks
1. Select the "Cursor Task Injection" tab in the CursorExecutionTab
2. Choose a template from the dropdown
3. Enter context variables in JSON format
4. Specify the target output file/directory
5. Toggle auto-execution if desired
6. Click "Create Cursor Task"

#### Viewing Task History
1. Select the "Task History" tab
2. Filter tasks by status, template, or search term
3. Click "View" to see task details
4. Use action buttons to manage tasks

#### Running the Task Watcher
To enable automatic execution of flagged tasks:
```
python scripts/task_watcher.py
```

Optional arguments:
- `--queued-dir`: Directory for queued tasks (default: `.cursor/queued_tasks`)
- `--executed-dir`: Directory for executed tasks (default: `.cursor/executed_tasks`)
- `--memory-file`: File for task history (default: `memory/task_history.json`)
- `--interval`: Check interval in seconds (default: 5)

### Architecture

The Full Sync Execution Core follows a modular architecture:

- **Core Components**:
  - `TaskManager`: Enforces task schema consistency
  - `PromptExecutionService`: Handles template rendering and task execution
  - `TaskWatcher`: Background service for auto-execution

- **UI Components**:
  - `CursorExecutionTab`: Main interface for task creation and management
  - `TaskDetailsModal`: Detailed task viewer
  - `CursorExecutionTabFactory`: Dependency validation and initialization

- **Templates**:
  - Jinja-based template system with structured sections
  - Support for context variables and conditional rendering

### Extending the System

To add new templates:
1. Create a .jinja file in `templates/cursor_templates/`
2. Follow the structured format with requirements, context, and output sections
3. Use Jinja2 syntax for conditional rendering and variable inclusion

To add new task types:
1. Update the TaskManager schema if needed
2. Extend the PromptExecutionService with new capabilities
3. Update the UI components to support the new task type

# Dream.OS Prompt Orchestration System

A comprehensive framework for automating, orchestrating, and monitoring AI prompt execution with browser automation and feedback mechanisms.

## Overview

The Dream.OS Prompt Orchestration System provides a robust infrastructure for executing AI prompts through browser automation, with support for template management, task validation, feedback mechanisms, and real-time monitoring. The system is designed to be modular, extensible, and seamlessly integrated with the Dream.OS application.

## Key Components

### Core Components

- **PromptCycleOrchestrator**: Central orchestration engine that manages the prompt execution cycle from context scanning to task execution and feedback.
- **CursorUIService**: Browser automation service that handles UI interactions, including navigation, typing, validation, and screenshot capture.
- **PromptExecutionService**: Executes prompt templates and manages task lifecycle, including requeuing failed tasks.
- **ProjectContextScanner**: Extracts context from the project codebase to inform prompt generation.
- **TaskFeedbackManager**: Manages feedback on task execution, validation, and requeuing.
- **DreamscapeSystemLoader**: Dependency injection system for service registration and retrieval.

### User Interface Components

- **TaskStatusTab**: Real-time monitoring of task execution status, screenshots, and validation results.
- **CursorPromptPreviewTab**: Template and queued task preview, editing, and execution.
- **SuccessDashboardTab**: Visualization of task execution metrics, success rates, and error trends.
- **OrchestratorBridge**: Connects the orchestration system to the PyQt5-based UI.

## Workflow

The Prompt Orchestration System follows a consistent workflow:

1. **Context Scanning**: The system scans the project codebase to extract relevant context for prompt generation.
2. **Task Generation**: Based on the context and templates, tasks are generated and queued for execution.
3. **Task Execution**: The CursorUIService executes tasks through browser automation, capturing results and screenshots.
4. **Validation**: Task outputs are validated against specified criteria to ensure quality and correctness.
5. **Feedback & Requeuing**: Failed tasks are analyzed and requeued with updated parameters if necessary.
6. **Metrics & Visualization**: Task execution metrics are collected and visualized in the Success Dashboard.

## Features

- **Template Management**: Support for parameterized prompt templates with variable extraction and rendering.
- **Browser Automation**: Robust browser interaction with error handling and screenshot capture.
- **Task Validation**: Flexible validation rules with support for text content, output format, and custom criteria.
- **Real-time Monitoring**: Live updates on task status, validation results, and execution metrics.
- **Simulation Mode**: Test the orchestration system without actual browser interaction.
- **Dependency Injection**: Flexible service architecture with the DreamscapeSystemLoader.
- **Extensible Event System**: Rich event system for reacting to task status changes and other events.

## Getting Started

### Prerequisites

- Python 3.6+
- PyQt5
- PyAutoGUI
- Matplotlib (optional, for visualization)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/dream-os.git
cd dream-os

# Install dependencies
pip install -r requirements.txt
```

### Running the System

1. Start the Dream.OS application:

```bash
python run_dream_os.py
```

2. Navigate to the relevant tabs:
   - "Task Status" tab for monitoring task execution
   - "Prompt Preview" tab for template and task management
   - "Success Dashboard" tab for metrics visualization

3. For standalone operation, you can also use:

```bash
# Run the orchestration flow directly
python scripts/orchestration_flow.py --browser_path "/path/to/browser" --debug

# Run the demo script
python run_demo.py --browser /path/to/browser --debug --steps scan generate execute validate reexecute
```

## Directory Structure

```
dream-os/
│
├── core/                            # Core components
│   ├── prompt_cycle_orchestrator.py # Main orchestration engine
│   ├── prompt_execution_service.py  # Task execution service
│   ├── project_context_scanner.py   # Context scanning service
│   ├── services/                    # Core services
│   │   ├── cursor_ui_service.py     # Browser automation service
│   │   └── task_feedback.py         # Feedback management service
│   └── system_loader.py             # Dependency injection system
│
├── interfaces/                      # User interface components
│   └── pyqt/                        # PyQt5 interface
│       ├── tabs/                    # UI tabs
│       │   ├── task_status_tab.py   # Task status monitoring tab
│       │   ├── cursor_prompt_preview_tab.py # Template preview tab
│       │   └── success_dashboard_tab.py # Metrics visualization tab
│       └── orchestrator_bridge.py   # Bridge between UI and orchestration system
│
├── queued/                          # Queued task files
├── executed/                        # Executed task files
├── templates/                       # Prompt templates
├── memory/                          # Task history and memory files
└── scripts/                         # Utility scripts
    ├── orchestration_flow.py        # Standalone orchestration flow
    └── run_demo.py                  # Demo script
```

## Configuration

The system can be configured through various settings:

1. **Browser Path**: Path to the browser executable for automation.
2. **Debug Mode**: Enable debug logging and screenshots.
3. **Simulation Mode**: Run without actual browser automation.
4. **Template Directory**: Location of prompt templates.
5. **Memory File**: Path to task history memory file.

## Extending the System

The Prompt Orchestration System is designed to be extensible:

1. **Custom Validators**: Add custom validation logic by extending the validation system.
2. **New Templates**: Create new prompt templates in the templates directory.
3. **Additional UI Tabs**: Implement new UI tabs by following the tab factory pattern.
4. **Event Handlers**: Register custom event handlers for orchestration events.

## Troubleshooting

- **Browser Automation Issues**: Ensure the correct browser path and that the browser is compatible with PyAutoGUI.
- **Template Rendering Errors**: Check for proper variable syntax in templates.
- **Task Execution Failures**: Review the logs and screenshots for error details.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The PyQt5 team for the UI framework
- The PyAutoGUI project for browser automation capabilities
- The matplotlib project for visualization tools

---

© 2023 Dream.OS Team 