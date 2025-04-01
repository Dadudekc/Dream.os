#!/usr/bin/env python3
"""
Simulation script for running a complete prompt orchestration cycle.

This script demonstrates the end-to-end flow of the orchestration system in simulation mode,
from context scanning to task execution, validation, and requeuing.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
import random
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('simulation.log')
    ]
)
logger = logging.getLogger('simulation')

# Placeholder imports - in a real setup, you would import your actual classes
# from core.prompt_cycle_orchestrator import PromptCycleOrchestrator
# from core.project_context_scanner import ProjectContextScanner
# from core.prompt_execution_service import PromptExecutionService
# from interfaces.pyqt.orchestrator_bridge import OrchestratorBridge

class SimulatedScanner:
    """Simulated version of ProjectContextScanner that provides mock project data."""
    
    def __init__(self, root_dir=".", max_depth=10):
        self.root_dir = root_dir
        self.max_depth = max_depth
        self.completion_callback = None
        
    def scan(self):
        """Simulated scan that returns mock project data."""
        logger.info(f"Scanning project at {self.root_dir}")
        time.sleep(1)  # Simulate scan time
        
        # Mock project data
        context = {
            "scan_metadata": {
                "scanner_version": "1.0.0",
                "scan_time": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "scan_duration_seconds": 2.3,
                "files_scanned": 85,
                "root_directory": self.root_dir
            },
            "project_structure": {
                "directories": 12,
                "files_by_type": {
                    "py": 35,
                    "ts": 20,
                    "other": 30
                },
                "root_files": ["requirements.txt", "README.md", "setup.py"]
            },
            "language_stats": {
                "python": {
                    "files": 35,
                    "lines": 4250,
                    "imports": 120,
                    "exports": 45
                },
                "typescript": {
                    "files": 20,
                    "lines": 2800,
                    "imports": 85,
                    "exports": 30
                }
            },
            "component_analysis": {
                "service": [
                    {
                        "name": "PromptExecutionService",
                        "file": "core/prompt_execution_service.py",
                        "lines": 110,
                        "dependencies": 4,
                        "complexity": "medium"
                    }
                ],
                "ui": [
                    {
                        "name": "TaskStatusTab",
                        "file": "interfaces/pyqt/task_status_tab.py",
                        "lines": 130,
                        "dependencies": 3,
                        "complexity": "medium"
                    }
                ]
            }
        }
        
        logger.info("Scan completed successfully")
        
        # Call completion callback if registered
        if self.completion_callback:
            self.completion_callback(context)
            
        return context
        
    def register_completion_callback(self, callback):
        """Register a callback for scan completion."""
        self.completion_callback = callback


class SimulatedExecutionService:
    """Simulated version of PromptExecutionService that handles task execution simulation."""
    
    def __init__(self):
        self.tasks = []
        self.executed_tasks = []
        self.completion_callback = None
        
    def add_task(self, template_name, params, target_output):
        """Add a task to the execution queue."""
        task_id = f"task_{len(self.tasks) + 1}"
        task = {
            "id": task_id,
            "template_name": template_name,
            "params": params,
            "target_output": target_output,
            "status": "queued",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        self.tasks.append(task)
        logger.info(f"Added task {task_id} using template {template_name}")
        return task_id
        
    def execute_task(self, task_id=None):
        """Simulate execution of a task."""
        if not task_id and not self.tasks:
            logger.warning("No tasks to execute")
            return None
            
        if not task_id:
            task = self.tasks.pop(0)
        else:
            task = next((t for t in self.tasks if t["id"] == task_id), None)
            if task:
                self.tasks.remove(task)
            else:
                logger.warning(f"Task {task_id} not found")
                return None
                
        logger.info(f"Executing task {task['id']} with template {task['template_name']}")
        time.sleep(1.5)  # Simulate execution time
        
        # Generate simulated output based on template
        template_type = task['template_name'].split('/')[1].split('_')[0]
        
        if template_type == 'service':
            output = self._generate_service_output(task)
        elif template_type == 'ui':
            output = self._generate_ui_output(task)
        elif template_type == 'scanner':
            output = self._generate_scanner_output(task)
        else:
            output = "Generated content for unknown template type"
            
        # 20% chance of execution "failure" for testing requeue logic
        if random.random() < 0.2:
            task["status"] = "failed"
            task["output"] = "Error: Simulated execution failure"
            task["error"] = "Execution timed out or encountered an error"
            logger.warning(f"Task {task['id']} failed (simulated)")
        else:
            task["status"] = "completed"
            task["output"] = output
            task["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            logger.info(f"Task {task['id']} completed successfully")
            
        self.executed_tasks.append(task)
        
        # Call completion callback if registered
        if self.completion_callback:
            self.completion_callback(task)
            
        return task
        
    def _generate_service_output(self, task):
        """Generate simulated output for a service template."""
        service_name = task['params'].get('service_name', 'Example')
        return f"""
