#!/usr/bin/env python3
"""
Prompt Orchestration System Demo

This script demonstrates the complete prompt orchestration system, integrating
all components including project scanning, task generation, execution, validation,
and feedback. It provides options for running in real or simulation mode.
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("demo_orchestration.log")
    ]
)

logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import core components
from core.prompt_cycle_orchestrator import PromptCycleOrchestrator
from core.system_loader import DreamscapeSystemLoader
from core.services.cursor_ui_service import CursorUIService
from interfaces.pyqt.orchestrator_bridge import OrchestratorBridge

def ensure_directories() -> None:
    """Ensure all required directories exist."""
    directories = [
        "templates",
        "templates/service",
        "templates/ui",
        "queued",
        "executed",
        "memory",
        "output"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

def create_demo_templates() -> None:
    """Create demo templates if they don't exist."""
    # Service template
    service_template = """# Generate a Service Class
{{service_name}}Service

## Description
Generate a service class named {{service_name}}Service that handles {{service_function}}.

## Requirements
- Include proper error handling
- Use dependency injection for any dependencies
- Include unit tests for the service

## Code
```typescript
// Your {{service_name}}Service implementation here
```
"""
    
    # UI template
    ui_template = """# Generate a UI Component
{{component_name}}

## Description
Create a {{component_type}} component for the {{component_function}} functionality.

## Requirements
- Use {{framework}} framework
- Make it responsive
- Include proper state management
- Add accessibility features

## Component Preview
```jsx
// Your {{component_name}} implementation here
```
"""
    
    # Create templates if they don't exist
    service_path = Path("templates/service/service_class.txt")
    if not service_path.exists():
        with open(service_path, 'w') as f:
            f.write(service_template)
        logger.info(f"Created demo template: {service_path}")
    
    ui_path = Path("templates/ui/ui_component.txt")
    if not ui_path.exists():
        with open(ui_path, 'w') as f:
            f.write(ui_template)
        logger.info(f"Created demo template: {ui_path}")

def create_demo_tasks() -> List[Dict[str, Any]]:
    """Create demo tasks for execution."""
    tasks = [
        {
            "id": "task-" + str(int(time.time())) + "-1",
            "template_name": "service_class",
            "template_path": "templates/service/service_class.txt",
            "variables": {
                "service_name": "TaskValidation",
                "service_function": "validating executed tasks against custom criteria"
            },
            "target_output": "output/TaskValidationService.ts",
            "status": "queued",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "priority": 1
        },
        {
            "id": "task-" + str(int(time.time())) + "-2",
            "template_name": "ui_component",
            "template_path": "templates/ui/ui_component.txt",
            "variables": {
                "component_name": "TaskStatusCard",
                "component_type": "card",
                "component_function": "displaying task status and results",
                "framework": "React"
            },
            "target_output": "output/TaskStatusCard.jsx",
            "status": "queued",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "priority": 2
        }
    ]
    
    # Save tasks to queued directory
    for task in tasks:
        task_path = Path(f"queued/{task['id']}.json")
        with open(task_path, 'w') as f:
            json.dump(task, f, indent=2)
        logger.info(f"Created demo task: {task_path}")
    
    return tasks

