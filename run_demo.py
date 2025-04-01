#!/usr/bin/env python3
"""
Demo Script for Prompt Orchestration

This script demonstrates the complete prompt orchestration workflow:
1. Project scanning
2. Task generation based on context
3. Task execution via browser automation
4. Validation and feedback
5. Re-execution when needed

It uses simple templates that quickly produce visible results.
"""

import os
import sys
import time
import logging
import argparse
from typing import List, Dict, Any
from pathlib import Path

# Add parent directory to path to allow importing from modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from scripts.orchestration_flow import OrchestrationFlow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('demo.log')
    ]
)

logger = logging.getLogger('demo')

# Define demo templates and outputs
DEMO_TEMPLATES = [
    "generate_service.jinja",
    "generate_ui_tab.jinja"
]

DEMO_OUTPUTS = [
    "core/demo_service.py",
    "interfaces/pyqt/tabs/demo_tab.py"
]

def ensure_resources():
    """Ensure all necessary resources are available."""
    # Create template directory
    template_dir = "templates/cursor_templates"
    os.makedirs(template_dir, exist_ok=True)
    
    # Create output directories
    os.makedirs("core", exist_ok=True)
    os.makedirs("interfaces/pyqt/tabs", exist_ok=True)
    os.makedirs(".cursor/queued_tasks", exist_ok=True)
    os.makedirs(".cursor/executed_tasks", exist_ok=True)
    os.makedirs("memory", exist_ok=True)
    os.makedirs("resources", exist_ok=True)
    os.makedirs("debug/screenshots", exist_ok=True)
    
    # Create required template files if they don't exist
    create_demo_templates(template_dir)
    
    # Create resource images for browser automation
    create_demo_resources()
    
    logger.info("Resources ensured")

def create_demo_templates(template_dir: str):
    """Create simple demo templates for testing."""
    # Service template
    service_template_path = os.path.join(template_dir, "generate_service.jinja")
    if not os.path.exists(service_template_path):
        with open(service_template_path, 'w') as f:
            f.write("""# REQUIREMENTS:
Create a service class that implements the given requirements.

# SERVICE INTERFACE:
Service Name: {{ service_name|default("DemoService") }}
Target Output: {{ target_output }}

# CONTEXT:
Project analyzed: {{ project_name }}
Scan Time: {{ scan_time }}
Core components: {{ core_paths|join(", ") }}
Primary Languages: {{ languages|keys|join(", ") }}

# DEPENDENCIES:
Use logging for proper service diagnostics.
Service should implement an initialization method.
Service should be compatible with the project's existing architecture.

{% if existing_services %}
# EXISTING SERVICES:
{% for service in existing_services %}
- {{ service.name }} (from {{ service.file }})
{% endfor %}
{% endif %}

# OUTPUT EXPECTATIONS:
- Follow PEP8 naming and style conventions
- Implement proper error handling
- Include docstrings and type hints
- Add appropriate logging statements

""")
            
    # UI Tab template
    ui_template_path = os.path.join(template_dir, "generate_ui_tab.jinja")
    if not os.path.exists(ui_template_path):
        with open(ui_template_path, 'w') as f:
            f.write("""# COMPONENT REQUIREMENTS:
Create a PyQt5 UI tab that displays information and allows user interaction.

# UI ELEMENTS:
- Title: {{ tab_title|default("Demo Tab") }}
- Controls: Buttons, labels, and text inputs
- Display area for results

# DATA MODEL:
The tab will need to display and interact with data from the project.

# SERVICE INTEGRATION:
This tab should integrate with services in the project for data processing.

# SIGNAL/SLOT CONNECTIONS:
Implement proper PyQt signal/slot connections for UI interaction.

# UI LAYOUT STRUCTURE:
Use a clean, organized grid or vertical layout.

# OUTPUT SPECIFICATIONS:
Target File: {{ target_output }}
Class Name: {{ class_name|default("DemoTab") }}
Factory Pattern: Required

{% if existing_ui_components %}
# EXISTING UI COMPONENTS:
{% for component in existing_ui_components %}
- {{ component.name }} (from {{ component.file }})
{% endfor %}
{% endif %}

""")
    
    logger.info("Demo templates created")

def create_demo_resources():
    """Create placeholder images for browser automation."""
    resources_dir = "resources"
    
    # Create placeholder files
    placeholders = [
        "cursor_new_chat.png",
        "cursor_input_area.png",
        "cursor_regenerate.png"
    ]
    
    for placeholder in placeholders:
        placeholder_path = os.path.join(resources_dir, placeholder)
        if not os.path.exists(placeholder_path):
            # Create a 1x1 transparent pixel
            try:
                from PIL import Image
                img = Image.new('RGBA', (1, 1), (255, 255, 255, 0))
                img.save(placeholder_path)
            except ImportError:
                # If PIL is not available, just create an empty file
                with open(placeholder_path, 'wb') as f:
                    f.write(b'')
    
    logger.info("Demo resources created")