// Generated {service_name}Service
import {{ inject, injectable }} from 'inversify';
import {{ Logger }} from '../logger/logger.service';

@injectable()
export class {service_name}Service implements I{service_name}Service {{
  constructor(
    @inject(TYPES.Logger) private logger: Logger
  ) {{}}
  
  async processRequest(data: any): Promise<any> {{
    this.logger.info('Processing request in {service_name}Service');
    // Implementation for {task['params'].get('service_function', 'processing data')}
    return {{ result: 'Success', data }};
  }}
}}
"""
        
    def _generate_ui_output(self, task):
        """Generate simulated output for a UI template."""
        tab_name = task['params'].get('tab_name', 'Example')
        return f"""
import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import pyqtSignal

class {tab_name}Tab(QWidget):
    \"\"\"
    Tab for {task['params'].get('tab_function', 'displaying data')} in the Dream.OS UI.
    \"\"\"
    
    data_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None, service=None):
        \"\"\"Initialize the {tab_name}Tab.\"\"\"
        super().__init__(parent)
        self.service = service
        self.setup_ui()
        
    def setup_ui(self):
        \"\"\"Set up the tab UI components.\"\"\"
        main_layout = QVBoxLayout(self)
        
        # Header section with title
        header_layout = QHBoxLayout()
        title_label = QLabel("{tab_name}")
        header_layout.addWidget(title_label)
        
        # Add to main layout
        main_layout.addLayout(header_layout)
        
        # More UI components would be added here
"""

    def _generate_scanner_output(self, task):
        """Generate simulated output for a scanner template."""
        scanner_name = task['params'].get('scanner_name', 'Project')
        return f"""
import os
import json
from typing import Dict, List, Any, Callable

class {scanner_name}Scanner:
    \"\"\"
    Scanner that extracts code context from projects.
    \"\"\"
    
    def __init__(self, 
                root_dir: str = ".",
                include_patterns: List[str] = None,
                exclude_patterns: List[str] = None,
                max_depth: int = 10):
        \"\"\"Initialize the scanner with configuration options.\"\"\"
        self.root_dir = root_dir
        self.include_patterns = include_patterns or ["*.py", "*.ts"]
        self.exclude_patterns = exclude_patterns or ["*node_modules*", "*__pycache__*"]
        self.max_depth = max_depth
        self._completion_callback = None
        
    def scan(self) -> Dict[str, Any]:
        \"\"\"
        Perform a full scan of the project.
        
        Returns:
            Dictionary containing extracted context
        \"\"\"
        # Implementation would scan files and extract context
        return {{"scan_completed": True, "files_scanned": 120}}
