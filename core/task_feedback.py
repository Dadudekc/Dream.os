#!/usr/bin/env python3
"""
Task Feedback Module

This module handles validation and feedback for prompt execution tasks.
It allows for tracking task execution status, validating results against criteria,
and enabling re-execution of tasks based on feedback.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class TaskFeedbackManager:
    """
    Manages feedback for task execution, validation, and re-execution.
    
    This class tracks task execution status, validates results against predefined
    criteria, and enables re-execution of tasks that didn't meet the criteria.
    """
    
    def __init__(self, memory_file: str = "memory/task_history.json"):
        """
        Initialize the TaskFeedbackManager.
        
        Args:
            memory_file: Path to the memory file for storing task history
        """
        self.memory_file = memory_file
        self.callbacks: Dict[str, List[Callable]] = {
            "on_validation": [],
            "on_success": [],
            "on_failure": [],
            "on_requeue": []
        }
        
        # Ensure the memory directory exists
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        
        # Initialize memory file if it doesn't exist
        if not os.path.exists(memory_file):
            with open(memory_file, 'w') as f:
                json.dump({"tasks": []}, f, indent=2)
    
    def register_callback(self, event_type: str, callback: Callable) -> bool:
        """
        Register a callback for a specific event type.
        
        Args:
            event_type: Type of event to register callback for
            callback: Function to call when event occurs
            
        Returns:
            True if callback was registered, False otherwise
        """
        if event_type not in self.callbacks:
            logger.warning(f"Unknown event type: {event_type}")
            return False
            
        self.callbacks[event_type].append(callback)
        return True
    
    def _trigger_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Trigger all callbacks for a specific event type.
        
        Args:
            event_type: Type of event
            data: Data to pass to callbacks
        """
        if event_type not in self.callbacks:
            return
            
        for callback in self.callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in {event_type} callback: {e}")
    
    def validate_task_result(self, task_id: str, result: Dict[str, Any], 
                           criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a task result against criteria.
        
        Args:
            task_id: ID of the task to validate
            result: Result data from execution
            criteria: Validation criteria
            
        Returns:
            Validation results
        """
        logger.info(f"Validating task {task_id}")
        
        validation = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "passed": False,
            "checks": [],
            "requeue": False
        }
        
        # Get task from memory
        task = self._get_task_from_memory(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found in memory")
            return validation
        
        output = result.get("output", "")
        
        # Run checks
        all_passed = True
        
        # Check if output contains expected content
        if "expected_content" in criteria:
            for content in criteria["expected_content"]:
                check = {
                    "type": "content_present",
                    "expected": content,
                    "passed": content in output
                }
                validation["checks"].append(check)
                all_passed = all_passed and check["passed"]
        
        # Check if output excludes unwanted content
        if "excluded_content" in criteria:
            for content in criteria["excluded_content"]:
                check = {
                    "type": "content_absent",
                    "excluded": content,
                    "passed": content not in output
                }
                validation["checks"].append(check)
                all_passed = all_passed and check["passed"]
        
        # Check minimum length
        if "min_length" in criteria:
            min_length = criteria["min_length"]
            check = {
                "type": "min_length",
                "expected": min_length,
                "actual": len(output),
                "passed": len(output) >= min_length
            }
            validation["checks"].append(check)
            all_passed = all_passed and check["passed"]
        
        # Set validation result
        validation["passed"] = all_passed
        
        # Determine if task should be requeued
        should_requeue = not all_passed and criteria.get("requeue_on_failure", False)
        max_attempts = criteria.get("max_attempts", 3)
        current_attempts = task.get("attempts", 1)
        
        if should_requeue and current_attempts < max_attempts:
            validation["requeue"] = True
            
        # Update task in memory with validation results
        task["validation"] = validation
        task["attempts"] = current_attempts
        self._update_task_in_memory(task)
        
        # Trigger validation callbacks
        self._trigger_callbacks("on_validation", validation)
        
        # Trigger success/failure callbacks
        if all_passed:
            self._trigger_callbacks("on_success", validation)
        else:
            self._trigger_callbacks("on_failure", validation)
            if validation["requeue"]:
                self._trigger_callbacks("on_requeue", validation)
        
        logger.info(f"Validation {'passed' if all_passed else 'failed'} for task {task_id}")
        return validation
    
    def register_task_execution(self, task_id: str, status: str, 
                              result: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register a task execution with status and result.
        
        Args:
            task_id: ID of the task
            status: Status of execution
            result: Optional result data
            
        Returns:
            True if successful, False otherwise
        """
        # Get task from memory
        task = self._get_task_from_memory(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found in memory")
            return False
        
        # Update task in memory
        task["status"] = status
        task["execution_timestamp"] = datetime.now().isoformat()
        if result:
            task["result"] = result
        
        # Increment attempts counter if it exists
        if "attempts" in task:
            task["attempts"] += 1
        else:
            task["attempts"] = 1
        
        return self._update_task_in_memory(task)
    
    def get_failed_tasks_for_requeue(self) -> List[Dict[str, Any]]:
        """
        Get a list of failed tasks that should be requeued.
        
        Returns:
            List of tasks to requeue
        """
        tasks = []
        memory = self._load_memory()
        
        for task in memory.get("tasks", []):
            # Check if task failed validation and is marked for requeue
            validation = task.get("validation", {})
            if (task.get("status") == "completed" 
                and not validation.get("passed", True)
                and validation.get("requeue", False)):
                tasks.append(task)
        
        return tasks
    
    def _get_task_from_memory(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task from memory by ID.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Task data if found, None otherwise
        """
        memory = self._load_memory()
        
        for task in memory.get("tasks", []):
            if task.get("id") == task_id:
                return task
                
        return None
    
    def _update_task_in_memory(self, task: Dict[str, Any]) -> bool:
        """
        Update a task in memory.
        
        Args:
            task: Task data to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            memory = self._load_memory()
            
            # Find and update task
            for i, existing_task in enumerate(memory.get("tasks", [])):
                if existing_task.get("id") == task.get("id"):
                    memory["tasks"][i] = task
                    break
            else:
                # Task not found, add it
                memory.setdefault("tasks", []).append(task)
            
            # Save memory
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating task in memory: {e}")
            return False
    
    def _load_memory(self) -> Dict[str, Any]:
        """
        Load memory from file.
        
        Returns:
            Memory data
        """
        try:
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            return {"tasks": []} 