def run_demo(browser_path=None, debug_mode=False, steps=None):
    """
    Run the complete demo.
    
    Args:
        browser_path: Path to browser executable
        debug_mode: Whether to enable debug mode
        steps: List of steps to execute (all if None)
    """
    # Ensure all resources
    ensure_resources()
    
    # Define the steps
    all_steps = ["scan", "generate", "execute", "validate", "reexecute"]
    
    # Check which steps to run
    steps_to_run = steps or all_steps
    
    # Initialize orchestration flow
    flow = OrchestrationFlow(
        project_root=".",
        template_dir="templates/cursor_templates",
        browser_path=browser_path,
        debug_mode=debug_mode
    )
    
    # Step 1: Scan project
    if "scan" in steps_to_run:
        logger.info("STEP 1: Scanning project for context")
        context = flow.scan_project()
        print(f"Context scan complete with {len(context.get('languages', {}))} languages detected")
        time.sleep(1)
    
    # Step 2: Generate tasks
    task_ids = []
    if "generate" in steps_to_run:
        logger.info("STEP 2: Generating tasks from context")
        
        # Create templates with dynamic names
        templates = DEMO_TEMPLATES.copy()
        outputs = DEMO_OUTPUTS.copy()
        
        # For demo purposes, disable auto-execute to allow inspection
        task_ids = flow.generate_tasks_from_context(
            templates,
            outputs,
            auto_execute=False
        )
        
        print(f"Generated {len(task_ids)} tasks:")
        for i, task_id in enumerate(task_ids):
            print(f"  Task {i+1}: {task_id} -> {outputs[i]}")
        
        print("\nTasks are now in the queue. Inspect them in .cursor/queued_tasks/")
        time.sleep(3)
    
    # Step 3: Execute tasks (if tasks were generated or in the queue)
    results = []
    if "execute" in steps_to_run:
        logger.info("STEP 3: Executing tasks")
        
        if task_ids:
            results = flow.execute_tasks(task_ids)
        else:
            # If no tasks were generated (running only this step), execute all queued tasks
            results = flow.execute_tasks()
        
        if results:
            print(f"Executed {len(results)} tasks:")
            for i, result in enumerate(results):
                status = result.get("status", "unknown")
                task_id = result.get("task_id", "unknown")
                print(f"  Task {i+1} ({task_id}): {status}")
                
                if status == "completed":
                    output_length = len(result.get("output", ""))
                    print(f"    Output length: {output_length} characters")
                    
            print("\nTask execution complete. Tasks moved to .cursor/executed_tasks/")
        else:
            print("No tasks were executed (queue is empty)")
        
        time.sleep(2)
    
    # Step 4: Validate and requeue failed tasks
    if "validate" in steps_to_run:
        logger.info("STEP 4: Validating tasks and requeuing failed ones")
        
        requeued = flow.validate_and_requeue_tasks()
        
        if requeued > 0:
            print(f"Requeued {requeued} failed tasks for re-execution")
        else:
            print("No tasks need to be requeued")
            
        time.sleep(1)
    
    # Step 5: Re-execute requeued tasks
    if "reexecute" in steps_to_run:
        logger.info("STEP 5: Re-executing requeued tasks")
        
        rerun_results = flow.execute_tasks()
        
        if rerun_results:
            print(f"Re-executed {len(rerun_results)} tasks:")
            for i, result in enumerate(rerun_results):
                status = result.get("status", "unknown")
                task_id = result.get("task_id", "unknown")
                print(f"  Task {i+1} ({task_id}): {status}")
        else:
            print("No tasks were re-executed (requeue is empty)")
    
    # Summarize 
    logger.info("Demo complete")
    print("\nDemo complete! Check the generated files in core/ and interfaces/")
    print("Task history is stored in memory/task_history.json")
    print("Project context is stored in memory/project_context.json")
    
    if debug_mode:
        print("Debug screenshots are stored in debug/screenshots/")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Prompt Orchestration Demo")
    
    # Options
    parser.add_argument("--browser", help="Path to browser executable")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--steps", nargs="+", choices=["scan", "generate", "execute", "validate", "reexecute"],
                       help="Specific steps to run (all if not specified)")
    
    args = parser.parse_args()
    
    # Run the demo
    run_demo(args.browser, args.debug, args.steps)

if __name__ == "__main__":
    main() 