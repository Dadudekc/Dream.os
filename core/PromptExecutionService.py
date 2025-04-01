#!/usr/bin/env python3
"""
PromptExecutionService.py

This module provides the service to construct and inject prompt execution tasks 
into Cursor's execution queue (i.e. .cursor/queued_tasks/).
"""

import os
import json
import uuid
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.task_manager import TaskManager
from core.task_feedback import TaskFeedbackManager

logger = logging.getLogger(__name__)

class PromptExecutionService:
    """
    Service for executing prompts.

    It loads a Jinja template, renders it with the provided context,
    and packages this into a task that is injected into Cursor's queued tasks.
    """

    def __init__(
        self, 
        template_dir: str = "templates/cursor_templates",
        queued_dir: str = ".cursor/queued_tasks",
        executed_dir: str = ".cursor/executed_tasks",
        memory_file: str = "memory/task_history.json",
        cursor_automation = None
    ):
        """
        Initialize the PromptExecutionService.
        
        Args:
            template_dir: Directory containing Jinja templates
            queued_dir: Directory for queued tasks
            executed_dir: Directory for executed/completed tasks
            memory_file: File for storing task history
            cursor_automation: Optional CursorAutomation instance for executing tasks
        """
        self.template_dir = template_dir
        self.queued_dir = queued_dir
        self.executed_dir = executed_dir
        self.memory_file = memory_file
        self.task_manager = TaskManager()
        self.feedback_manager = TaskFeedbackManager(memory_file)
        self.cursor_automation = cursor_automation
        
        # Create directories and memory file if they don't exist
        os.makedirs(template_dir, exist_ok=True)
        os.makedirs(queued_dir, exist_ok=True)
        os.makedirs(executed_dir, exist_ok=True)
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        
        # Initialize memory file if it doesn't exist
        if not os.path.exists(memory_file):
            with open(memory_file, 'w') as f:
                json.dump({"tasks": []}, f, indent=2)
        
        # Set up Jinja environment
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Register callbacks for feedback events
        self.feedback_manager.register_callback("on_requeue", self._handle_requeue)
    
    def get_templates(self) -> List[str]:
        """
        Get a list of available templates.
        
        Returns:
            List of template names
        """
        if not os.path.exists(self.template_dir):
            return []
            
        templates = []
        for file in os.listdir(self.template_dir):
            if file.endswith('.jinja'):
                templates.append(file)
        return templates
    
    def render_prompt(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template file
            context: Dictionary of variables to use in the template
            
        Returns:
            Rendered template as a string
        """
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def execute_prompt(self, 
                      template_name: str, 
                      context: Dict[str, Any], 
                      target_output: str,
                      auto_execute: bool = False,
                      validation_criteria: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute a prompt by rendering a template and creating a task file.
        
        Args:
            template_name: Name of the template to use
            context: Context variables for the template
            target_output: Path to the output file/folder
            auto_execute: Flag indicating if task should be automatically executed
            validation_criteria: Optional criteria for validating task output
            
        Returns:
            Path to the created task file
        """
        # Render the template
        rendered_prompt = self.render_prompt(template_name, context)
        
        # Create a task using TaskManager
        task = self.task_manager.create_task(
            template_name=template_name,
            context=context,
            target_output=target_output,
            rendered_prompt=rendered_prompt,
            auto_execute=auto_execute
        )
        
        # Add validation criteria if provided
        if validation_criteria:
            task["validation_criteria"] = validation_criteria
        
        # Create task file
        task_file = os.path.join(self.queued_dir, f"{task['id']}.json")
        with open(task_file, 'w') as f:
            f.write(self.task_manager.serialize_task(task))
            
        # Log task to memory
        self.log_task_to_memory(task)
        
        # If CursorAutomation is available and auto_execute is True, execute now
        if auto_execute and self.cursor_automation:
            self._execute_task_via_automation(task)
            
        return task_file
    
    def _execute_task_via_automation(self, task: Dict[str, Any]) -> None:
        """
        Execute a task via CursorAutomation.
        
        Args:
            task: Task data
        """
        if not self.cursor_automation:
            logger.warning("CursorAutomation not available for task execution")
            return
            
        logger.info(f"Executing task {task.get('id')} via automation")
        
        try:
            # Execute task
            result = self.cursor_automation.execute_task(task)
            
            # Register execution
            self.feedback_manager.register_task_execution(
                task.get('id'), 
                result.get('status', 'error'),
                result
            )
            
            # Validate result if criteria are available
            if "validation_criteria" in task and result.get('status') == 'completed':
                self.feedback_manager.validate_task_result(
                    task.get('id'),
                    result,
                    task.get('validation_criteria')
                )
                
            # Mark task as complete
            self.mark_task_complete(task.get('id'), result)
            
        except Exception as e:
            logger.error(f"Error executing task via automation: {e}")
            
            # Register execution error
            self.feedback_manager.register_task_execution(
                task.get('id'),
                'error',
                {"error": str(e)}
            )
            
    def _handle_requeue(self, validation_data: Dict[str, Any]) -> None:
        """
        Handle requeue event from feedback manager.
        
        Args:
            validation_data: Validation data
        """
        task_id = validation_data.get('task_id')
        if not task_id:
            return
            
        logger.info(f"Requeuing task {task_id} after failed validation")
        
        # Get task from memory
        task = None
        try:
            with open(self.memory_file, 'r') as f:
                memory = json.load(f)
                
            for t in memory.get('tasks', []):
                if t.get('id') == task_id:
                    task = t
                    break
                    
        except Exception as e:
            logger.error(f"Error getting task for requeue: {e}")
            return
            
        if not task:
            logger.warning(f"Task {task_id} not found for requeue")
            return
            
        # Update task status
        task['status'] = 'queued'
        
        # Increment attempts if not already done
        if 'attempts' not in task:
            task['attempts'] = 1
            
        # Create new task file in queued directory
        task_file = os.path.join(self.queued_dir, f"{task_id}.json")
        try:
            with open(task_file, 'w') as f:
                json.dump(task, f, indent=2)
                
            logger.info(f"Task {task_id} requeued successfully")
            
            # If CursorAutomation is available and auto_execute is True, execute now
            if task.get('auto_execute', False) and self.cursor_automation:
                self._execute_task_via_automation(task)
                
        except Exception as e:
            logger.error(f"Error requeuing task: {e}")
        
    def log_task_to_memory(self, task: Dict[str, Any]) -> None:
        """
        Log a task to the memory file.
        
        Args:
            task: Task object to log
        """
        # Make a copy to avoid modifying the original
        memory_task = task.copy()
        
        # Truncate large fields for memory storage
        if "rendered_prompt" in memory_task and len(memory_task["rendered_prompt"]) > 1000:
            memory_task["rendered_prompt"] = memory_task["rendered_prompt"][:1000] + "... [truncated]"
            
        try:
            # Read existing memory
            with open(self.memory_file, 'r') as f:
                memory = json.load(f)
                
            # Check if task already exists
            for i, existing_task in enumerate(memory.get("tasks", [])):
                if existing_task.get("id") == memory_task["id"]:
                    # Update existing task
                    memory["tasks"][i] = memory_task
                    break
            else:
                # Add new task
                memory.setdefault("tasks", []).append(memory_task)
                
            # Write updated memory
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error logging task to memory: {e}")
    
    def mark_task_complete(self, task_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark a task as complete and move it to the executed directory.
        
        Args:
            task_id: ID of the task to mark as complete
            result: Optional result data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find task file
            task_file = os.path.join(self.queued_dir, f"{task_id}.json")
            if not os.path.exists(task_file):
                task_file = os.path.join(self.executed_dir, f"{task_id}.json")
                if not os.path.exists(task_file):
                    return False
                    
            # Read task
            with open(task_file, 'r') as f:
                task = json.loads(f.read())
                
            # Update task status
            task = self.task_manager.update_task_status(task, "completed", result)
                
            # Move to executed directory
            dest_file = os.path.join(self.executed_dir, f"{task_id}.json")
            with open(dest_file, 'w') as f:
                f.write(self.task_manager.serialize_task(task))
                
            # Remove from queued directory if it's there
            if os.path.exists(os.path.join(self.queued_dir, f"{task_id}.json")):
                os.remove(os.path.join(self.queued_dir, f"{task_id}.json"))
                
            # Update in memory
            self.log_task_to_memory(task)
                
            return True
            
        except Exception as e:
            logger.error(f"Error marking task as complete: {e}")
            return False
    
    def update_task_in_memory(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update a task's status in memory without moving the file.
        
        Args:
            task_id: ID of the task to update
            status: New status
            result: Optional result data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read existing memory
            with open(self.memory_file, 'r') as f:
                memory = json.load(f)
                
            # Find and update task
            for task in memory.get("tasks", []):
                if task.get("id") == task_id:
                    task["status"] = status
                    if status in ["completed", "failed"]:
                        task["completed_at"] = datetime.utcnow().isoformat()
                    if result is not None:
                        task["result"] = result
                    break
            else:
                return False
                
            # Write updated memory
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating task in memory: {e}")
            return False
    
    def get_queued_tasks(self) -> List[Dict[str, Any]]:
        """
        Get a list of queued tasks.
        
        Returns:
            List of queued tasks
        """
        tasks = []
        
        if not os.path.exists(self.queued_dir):
            return tasks
            
        for file in os.listdir(self.queued_dir):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(self.queued_dir, file), 'r') as f:
                        task = json.load(f)
                        tasks.append(task)
                except Exception as e:
                    logger.error(f"Error loading task file: {e}")
                    
        return tasks
    
    def get_executed_tasks(self) -> List[Dict[str, Any]]:
        """
        Get a list of executed tasks.
        
        Returns:
            List of executed tasks
        """
        tasks = []
        
        if not os.path.exists(self.executed_dir):
            return tasks
            
        for file in os.listdir(self.executed_dir):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(self.executed_dir, file), 'r') as f:
                        task = json.load(f)
                        tasks.append(task)
                except Exception as e:
                    logger.error(f"Error loading task file: {e}")
                    
        return tasks
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        Get a list of all tasks from memory.
        
        Returns:
            List of all tasks
        """
        try:
            with open(self.memory_file, 'r') as f:
                memory = json.load(f)
                return memory.get("tasks", [])
        except Exception as e:
            logger.error(f"Error loading tasks from memory: {e}")
            return []
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from the system.
        
        Args:
            task_id: ID of the task to delete
            
        Returns:
            True if task was deleted, False otherwise
        """
        deleted = False
        
        # Delete from queued directory
        queued_file = os.path.join(self.queued_dir, f"{task_id}.json")
        if os.path.exists(queued_file):
            try:
                os.remove(queued_file)
                deleted = True
            except Exception as e:
                logger.error(f"Error deleting queued task: {e}")
                
        # Delete from executed directory
        executed_file = os.path.join(self.executed_dir, f"{task_id}.json")
        if os.path.exists(executed_file):
            try:
                os.remove(executed_file)
                deleted = True
            except Exception as e:
                logger.error(f"Error deleting executed task: {e}")
                
        # Delete from memory
        try:
            with open(self.memory_file, 'r') as f:
                memory = json.load(f)
                
            original_count = len(memory.get("tasks", []))
            memory["tasks"] = [task for task in memory.get("tasks", []) if task.get("id") != task_id]
            
            if len(memory.get("tasks", [])) < original_count:
                with open(self.memory_file, 'w') as f:
                    json.dump(memory, f, indent=2)
                deleted = True
                
        except Exception as e:
            logger.error(f"Error removing task from memory: {e}")
            
        return deleted
        
    def set_cursor_automation(self, cursor_automation) -> None:
        """
        Set the CursorAutomation instance.
        
        Args:
            cursor_automation: CursorAutomation instance
        """
        self.cursor_automation = cursor_automation
        
    def requeue_failed_tasks(self) -> int:
        """
        Requeue tasks that failed validation and are marked for requeue.
        
        Returns:
            Number of tasks requeued
        """
        requeued = 0
        
        # Get failed tasks that should be requeued
        tasks = self.feedback_manager.get_failed_tasks_for_requeue()
        
        for task in tasks:
            task_id = task.get('id')
            if not task_id:
                continue
                
            # Update task status
            task['status'] = 'queued'
            
            # Create new task file in queued directory
            task_file = os.path.join(self.queued_dir, f"{task_id}.json")
            try:
                with open(task_file, 'w') as f:
                    json.dump(task, f, indent=2)
                    
                logger.info(f"Task {task_id} requeued successfully")
                requeued += 1
                
                # If CursorAutomation is available and auto_execute is True, execute now
                if task.get('auto_execute', False) and self.cursor_automation:
                    self._execute_task_via_automation(task)
                    
            except Exception as e:
                logger.error(f"Error requeuing task: {e}")
                
        return requeued 