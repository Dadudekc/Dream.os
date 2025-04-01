#!/usr/bin/env python3
"""
PromptCycleOrchestrator

This module provides a high-level orchestrator for managing prompt execution cycles,
including simulation mode for testing without actual execution.
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime

# Add parent directory to path to allow importing from modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.project_context_scanner import ProjectContextScanner
from core.PromptExecutionService import PromptExecutionService
from core.services.cursor_ui_service import CursorUIService, CursorUIServiceFactory
from core.system_loader import get_system_loader


logger = logging.getLogger(__name__)


class PromptCycleOrchestrator:
    """
    High-level orchestrator for managing prompt execution cycles.
    
    This class coordinates the complete prompt execution lifecycle, including
    context scanning, task generation, execution, validation, and feedback.
    It supports both real execution and simulation mode for testing.
    """
    
    def __init__(self,
                project_root: str = ".",
                template_dir: str = "templates/cursor_templates",
                queued_dir: str = ".cursor/queued_tasks",
                executed_dir: str = ".cursor/executed_tasks",
                memory_file: str = "memory/task_history.json",
                context_file: str = "memory/project_context.json",
                browser_path: Optional[str] = None,
                debug_mode: bool = False,
                simulate_only: bool = False,
                system_loader = None):
        """
        Initialize the PromptCycleOrchestrator.
        
        Args:
            project_root: Root directory of the project
            template_dir: Directory containing templates
            queued_dir: Directory for queued tasks
            executed_dir: Directory for executed tasks
            memory_file: Path to the task memory file
            context_file: Path to the context memory file
            browser_path: Path to browser executable
            debug_mode: Whether to enable debug mode
            simulate_only: Whether to run in simulation mode only
            system_loader: Optional system loader for service injection
        """
        self.project_root = project_root
        self.template_dir = template_dir
        self.queued_dir = queued_dir
        self.executed_dir = executed_dir
        self.memory_file = memory_file
        self.context_file = context_file
        self.browser_path = browser_path
        self.debug_mode = debug_mode
        self.simulate_only = simulate_only
        
        # Event handlers
        self.event_handlers = {}
        
        # Create necessary directories
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        os.makedirs(template_dir, exist_ok=True)
        os.makedirs(queued_dir, exist_ok=True)
        os.makedirs(executed_dir, exist_ok=True)
        
        # Get or create system loader
        self.system_loader = system_loader or get_system_loader()
        
        # Initialize components
        self._initialize_components()
        
        logger.info(f"PromptCycleOrchestrator initialized (simulate_only={simulate_only})")
    
    def _initialize_components(self):
        """Initialize the required components."""
        # Initialize context scanner
        logger.info("Initializing ProjectContextScanner...")
        self.scanner = ProjectContextScanner(
            project_root=self.project_root,
            memory_file=self.context_file,
            scan_on_init=False,  # We'll trigger scanning explicitly
            callbacks={
                "on_scan_complete": self._on_scan_complete
            }
        )
        
        # Initialize cursor UI service (either from system loader or create new)
        logger.info("Initializing CursorUIService...")
        self.ui_service = self.system_loader.get_service("cursor_ui_service")
        if not self.ui_service:
            self.ui_service = self.system_loader.initialize_cursor_ui_service(
                browser_path=self.browser_path,
                debug_mode=self.debug_mode
            )
        
        # Initialize execution service
        logger.info("Initializing PromptExecutionService...")
        self.execution_service = PromptExecutionService(
            template_dir=self.template_dir,
            queued_dir=self.queued_dir,
            executed_dir=self.executed_dir,
            memory_file=self.memory_file
        )
        
        # Set UI service in execution service
        self.execution_service.set_cursor_automation(self.ui_service)
    
    def register_event_handler(self, event_name: str, handler: Callable):
        """
        Register an event handler.
        
        Args:
            event_name: Name of the event
            handler: Handler function
        """
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def _trigger_event(self, event_name: str, data: Any = None):
        """
        Trigger an event.
        
        Args:
            event_name: Name of the event
            data: Event data
        """
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_name}: {e}")
    
    def _on_scan_complete(self, data: Dict[str, Any]) -> None:
        """
        Callback for when context scanning is complete.
        
        Args:
            data: Scan completion data
        """
        logger.info(f"Context scan completed in {data.get('duration_seconds', 0):.2f} seconds")
        changed = data.get('changed', False)
        
        if changed:
            logger.info("Project context has changed, updating execution context")
            self._trigger_event("context_changed", data)
        else:
            logger.info("Project context unchanged")
            
        self._trigger_event("scan_complete", data)
    
    def scan_project(self) -> Dict[str, Any]:
        """
        Scan the project to update context information.
        
        Returns:
            Updated context data
        """
        logger.info("Scanning project for context information...")
        context = self.scanner.scan()
        return context
    
    def generate_tasks(self, 
                     template_names: List[str],
                     target_outputs: List[str],
                     auto_execute: bool = False,
                     extra_context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate tasks using the specified templates.
        
        Args:
            template_names: List of template names to use
            target_outputs: List of target output paths
            auto_execute: Whether to auto-execute the tasks
            extra_context: Additional context to include
            
        Returns:
            List of generated task IDs
        """
        if len(template_names) != len(target_outputs):
            raise ValueError("template_names and target_outputs must have the same length")
            
        task_ids = []
        
        for i, template_name in enumerate(template_names):
            target_output = target_outputs[i]
            
            # Get context
            template_context = self.scanner.get_context_for_template(template_name)
            
            # Add extra context if provided
            if extra_context:
                template_context.update(extra_context)
            
            # Add target output
            template_context["target_output"] = target_output
            template_context["generation_time"] = datetime.now().isoformat()
            
            # Define validation criteria
            validation_criteria = {
                "expected_content": [target_output],
                "min_length": 100,
                "requeue_on_failure": True,
                "max_attempts": 3
            }
            
            # Execute the prompt
            task_file = self.execution_service.execute_prompt(
                template_name=template_name,
                context=template_context,
                target_output=target_output,
                auto_execute=auto_execute and not self.simulate_only,  # Don't auto-execute in simulation mode
                validation_criteria=validation_criteria
            )
            
            # Extract task ID from filename
            task_id = os.path.splitext(os.path.basename(task_file))[0]
            task_ids.append(task_id)
            
            logger.info(f"Generated task {task_id} from template {template_name}")
            self._trigger_event("task_generated", {
                "task_id": task_id,
                "template_name": template_name,
                "target_output": target_output
            })
        
        return task_ids
    
    def execute_tasks(self, task_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Execute specified tasks or all queued tasks.
        
        Args:
            task_ids: Optional list of task IDs to execute
            
        Returns:
            List of execution result data
        """
        # Check if in simulation mode
        if self.simulate_only:
            logger.info("Running in simulation mode - tasks will not actually be executed")
            return self._simulate_task_execution(task_ids)
        
        # Get tasks to execute
        if task_ids:
            tasks = []
            for task_id in task_ids:
                task_file = os.path.join(self.queued_dir, f"{task_id}.json")
                if os.path.exists(task_file):
                    with open(task_file, 'r') as f:
                        tasks.append(json.load(f))
        else:
            tasks = self.execution_service.get_queued_tasks()
        
        if not tasks:
            logger.info("No tasks to execute")
            return []
        
        # Execute each task
        results = []
        for task in tasks:
            task_id = task.get('id')
            logger.info(f"Executing task {task_id}...")
            self._trigger_event("task_execution_started", {
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # Execute task
            result = self.ui_service.execute_task(task)
            
            # Apply validation criteria if available
            if "validation_criteria" in task:
                validation = self.ui_service.validate_task_result(
                    result,
                    task.get("validation_criteria")
                )
                result["validation"] = validation
            
            # Mark task as complete
            self.execution_service.mark_task_complete(task_id, result)
            
            results.append(result)
            
            # Trigger event
            self._trigger_event("task_execution_completed", {
                "task_id": task_id,
                "result": result
            })
            
            # Sleep briefly between tasks
            time.sleep(2)
        
        return results
    
    def _simulate_task_execution(self, task_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Simulate task execution without actually running them.
        
        Args:
            task_ids: Optional list of task IDs to simulate
            
        Returns:
            List of simulated execution results
        """
        # Get tasks to simulate
        if task_ids:
            tasks = []
            for task_id in task_ids:
                task_file = os.path.join(self.queued_dir, f"{task_id}.json")
                if os.path.exists(task_file):
                    with open(task_file, 'r') as f:
                        tasks.append(json.load(f))
        else:
            tasks = self.execution_service.get_queued_tasks()
        
        if not tasks:
            logger.info("No tasks to simulate")
            return []
        
        # Simulate each task execution
        results = []
        for task in tasks:
            task_id = task.get('id')
            logger.info(f"Simulating task {task_id}...")
            
            # Trigger event
            self._trigger_event("task_execution_started", {
                "task_id": task_id,
                "timestamp": datetime.now().isoformat(),
                "simulated": True
            })
            
            # Create simulated result
            start_time = datetime.now().isoformat()
            time.sleep(1)  # Brief pause for realism
            
            # Generate simulated output (can be customized based on task type)
            template_name = task.get("template_name", "")
            target_output = task.get("target_output", "")
            output = self._generate_simulated_output(template_name, target_output)
            
            # Create result structure
            result = {
                "task_id": task_id,
                "status": "completed",
                "start_time": start_time,
                "end_time": datetime.now().isoformat(),
                "duration_seconds": 1.0,
                "output": output,
                "simulated": True  # Flag to indicate this was simulated
            }
            
            # Apply validation criteria if available
            if "validation_criteria" in task:
                validation = {
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "passed": True,
                    "checks": [
                        {
                            "type": "content_present",
                            "expected": target_output,
                            "passed": True
                        },
                        {
                            "type": "min_length",
                            "expected": 100,
                            "actual": len(output),
                            "passed": len(output) >= 100
                        }
                    ],
                    "requeue": False,
                    "simulated": True
                }
                result["validation"] = validation
            
            # Mark task as complete
            self.execution_service.mark_task_complete(task_id, result)
            
            results.append(result)
            
            # Trigger event
            self._trigger_event("task_execution_completed", {
                "task_id": task_id,
                "result": result,
                "simulated": True
            })
            
            # Sleep briefly between tasks
            time.sleep(0.5)
        
        return results
    
    def _generate_simulated_output(self, template_name: str, target_output: str) -> str:
        """
        Generate simulated output for a task.
        
        Args:
            template_name: Template name
            target_output: Target output path
            
        Returns:
            Simulated output
        """
        # Generate output based on template and target
        if "service" in template_name.lower():
            return f"""
# Simulated output for {template_name}
# Target: {target_output}

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class {os.path.basename(target_output).replace('.py', '').title()}:
    \"\"\"
    Service class generated from template {template_name}.
    
    This is a simulated output for demonstration purposes.
    \"\"\"
    
    def __init__(self):
        \"\"\"Initialize the service.\"\"\"
        logger.info("Service initialized")
        
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"
        Process the input data.
        
        Args:
            data: Input data
            
        Returns:
            Processed data
        \"\"\"
        return {"result": "success", "processed": True}
        
    def get_status(self) -> str:
        \"\"\"Get the service status.\"\"\"
        return "running"
"""
        elif "ui" in template_name.lower() or "tab" in template_name.lower():
            return f"""
# Simulated output for {template_name}
# Target: {target_output}

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt5.QtCore import Qt, pyqtSignal

class {os.path.basename(target_output).replace('.py', '').title()}(QWidget):
    \"\"\"
    UI Tab generated from template {template_name}.
    
    This is a simulated output for demonstration purposes.
    \"\"\"
    
    def __init__(self, parent=None):
        \"\"\"Initialize the tab.\"\"\"
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        \"\"\"Set up the UI.\"\"\"
        layout = QVBoxLayout(self)
        
        # Add a label
        label = QLabel("Demo Tab")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        # Add a text edit
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        
        # Add a button
        button = QPushButton("Submit")
        button.clicked.connect(self.on_submit)
        layout.addWidget(button)
        
    def on_submit(self):
        \"\"\"Handle submit button click.\"\"\"
        text = self.text_edit.toPlainText()
        print(f"Submitted: {text}")
"""
        else:
            return f"""
# Simulated output for {template_name}
# Target: {target_output}

def main():
    \"\"\"Main function.\"\"\"
    print("This is a simulated output for demonstration purposes.")
    
if __name__ == "__main__":
    main()
"""
    
    def validate_and_requeue_tasks(self) -> int:
        """
        Validate executed tasks and requeue those that failed validation.
        
        Returns:
            Number of tasks requeued
        """
        if self.simulate_only:
            logger.info("Running in simulation mode - no tasks will be requeued")
            return 0
            
        requeued = self.execution_service.requeue_failed_tasks()
        if requeued > 0:
            logger.info(f"Requeued {requeued} tasks for re-execution")
            self._trigger_event("tasks_requeued", {"count": requeued})
        else:
            logger.info("No tasks to requeue")
            
        return requeued
    
    def run_complete_cycle(self, 
                         template_names: List[str],
                         target_outputs: List[str],
                         extra_context: Optional[Dict[str, Any]] = None,
                         max_retry_cycles: int = 3) -> Dict[str, Any]:
        """
        Run a complete prompt cycle.
        
        Args:
            template_names: List of template names to use
            target_outputs: List of target output paths
            extra_context: Additional context to include
            max_retry_cycles: Maximum number of retry cycles
            
        Returns:
            Summary data for the cycle execution
        """
        summary = {
            "start_time": datetime.now().isoformat(),
            "template_names": template_names,
            "target_outputs": target_outputs,
            "simulate_only": self.simulate_only,
            "scan_result": None,
            "generated_tasks": [],
            "execution_results": [],
            "requeue_cycles": 0,
            "success_rate": 0.0,
            "end_time": None,
            "duration_seconds": 0
        }
        
        start_time = time.time()
        
        self._trigger_event("cycle_started", {
            "timestamp": summary["start_time"],
            "templates": template_names,
            "outputs": target_outputs,
            "simulate_only": self.simulate_only
        })
        
        # Step 1: Scan project
        logger.info("Step 1: Scanning project for context")
        summary["scan_result"] = self.scan_project()
        
        # Step 2: Generate tasks
        logger.info("Step 2: Generating tasks from context")
        task_ids = self.generate_tasks(
            template_names,
            target_outputs,
            auto_execute=False,  # We'll execute explicitly
            extra_context=extra_context
        )
        summary["generated_tasks"] = task_ids
        
        # Step 3: Execute tasks
        logger.info("Step 3: Executing tasks")
        execution_results = self.execute_tasks(task_ids)
        summary["execution_results"] = execution_results
        
        # Step 4: Validate and requeue failed tasks
        requeue_cycles = 0
        while requeue_cycles < max_retry_cycles:
            logger.info(f"Step 4: Validating and requeuing tasks (cycle {requeue_cycles + 1})")
            requeued = self.validate_and_requeue_tasks()
            if requeued == 0:
                break
                
            # Execute requeued tasks
            logger.info(f"Step 5: Executing requeued tasks (cycle {requeue_cycles + 1})")
            requeue_results = self.execute_tasks()
            summary["execution_results"].extend(requeue_results)
            
            requeue_cycles += 1
            
        summary["requeue_cycles"] = requeue_cycles
        
        # Calculate success rate
        if execution_results:
            successful = sum(1 for r in summary["execution_results"] 
                          if r.get("status") == "completed" and 
                             r.get("validation", {}).get("passed", False))
            summary["success_rate"] = successful / len(summary["execution_results"])
        
        # Finalize summary
        summary["end_time"] = datetime.now().isoformat()
        summary["duration_seconds"] = time.time() - start_time
        
        logger.info(f"Complete cycle finished in {summary['duration_seconds']:.2f} seconds")
        logger.info(f"Success rate: {summary['success_rate'] * 100:.1f}%")
        
        self._trigger_event("cycle_completed", summary)
        
        return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Prompt Cycle Orchestrator")
    
    # Main options
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--template-dir", default="templates/cursor_templates", help="Template directory")
    parser.add_argument("--browser", help="Path to browser executable")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--simulate", action="store_true", help="Run in simulation mode only")
    
    # Command selection
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("--scan", action="store_true", help="Scan project only")
    command_group.add_argument("--generate", action="store_true", help="Generate tasks from context")
    command_group.add_argument("--execute", action="store_true", help="Execute tasks")
    command_group.add_argument("--cycle", action="store_true", help="Run complete cycle")
    
    # Task options
    parser.add_argument("--templates", nargs="+", help="Template names to use")
    parser.add_argument("--outputs", nargs="+", help="Target output paths")
    parser.add_argument("--tasks", nargs="+", help="Task IDs to execute")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum retry cycles")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('prompt_cycle.log')
        ]
    )
    
    # Initialize orchestrator
    orchestrator = PromptCycleOrchestrator(
        project_root=args.project_root,
        template_dir=args.template_dir,
        browser_path=args.browser,
        debug_mode=args.debug,
        simulate_only=args.simulate
    )
    
    # Process command
    if args.scan:
        logger.info("Scanning project...")
        context = orchestrator.scan_project()
        print(f"Scan complete. Context has {len(context.get('file_metadata', {}))} files")
        
    elif args.generate:
        if not args.templates or not args.outputs:
            parser.error("--generate requires --templates and --outputs")
        
        if len(args.templates) != len(args.outputs):
            parser.error("--templates and --outputs must have the same length")
            
        logger.info("Generating tasks from context...")
        task_ids = orchestrator.generate_tasks(
            args.templates,
            args.outputs
        )
        print(f"Generated {len(task_ids)} tasks: {', '.join(task_ids)}")
        
    elif args.execute:
        logger.info("Executing tasks...")
        results = orchestrator.execute_tasks(args.tasks)
            
        print(f"Executed {len(results)} tasks")
        for result in results:
            status = result.get("status", "unknown")
            task_id = result.get("task_id", "unknown")
            simulated = " (simulated)" if result.get("simulated", False) else ""
            print(f"  Task {task_id}: {status}{simulated}")
            
    elif args.cycle:
        if not args.templates or not args.outputs:
            parser.error("--cycle requires --templates and --outputs")
            
        if len(args.templates) != len(args.outputs):
            parser.error("--templates and --outputs must have the same length")
            
        logger.info("Running complete cycle...")
        summary = orchestrator.run_complete_cycle(
            args.templates,
            args.outputs,
            max_retry_cycles=args.max_retries
        )
        
        print(f"Cycle completed in {summary['duration_seconds']:.2f} seconds")
        print(f"Success rate: {summary['success_rate'] * 100:.1f}%")
        print(f"Generated tasks: {', '.join(summary['generated_tasks'])}")
        print(f"Retry cycles: {summary['requeue_cycles']}")
        if summary['simulate_only']:
            print("Note: Ran in simulation mode - no actual tasks were executed")


if __name__ == "__main__":
    main() 