def run_orchestration(
    simulate: bool = False, 
    browser_path: Optional[str] = None,
    debug: bool = False,
    steps: List[str] = None
) -> None:
    """
    Run the orchestration demo.
    
    Args:
        simulate: Whether to run in simulation mode
        browser_path: Path to browser executable
        debug: Enable debug mode
        steps: Specific steps to run (scan, generate, execute, validate, reexecute)
    """
    # Initialize system loader for dependency injection
    system_loader = DreamscapeSystemLoader.get_instance()
    system_loader.load_config()
    
    # Initialize CursorUIService
    cursor_ui_service = None
    if not simulate:
        try:
            cursor_ui_service = CursorUIService(
                browser_path=browser_path,
                debug_mode=debug
            )
            system_loader.register_service('cursor_ui_service', cursor_ui_service)
            logger.info("Initialized CursorUIService for real execution")
        except Exception as e:
            logger.warning(f"Failed to initialize CursorUIService: {e}")
            logger.warning("Falling back to simulation mode")
            simulate = True
    
    # Initialize orchestrator
    orchestrator = PromptCycleOrchestrator(
        cursor_ui_service=cursor_ui_service,
        simulate_only=simulate
    )
    system_loader.register_service('prompt_cycle_orchestrator', orchestrator)
    logger.info(f"Initialized PromptCycleOrchestrator (simulation: {simulate})")
    
    # Create bridge for monitoring events
    bridge = OrchestratorBridge(orchestrator)
    
    # Set up event monitoring
    def on_task_execution_completed(data):
        task_id = data.get("task_id")
        result = data.get("result", {})
        status = result.get("status", "unknown")
        logger.info(f"Task {task_id} execution completed with status: {status}")
    
    def on_task_requeued(data):
        task_id = data.get("task_id")
        success = data.get("success", False)
        logger.info(f"Task {task_id} requeued: {success}")
    
    bridge.task_execution_completed.connect(on_task_execution_completed)
    bridge.task_requeued.connect(on_task_requeued)
    
    # Run specified steps or all steps
    all_steps = not steps or "all" in steps
    
    # Step 1: Scan project for context (if specified)
    if all_steps or "scan" in steps:
        logger.info("Step 1: Scanning project for context")
        orchestrator.scan_project()
        time.sleep(1)  # Give time for events to propagate
    
    # Step 2: Generate tasks from templates (if specified)
    if all_steps or "generate" in steps:
        logger.info("Step 2: Generating tasks from templates")
        # For demo, we'll create predefined tasks
        demo_tasks = create_demo_tasks()
        logger.info(f"Created {len(demo_tasks)} demo tasks")
        time.sleep(1)  # Give time for events to propagate
    
    # Step 3: Execute tasks (if specified)
    if all_steps or "execute" in steps:
        logger.info("Step 3: Executing tasks")
        task_data = orchestrator.refresh_tasks()
        queued_tasks = task_data.get("queued", [])
        
        if queued_tasks:
            logger.info(f"Found {len(queued_tasks)} queued tasks")
            for task in queued_tasks:
                task_id = task.get("id")
                logger.info(f"Executing task {task_id}")
                result = orchestrator.execute_task(task_id)
                if result:
                    logger.info(f"Task {task_id} execution started")
                else:
                    logger.warning(f"Failed to start task {task_id}")
                
                # Wait a bit between tasks
                time.sleep(2)
        else:
            logger.warning("No queued tasks found to execute")
    
    # Step 4: Validate task results (if specified)
    if all_steps or "validate" in steps:
        logger.info("Step 4: Validating task results")
        task_data = orchestrator.refresh_tasks()
        executed_tasks = task_data.get("executed", [])
        
        if executed_tasks:
            logger.info(f"Found {len(executed_tasks)} executed tasks")
            for task in executed_tasks:
                task_id = task.get("id")
                # Custom validation criteria
                validation_criteria = {
                    "text_contains": [task.get("template_name", "")],
                    "no_errors": True
                }
                logger.info(f"Validating task {task_id}")
                is_valid = orchestrator.validate_task(task_id, validation_criteria)
                logger.info(f"Task {task_id} validation: {'passed' if is_valid else 'failed'}")
                
                # Wait a bit between validations
                time.sleep(1)
        else:
            logger.warning("No executed tasks found to validate")
    
    # Step 5: Re-execute failed tasks (if specified)
    if all_steps or "reexecute" in steps:
        logger.info("Step 5: Re-executing failed tasks")
        requeued = orchestrator.requeue_failed_tasks()
        logger.info(f"Requeued {requeued} failed tasks")
        
        # Execute requeued tasks
        task_data = orchestrator.refresh_tasks()
        queued_tasks = task_data.get("queued", [])
        
        if queued_tasks:
            logger.info(f"Found {len(queued_tasks)} queued tasks after requeuing")
            for task in queued_tasks:
                task_id = task.get("id")
                logger.info(f"Re-executing task {task_id}")
                result = orchestrator.execute_task(task_id)
                if result:
                    logger.info(f"Task {task_id} re-execution started")
                else:
                    logger.warning(f"Failed to re-start task {task_id}")
                
                # Wait a bit between tasks
                time.sleep(2)
    
    # Summary
    task_data = orchestrator.refresh_tasks()
    executed_tasks = task_data.get("executed", [])
    queued_tasks = task_data.get("queued", [])
    
    logger.info("\n----- Orchestration Demo Summary -----")
    logger.info(f"Total tasks: {len(executed_tasks) + len(queued_tasks)}")
    logger.info(f"Executed tasks: {len(executed_tasks)}")
    logger.info(f"Queued tasks: {len(queued_tasks)}")
    
    # Calculate success rate
    success_count = sum(1 for t in executed_tasks if t.get("status") == "completed")
    if executed_tasks:
        success_rate = (success_count / len(executed_tasks)) * 100
        logger.info(f"Success rate: {success_rate:.1f}%")
    
    logger.info("----- End of Demo -----\n")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Prompt Orchestration System Demo")
    parser.add_argument("--browser", type=str, help="Path to browser executable")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--simulate", action="store_true", help="Run in simulation mode")
    parser.add_argument("--steps", nargs="+", choices=["all", "scan", "generate", "execute", "validate", "reexecute"],
                       default=["all"], help="Specific steps to run")
    
    args = parser.parse_args()
    
    # Ensure all required directories exist
    ensure_directories()
    
    # Create demo templates
    create_demo_templates()
    
    # Run the orchestration demo
    run_orchestration(
        simulate=args.simulate,
        browser_path=args.browser,
        debug=args.debug,
        steps=args.steps
    )

if __name__ == "__main__":
    main() 