"""
        
    def requeue_task(self, task_id, updated_params=None):
        """Requeue a failed task with optional updated parameters."""
        task = next((t for t in self.executed_tasks if t["id"] == task_id), None)
        if not task:
            logger.warning(f"Task {task_id} not found for requeuing")
            return False
            
        if task["status"] != "failed":
            logger.warning(f"Cannot requeue task {task_id} that is not failed")
            return False
            
        # Create a new task based on the failed one
        new_task = {
            "id": f"{task_id}_retry",
            "template_name": task["template_name"],
            "params": updated_params or task["params"],
            "target_output": task["target_output"],
            "status": "queued",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "original_task_id": task_id
        }
        
        self.tasks.append(new_task)
        logger.info(f"Requeued task {task_id} as {new_task['id']}")
        return new_task["id"]
        
    def register_completion_callback(self, callback):
        """Register a callback for task completion."""
        self.completion_callback = callback
        
    def get_all_tasks(self):
        """Get all tasks (queued and executed)."""
        return {
            "queued": self.tasks,
            "executed": self.executed_tasks
        }


class SimulatedOrchestrator:
    """Simulated version of PromptCycleOrchestrator that orchestrates the whole process."""
    
    def __init__(self, project_dir=".", templates_dir="templates"):
        self.project_dir = project_dir
        self.templates_dir = templates_dir
        self.scanner = SimulatedScanner(root_dir=project_dir)
        self.execution_service = SimulatedExecutionService()
        self.context = None
        self.event_handlers = {
            "scan_completed": [],
            "task_generated": [],
            "task_execution_started": [],
            "task_execution_completed": [],
            "task_requeued": [],
            "cycle_completed": []
        }
        
        # Register callbacks
        self.scanner.register_completion_callback(self._on_scan_completed)
        self.execution_service.register_completion_callback(self._on_task_completed)
        
    def _on_scan_completed(self, context):
        """Handle completion of project scanning."""
        self.context = context
        logger.info("Project context scan completed")
        self._emit_event("scan_completed", context)
        
    def _on_task_completed(self, task):
        """Handle completion of task execution."""
        logger.info(f"Task {task['id']} execution completed with status: {task['status']}")
        self._emit_event("task_execution_completed", task)
        
    def _emit_event(self, event_name, data):
        """Emit an event to registered handlers."""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                handler(data)
                
    def register_event_handler(self, event_name, handler):
        """Register a handler for a specific event."""
        if event_name in self.event_handlers:
            self.event_handlers[event_name].append(handler)
            logger.info(f"Registered handler for {event_name} event")
        else:
            logger.warning(f"Unknown event: {event_name}")
            
    def load_templates(self):
        """Load templates from the templates directory."""
        templates = {}
        template_dirs = ['service', 'ui', 'scanner']
        
        for template_type in template_dirs:
            type_dir = os.path.join(self.templates_dir, template_type)
            if os.path.exists(type_dir):
                for filename in os.listdir(type_dir):
                    if filename.endswith('.txt'):
                        template_path = os.path.join(type_dir, filename)
                        template_name = f"{template_type}/{os.path.splitext(filename)[0]}"
                        with open(template_path, 'r') as f:
                            templates[template_name] = f.read()
                        logger.info(f"Loaded template: {template_name}")
                        
        logger.info(f"Loaded {len(templates)} templates")
        return templates
        
    def generate_tasks_from_templates(self):
        """Generate tasks from the loaded templates and context."""
        templates = self.load_templates()
        if not templates:
            logger.warning("No templates found")
            return []
            
        tasks = []
        
        # Generate service task
        if "service/service_class_template" in templates:
            service_params = {
                "service_name": "PromptGenerator",
                "service_function": "AI prompt generation and validation",
                "project_name": "Dream.OS",
                "dependency_1": "TemplateRepository",
                "dependency_2": "ValidationService",
                "test_coverage_percentage": 80,
                "primary_method_name": "generatePrompt",
                "primary_method_params": "template: string, params: Record<string, any>",
                "return_type": "Promise<string>",
                "helper_method_name": "validateTemplate",
                "helper_method_params": "template: string",
                "event_name": "PromptGenerated",
                "event_data_type": "GeneratedPromptData"
            }
            
            task_id = self.execution_service.add_task(
                "service/service_class_template",
                service_params,
                "typescript_service"
            )
            tasks.append(task_id)
            self._emit_event("task_generated", {"id": task_id, "type": "service"})
            
        # Generate UI task
        if "ui/tab_component_template" in templates:
            ui_params = {
                "tab_name": "PromptPreview",
                "tab_function": "prompt template preview and editing",
                "data_type": "prompt template",
                "service_integration": "PromptGenerator",
                "additional_dependency": "SyntaxHighlighter",
                "feature_1": "template editing",
                "feature_2": "parameter configuration",
                "signal_name": "templateChanged",
                "signal_params": "str",
                "service_param": "prompt_service",
                "service_var": "prompt_service",
                "primary_method_name": "update_preview",
                "method_params": "template_text: str",
                "primary_functionality": "template preview updating",
                "param_name": "template_text",
                "param_description": "The template text to preview"
            }
            
            task_id = self.execution_service.add_task(
                "ui/tab_component_template",
                ui_params,
                "python_ui_component"
            )
            tasks.append(task_id)
            self._emit_event("task_generated", {"id": task_id, "type": "ui"})
            
        # Generate scanner task
        if "scanner/context_scanner_template" in templates:
            scanner_params = {
                "scanner_name": "CodeBase",
                "project_type": "Python and TypeScript",
                "context_type": "code structure and dependency",
                "stat_type": "code complexity and usage",
                "primary_language": "Python",
                "default_max_depth": 10,
                "default_granularity": "medium",
                "scanner_version": "1.0.0",
                "file_type_1": "py",
                "file_type_2": "ts",
                "language_1": "python",
                "language_2": "typescript",
                "component_type_1": "Service",
                "component_type_2": "Controller",
                "file_extension": "py",
                "note_item_1": "circular dependencies",
                "note_item_2": "unused imports",
                "warning_type": "Complexity"
            }
            
            task_id = self.execution_service.add_task(
                "scanner/context_scanner_template",
                scanner_params,
                "python_scanner"
            )
            tasks.append(task_id)
            self._emit_event("task_generated", {"id": task_id, "type": "scanner"})
            
        logger.info(f"Generated {len(tasks)} tasks")
        return tasks
        
    def execute_tasks(self):
        """Execute all queued tasks."""
        task_results = []
        
        while True:
            tasks = self.execution_service.get_all_tasks()
            if not tasks["queued"]:
                break
                
            # Execute next task
            task_id = tasks["queued"][0]["id"]
            self._emit_event("task_execution_started", {"id": task_id})
            result = self.execution_service.execute_task(task_id)
            task_results.append(result)
            
        logger.info(f"Executed {len(task_results)} tasks")
        return task_results
        
    def validate_tasks(self):
        """Validate executed tasks and requeue failed ones."""
        tasks = self.execution_service.get_all_tasks()
        failed_tasks = [t for t in tasks["executed"] if t["status"] == "failed"]
        
        if not failed_tasks:
            logger.info("No failed tasks to validate")
            return []
            
        requeued_tasks = []
        for task in failed_tasks:
            # In a real system, this could apply validation logic
            # For simulation, we'll just requeue with the same parameters
            new_task_id = self.execution_service.requeue_task(task["id"])
            if new_task_id:
                requeued_tasks.append(new_task_id)
                self._emit_event("task_requeued", {"original_id": task["id"], "new_id": new_task_id})
                
        logger.info(f"Requeued {len(requeued_tasks)} failed tasks")
        return requeued_tasks
        
    def run_simulation(self):
        """Run a complete simulation cycle."""
        logger.info("Starting simulation cycle")
        
        # Step 1: Scan project
        self.scanner.scan()
        
        # Step 2: Generate tasks from templates
        self.generate_tasks_from_templates()
        
        # Step 3: Execute tasks
        self.execute_tasks()
        
        # Step 4: Validate and requeue failed tasks
        requeued_tasks = self.validate_tasks()
        
        # Step 5: Execute requeued tasks
        if requeued_tasks:
            logger.info("Executing requeued tasks")
            self.execute_tasks()
            
        # Complete the cycle
        self._emit_event("cycle_completed", {
            "tasks_executed": len(self.execution_service.executed_tasks),
            "tasks_successful": len([t for t in self.execution_service.executed_tasks if t["status"] == "completed"]),
            "tasks_failed": len([t for t in self.execution_service.executed_tasks if t["status"] == "failed"])
        })
        
        logger.info("Simulation cycle completed")
        return {
            "success": True,
            "tasks": self.execution_service.get_all_tasks()
        }


def print_simulation_summary(results):
    """Print a summary of the simulation results."""
    print("\n" + "="*50)
    print("SIMULATION SUMMARY")
    print("="*50)
    
    # Task statistics
    executed_tasks = results["tasks"]["executed"]
    successful_tasks = [t for t in executed_tasks if t["status"] == "completed"]
    failed_tasks = [t for t in executed_tasks if t["status"] == "failed"]
    
    print(f"Total tasks executed: {len(executed_tasks)}")
    print(f"Successful tasks: {len(successful_tasks)} ({len(successful_tasks)/len(executed_tasks)*100:.1f}%)")
    print(f"Failed tasks: {len(failed_tasks)} ({len(failed_tasks)/len(executed_tasks)*100:.1f}%)")
    
    # Template usage
    template_counts = {}
    for task in executed_tasks:
        template = task["template_name"]
        template_counts[template] = template_counts.get(template, 0) + 1
        
    print("\nTemplate Usage:")
    for template, count in template_counts.items():
        print(f"  - {template}: {count} tasks")
    
    print("\nExecution Timeline:")
    for i, task in enumerate(executed_tasks, 1):
        status_indicator = "✓" if task["status"] == "completed" else "✗"
        print(f"  {i}. [{status_indicator}] {task['template_name']} (ID: {task['id']})")
    
    print("="*50 + "\n")


def main():
    """Main entry point for the simulation script."""
    # Setup directories
    project_dir = os.getcwd()
    templates_dir = os.path.join(project_dir, "templates")
    
    if not os.path.exists(templates_dir):
        logger.error(f"Templates directory not found: {templates_dir}")
        sys.exit(1)
    
    # Check if required template files exist
    required_templates = [
        os.path.join(templates_dir, "service", "service_class_template.txt"),
        os.path.join(templates_dir, "ui", "tab_component_template.txt"),
        os.path.join(templates_dir, "scanner", "context_scanner_template.txt")
    ]
    
    for template_path in required_templates:
        if not os.path.exists(template_path):
            logger.error(f"Required template not found: {template_path}")
            sys.exit(1)
    
    # Create and run the orchestrator
    orchestrator = SimulatedOrchestrator(
        project_dir=project_dir,
        templates_dir=templates_dir
    )
    
    # Register event handlers for logging
    def log_event(event_name):
        def handler(data):
            logger.info(f"Event: {event_name} - {json.dumps(data)[:100]}...")
        return handler
    
    orchestrator.register_event_handler("scan_completed", log_event("scan_completed"))
    orchestrator.register_event_handler("task_generated", log_event("task_generated"))
    orchestrator.register_event_handler("task_execution_started", log_event("task_execution_started"))
    orchestrator.register_event_handler("task_execution_completed", log_event("task_execution_completed"))
    orchestrator.register_event_handler("task_requeued", log_event("task_requeued"))
    orchestrator.register_event_handler("cycle_completed", log_event("cycle_completed"))
    
    # Run the simulation
    print("Starting orchestration simulation...")
    results = orchestrator.run_simulation()
    
    # Print summary
    print_simulation_summary(results)
    
    # Save results to file
    with open("simulation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Detailed results saved to simulation_results.json")
    print(f"Log file saved to simulation.log")


if __name__ == "__main__":
    main() 