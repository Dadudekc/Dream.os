#!/usr/bin/env python3
"""
Orchestration Flow

This script implements the complete prompt orchestration flow by integrating the
ProjectContextScanner, PromptExecutionService, and CursorUIService components.

It demonstrates the full end-to-end process of:
1. Scanning the project for context
2. Generating tasks based on context
3. Executing tasks with browser automation
4. Validating results and providing feedback
5. Re-executing tasks if needed
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# Add parent directory to path to allow importing from core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.project_context_scanner import ProjectContextScanner
from core.PromptExecutionService import PromptExecutionService
from core.services.cursor_ui_service import CursorUIService, CursorUIServiceFactory

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('orchestration_flow.log')
    ]
)

logger = logging.getLogger('orchestration_flow')

class OrchestrationFlow:
    """
    Implements the complete prompt orchestration flow by integrating the
    ProjectContextScanner, PromptExecutionService, and CursorUIService components.
    """
    
    def __init__(self,
                project_root: str = ".",
                template_dir: str = "templates/cursor_templates",
                queued_dir: str = ".cursor/queued_tasks",
                executed_dir: str = ".cursor/executed_tasks",
                memory_file: str = "memory/task_history.json",
                context_file: str = "memory/project_context.json",
                browser_path: Optional[str] = None,
                debug_mode: bool = False):
        """
        Initialize the OrchestrationFlow.
        
        Args:
            project_root: Root directory of the project
            template_dir: Directory containing templates
            queued_dir: Directory for queued tasks
            executed_dir: Directory for executed tasks
            memory_file: Path to the task memory file
            context_file: Path to the context memory file
            browser_path: Path to browser executable
            debug_mode: Whether to enable debug mode
        """
        self.project_root = project_root
        self.template_dir = template_dir
        self.queued_dir = queued_dir
        self.executed_dir = executed_dir
        self.memory_file = memory_file
        self.context_file = context_file
        self.browser_path = browser_path
        self.debug_mode = debug_mode
        
        # Create necessary directories
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        os.makedirs(template_dir, exist_ok=True)
        os.makedirs(queued_dir, exist_ok=True)
        os.makedirs(executed_dir, exist_ok=True)
        
        # Initialize components
        logger.info("Initializing ProjectContextScanner...")
        self.scanner = ProjectContextScanner(
            project_root=project_root,
            memory_file=context_file,
            scan_on_init=False,  # We'll trigger scanning explicitly
            callbacks={
                "on_scan_complete": self._on_scan_complete
            }
        )
        
        # Create service registry for dependency injection
        self.service_registry = {}
        
        logger.info("Initializing CursorUIService...")
        self.ui_service = CursorUIServiceFactory.create(
            browser_path=browser_path,
            debug_mode=debug_mode,
            service_registry=self.service_registry
        )
        
        # Register UI service in the registry
        self.service_registry["cursor_ui_service"] = self.ui_service
        
        logger.info("Initializing PromptExecutionService...")
        self.execution_service = PromptExecutionService(
            template_dir=template_dir,
            queued_dir=queued_dir,
            executed_dir=executed_dir,
            memory_file=memory_file
        )
        
        # Set UI service in execution service
        self.execution_service.set_cursor_automation(self.ui_service)
        
        # Register execution service in the registry
        self.service_registry["prompt_execution_service"] = self.execution_service
        
        logger.info("Orchestration flow initialized")
    
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
            # Here we could trigger task generation based on the new context
        else:
            logger.info("Project context unchanged")
    
    def scan_project(self) -> Dict[str, Any]:
        """
        Scan the project to update context information.
        
        Returns:
            Updated context data
        """
        logger.info("Scanning project for context information...")
        return self.scanner.scan()
    
    def generate_tasks_from_context(self, 
                                   template_names: List[str],
                                   target_outputs: List[str],
                                   auto_execute: bool = False) -> List[str]:
        """
        Generate tasks for each of the specified templates using project context.
        
        Args:
            template_names: List of template names to use
            target_outputs: List of target output paths (same length as template_names)
            auto_execute: Whether to auto-execute the tasks
            
        Returns:
            List of generated task IDs
        """
        if len(template_names) != len(target_outputs):
            raise ValueError("template_names and target_outputs must have the same length")
            
        task_ids = []
        context = self.scanner.get_context()
        
        for i, template_name in enumerate(template_names):
            target_output = target_outputs[i]
            
            # Get context specifically formatted for this template
            template_context = self.scanner.get_context_for_template(template_name)
            
            # Add additional context
            template_context["target_output"] = target_output
            template_context["generation_time"] = datetime.now().isoformat()
            
            # Define validation criteria for this template
            validation_criteria = {
                "expected_content": [target_output],  # Task should mention the target output
                "min_length": 100,  # Task should produce a minimum amount of content
                "requeue_on_failure": True,  # Requeue the task if validation fails
                "max_attempts": 3  # Maximum number of attempts
            }
            
            # Execute the prompt
            task_file = self.execution_service.execute_prompt(
                template_name=template_name,
                context=template_context,
                target_output=target_output,
                auto_execute=auto_execute,
                validation_criteria=validation_criteria
            )
            
            # Extract task ID from filename
            task_id = os.path.splitext(os.path.basename(task_file))[0]
            task_ids.append(task_id)
            
            logger.info(f"Generated task {task_id} from template {template_name}")
        
        return task_ids
    
    def execute_tasks(self, task_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Execute specified tasks or all queued tasks.
        
        Args:
            task_ids: Optional list of task IDs to execute (all queued tasks if None)
            
        Returns:
            List of execution result data
        """
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
            logger.info(f"Executing task {task.get('id')}...")
            
            # Execute via CursorUIService
            result = self.ui_service.execute_task(task)
            
            # Apply validation criteria if available
            if "validation_criteria" in task:
                validation = self.ui_service.validate_task_result(
                    result,
                    task.get("validation_criteria")
                )
                result["validation"] = validation
            
            # Mark task as complete
            self.execution_service.mark_task_complete(task.get('id'), result)
            
            results.append(result)
            
            # Log result
            status = result.get("status", "unknown")
            logger.info(f"Task {task.get('id')} execution {status}")
            
            # Sleep briefly between tasks
            time.sleep(2)
        
        return results
    
    def validate_and_requeue_tasks(self) -> int:
        """
        Validate executed tasks and requeue those that failed validation.
        
        Returns:
            Number of tasks requeued
        """
        requeued = self.execution_service.requeue_failed_tasks()
        if requeued > 0:
            logger.info(f"Requeued {requeued} tasks for re-execution")
        else:
            logger.info("No tasks to requeue")
        return requeued
    
    def run_complete_flow(self, 
                         template_names: List[str],
                         target_outputs: List[str],
                         auto_execute: bool = True,
                         max_retry_cycles: int = 3) -> Dict[str, Any]:
        """
        Run the complete orchestration flow.
        
        Args:
            template_names: List of template names to use
            target_outputs: List of target output paths
            auto_execute: Whether to auto-execute tasks
            max_retry_cycles: Maximum number of retry cycles
            
        Returns:
            Summary data for the flow execution
        """
        summary = {
            "start_time": datetime.now().isoformat(),
            "template_names": template_names,
            "target_outputs": target_outputs,
            "scan_result": None,
            "generated_tasks": [],
            "execution_results": [],
            "requeue_cycles": 0,
            "success_rate": 0.0,
            "end_time": None,
            "duration_seconds": 0
        }
        
        start_time = time.time()
        
        # Step 1: Scan project
        logger.info("Step 1: Scanning project for context")
        summary["scan_result"] = self.scan_project()
        
        # Step 2: Generate tasks
        logger.info("Step 2: Generating tasks from context")
        task_ids = self.generate_tasks_from_context(
            template_names,
            target_outputs,
            auto_execute=auto_execute
        )
        summary["generated_tasks"] = task_ids
        
        # If auto_execute is False, we're done
        if not auto_execute:
            logger.info("Auto-execute is disabled, stopping after task generation")
            summary["end_time"] = datetime.now().isoformat()
            summary["duration_seconds"] = time.time() - start_time
            return summary
        
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
        
        logger.info(f"Complete flow finished in {summary['duration_seconds']:.2f} seconds")
        logger.info(f"Success rate: {summary['success_rate'] * 100:.1f}%")
        
        return summary

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Orchestration Flow")
    
    # Main options
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--template-dir", default="templates/cursor_templates", help="Template directory")
    parser.add_argument("--browser", help="Path to browser executable")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    # Command selection
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("--scan", action="store_true", help="Scan project only")
    command_group.add_argument("--generate", action="store_true", help="Generate tasks from context")
    command_group.add_argument("--execute", action="store_true", help="Execute tasks")
    command_group.add_argument("--validate", action="store_true", help="Validate and requeue tasks")
    command_group.add_argument("--flow", action="store_true", help="Run complete flow")
    
    # Task options
    parser.add_argument("--templates", nargs="+", help="Template names to use")
    parser.add_argument("--outputs", nargs="+", help="Target output paths")
    parser.add_argument("--tasks", nargs="+", help="Task IDs to execute")
    parser.add_argument("--no-auto-execute", action="store_true", help="Disable auto-execution")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum retry cycles")
    
    args = parser.parse_args()
    
    # Initialize orchestration flow
    flow = OrchestrationFlow(
        project_root=args.project_root,
        template_dir=args.template_dir,
        browser_path=args.browser,
        debug_mode=args.debug
    )
    
    # Process command
    if args.scan:
        logger.info("Scanning project...")
        context = flow.scan_project()
        print(f"Scan complete. Context has {len(context.get('file_metadata', {}))} files")
        
    elif args.generate:
        if not args.templates or not args.outputs:
            parser.error("--generate requires --templates and --outputs")
        
        if len(args.templates) != len(args.outputs):
            parser.error("--templates and --outputs must have the same length")
            
        logger.info("Generating tasks from context...")
        task_ids = flow.generate_tasks_from_context(
            args.templates,
            args.outputs,
            auto_execute=not args.no_auto_execute
        )
        print(f"Generated {len(task_ids)} tasks: {', '.join(task_ids)}")
        
    elif args.execute:
        logger.info("Executing tasks...")
        if args.tasks:
            results = flow.execute_tasks(args.tasks)
        else:
            results = flow.execute_tasks()
            
        print(f"Executed {len(results)} tasks")
        for result in results:
            status = result.get("status", "unknown")
            task_id = result.get("task_id", "unknown")
            print(f"  Task {task_id}: {status}")
            
    elif args.validate:
        logger.info("Validating and requeuing tasks...")
        requeued = flow.validate_and_requeue_tasks()
        print(f"Requeued {requeued} tasks")
        
    elif args.flow:
        if not args.templates or not args.outputs:
            parser.error("--flow requires --templates and --outputs")
            
        if len(args.templates) != len(args.outputs):
            parser.error("--templates and --outputs must have the same length")
            
        logger.info("Running complete flow...")
        summary = flow.run_complete_flow(
            args.templates,
            args.outputs,
            auto_execute=not args.no_auto_execute,
            max_retry_cycles=args.max_retries
        )
        
        print(f"Flow completed in {summary['duration_seconds']:.2f} seconds")
        print(f"Success rate: {summary['success_rate'] * 100:.1f}%")
        print(f"Generated tasks: {', '.join(summary['generated_tasks'])}")
        print(f"Retry cycles: {summary['requeue_cycles']}")

if __name__ == "__main__":
    main() 