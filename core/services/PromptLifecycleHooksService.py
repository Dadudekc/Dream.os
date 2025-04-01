#!/usr/bin/env python3
"""
PromptLifecycleHooksService.py

Implements a structured lifecycle for task/prompt processing with validation,
enrichment, and approval stages. Works as middleware in the task processing pipeline.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Tuple, Union

class PromptLifecycleHooksService:
    """
    Manages the prompt/task lifecycle with hook points for validation, enrichment,
    and approval before execution.
    
    The lifecycle stages are:
    1. on_queue - When a task is first added to the queue
    2. on_inject - When system context is injected before processing
    3. on_validate - Validation of task content/structure before execution
    4. on_approve - Final approval check before dispatch
    5. on_dispatch - Just before execution
    
    Each stage can modify the task or reject it (by returning None).
    """
    
    def __init__(self, logger=None):
        """
        Initialize the lifecycle hooks service.
        
        Args:
            logger: Optional custom logger
        """
        self.logger = logger or logging.getLogger("PromptLifecycleHooks")
        
        # Initialize hook registries for each lifecycle stage
        self._queue_hooks: List[Callable] = []
        self._inject_hooks: List[Callable] = []
        self._validate_hooks: List[Callable] = []
        self._approve_hooks: List[Callable] = []
        self._dispatch_hooks: List[Callable] = []
        
        # Statistics for hook executions
        self.hook_stats = {
            "queue_hooks_run": 0,
            "inject_hooks_run": 0,
            "validate_hooks_run": 0,
            "approve_hooks_run": 0,
            "dispatch_hooks_run": 0,
            "tasks_rejected": 0,
            "tasks_modified": 0,
        }

    # ---------------
    # Hook Registration
    # ---------------
    
    def register_queue_hook(self, hook: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]):
        """Register a hook to run when a task is queued."""
        self._queue_hooks.append(hook)
        self.logger.debug(f"Registered queue hook: {hook.__name__}")
        
    def register_inject_hook(self, hook: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]):
        """Register a hook to run during context injection."""
        self._inject_hooks.append(hook)
        self.logger.debug(f"Registered inject hook: {hook.__name__}")
        
    def register_validate_hook(self, hook: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]):
        """Register a hook to run during task validation."""
        self._validate_hooks.append(hook)
        self.logger.debug(f"Registered validate hook: {hook.__name__}")
        
    def register_approve_hook(self, hook: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]):
        """Register a hook to run during task approval."""
        self._approve_hooks.append(hook)
        self.logger.debug(f"Registered approve hook: {hook.__name__}")
        
    def register_dispatch_hook(self, hook: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]):
        """Register a hook to run just before task dispatch."""
        self._dispatch_hooks.append(hook)
        self.logger.debug(f"Registered dispatch hook: {hook.__name__}")

    # ---------------
    # Lifecycle Methods
    # ---------------
    
    def process_on_queue(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute all registered queue hooks on a task.
        
        Args:
            task: The task dictionary to process
            
        Returns:
            Modified task or None if rejected
        """
        self.logger.debug(f"Processing on_queue for task {task.get('task_id', 'unknown')}")
        task = self._run_hooks(task, self._queue_hooks, "queue")
        
        # Add metadata about hook processing
        if task is not None:
            task["lifecycle"] = task.get("lifecycle", {})
            task["lifecycle"]["queued_at"] = datetime.now().isoformat()
            task["lifecycle"]["queue_processed"] = True
            
        return task
    
    def process_on_inject(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute all registered inject hooks on a task.
        
        Args:
            task: The task dictionary to process
            
        Returns:
            Modified task or None if rejected
        """
        self.logger.debug(f"Processing on_inject for task {task.get('task_id', 'unknown')}")
        task = self._run_hooks(task, self._inject_hooks, "inject")
        
        # Add metadata about hook processing
        if task is not None:
            task["lifecycle"] = task.get("lifecycle", {})
            task["lifecycle"]["injected_at"] = datetime.now().isoformat()
            task["lifecycle"]["inject_processed"] = True
            
        return task
    
    def process_on_validate(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute all registered validate hooks on a task.
        
        Args:
            task: The task dictionary to process
            
        Returns:
            Modified task or None if rejected
        """
        self.logger.debug(f"Processing on_validate for task {task.get('task_id', 'unknown')}")
        task = self._run_hooks(task, self._validate_hooks, "validate")
        
        # Add metadata about hook processing
        if task is not None:
            task["lifecycle"] = task.get("lifecycle", {})
            task["lifecycle"]["validated_at"] = datetime.now().isoformat()
            task["lifecycle"]["validate_processed"] = True
            
        return task
    
    def process_on_approve(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute all registered approve hooks on a task.
        
        Args:
            task: The task dictionary to process
            
        Returns:
            Modified task or None if rejected
        """
        self.logger.debug(f"Processing on_approve for task {task.get('task_id', 'unknown')}")
        task = self._run_hooks(task, self._approve_hooks, "approve")
        
        # Add metadata about hook processing
        if task is not None:
            task["lifecycle"] = task.get("lifecycle", {})
            task["lifecycle"]["approved_at"] = datetime.now().isoformat()
            task["lifecycle"]["approve_processed"] = True
            
        return task
    
    def process_on_dispatch(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute all registered dispatch hooks on a task.
        
        Args:
            task: The task dictionary to process
            
        Returns:
            Modified task or None if rejected
        """
        self.logger.debug(f"Processing on_dispatch for task {task.get('task_id', 'unknown')}")
        task = self._run_hooks(task, self._dispatch_hooks, "dispatch")
        
        # Add metadata about hook processing
        if task is not None:
            task["lifecycle"] = task.get("lifecycle", {})
            task["lifecycle"]["dispatched_at"] = datetime.now().isoformat()
            task["lifecycle"]["dispatch_processed"] = True
            
        return task

    # ---------------
    # Full Lifecycle Processing
    # ---------------
    
    def process_lifecycle(self, task: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Process a task through all lifecycle stages.
        
        Args:
            task: The task dictionary to process
            
        Returns:
            Tuple of (modified task or None if rejected, list of messages)
        """
        messages = []
        
        # Track the original task for comparison
        original_task = task.copy()
        
        # Add lifecycle container if not present
        task["lifecycle"] = task.get("lifecycle", {})
        task["lifecycle"]["started_at"] = datetime.now().isoformat()
        
        # Process each stage
        stages = [
            ("on_queue", self.process_on_queue),
            ("on_inject", self.process_on_inject),
            ("on_validate", self.process_on_validate),
            ("on_approve", self.process_on_approve),
            ("on_dispatch", self.process_on_dispatch)
        ]
        
        for stage_name, stage_processor in stages:
            if task is None:
                messages.append(f"Task rejected at {stage_name} stage")
                break
                
            task = stage_processor(task)
            
            if task is None:
                messages.append(f"Task rejected at {stage_name} stage")
                self.hook_stats["tasks_rejected"] += 1
                break
            
            messages.append(f"Task processed through {stage_name} stage")
        
        # Check if task was modified during processing
        if task is not None and self._is_task_modified(original_task, task):
            self.hook_stats["tasks_modified"] += 1
            messages.append("Task was modified during lifecycle processing")
            
        # Complete the lifecycle metadata
        if task is not None:
            task["lifecycle"]["completed_at"] = datetime.now().isoformat()
            
        return task, messages

    # ---------------
    # Helper Methods
    # ---------------
    
    def _run_hooks(self, task: Dict[str, Any], hooks: List[Callable], 
                  stage: str) -> Optional[Dict[str, Any]]:
        """
        Run a list of hooks on a task.
        
        Args:
            task: The task to process
            hooks: List of hook functions to run
            stage: Stage name for stats and logging
            
        Returns:
            Modified task or None if rejected
        """
        # Update stats
        stage_stat = f"{stage}_hooks_run"
        if stage_stat in self.hook_stats:
            self.hook_stats[stage_stat] += len(hooks)
            
        # Execute each hook in sequence
        for hook in hooks:
            try:
                hook_result = hook(task)
                
                # Check if the hook rejected the task
                if hook_result is None:
                    self.logger.info(f"Task {task.get('task_id', 'unknown')} rejected by {hook.__name__}")
                    return None
                    
                # Use the modified task for the next hook
                task = hook_result
                
            except Exception as e:
                self.logger.error(f"Error in {hook.__name__}: {str(e)}")
                # Continue with the next hook rather than rejecting the task
                
        return task
        
    def _is_task_modified(self, original: Dict[str, Any], 
                         modified: Dict[str, Any]) -> bool:
        """Check if a task was modified during processing."""
        # Create copies without lifecycle metadata for comparison
        original_copy = original.copy()
        modified_copy = modified.copy()
        
        # Remove lifecycle data for comparison
        if "lifecycle" in original_copy:
            del original_copy["lifecycle"]
        if "lifecycle" in modified_copy:
            del modified_copy["lifecycle"]
            
        # Special handling for common fields that might change format but not content
        for field in ["context", "metadata"]:
            # Convert to string for comparison
            if field in original_copy and field in modified_copy:
                try:
                    if isinstance(original_copy[field], (dict, list)):
                        original_copy[field] = json.dumps(original_copy[field], sort_keys=True)
                    if isinstance(modified_copy[field], (dict, list)):
                        modified_copy[field] = json.dumps(modified_copy[field], sort_keys=True)
                except Exception:
                    pass
                    
        return original_copy != modified_copy
        
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about hook executions."""
        return {**self.hook_stats}
        
    def reset_stats(self):
        """Reset hook execution statistics."""
        for key in self.hook_stats:
            self.hook_stats[key] = 0

# ---------------
# BUILT-IN HOOKS
# ---------------

def basic_validation_hook(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """A basic validation hook that ensures required fields are present."""
    required_fields = ["prompt", "task_id"]
    
    for field in required_fields:
        if field not in task or not task[field]:
            return None  # Reject task
            
    return task

def priority_normalization_hook(task: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize priority values to a standard format."""
    # Map various priority terms to standardized values
    priority_map = {
        "highest": "critical",
        "high": "high",
        "normal": "medium",
        "medium": "medium",
        "low": "low",
        "lowest": "low"
    }
    
    # Get current priority, default to "medium"
    current_priority = str(task.get("priority", "medium")).lower()
    
    # Normalize priority if it's in our map
    if current_priority in priority_map:
        task["priority"] = priority_map[current_priority]
    else:
        task["priority"] = "medium"  # Default if not recognized
        
    return task
    
def sanitize_prompt_hook(task: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize the prompt text to prevent injection issues."""
    if "prompt" in task and isinstance(task["prompt"], str):
        # Trim whitespace
        task["prompt"] = task["prompt"].strip()
        
        # Add more sanitization as needed
        
    return task 
