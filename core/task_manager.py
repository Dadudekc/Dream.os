import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

class TaskManager:
    """
    Manages the creation and validation of task objects with a unified schema.
    Enforces task object consistency throughout the system.
    """
    
    def __init__(self):
        """Initialize the TaskManager."""
        self.task_schema = {
            "id": str,
            "template_name": str,
            "target_output": str,
            "context": Dict[str, Any],
            "status": str,
            "timestamp": str,
            "rendered_prompt": str,
            "auto_execute": bool,
            "completed_at": Optional[str],
            "result": Optional[Dict[str, Any]]
        }
    
    def create_task(self, 
                   template_name: str, 
                   context: Dict[str, Any], 
                   target_output: str,
                   rendered_prompt: str,
                   auto_execute: bool = False) -> Dict[str, Any]:
        """
        Create a new task object with a unified schema.
        
        Args:
            template_name: Name of the template used
            context: Context variables for the template
            target_output: Path to the output file/folder
            rendered_prompt: The rendered prompt content
            auto_execute: Flag indicating if task should be automatically executed
            
        Returns:
            A task object dictionary with a unified schema
        """
        task_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        task = {
            "id": task_id,
            "template_name": template_name,
            "target_output": target_output,
            "context": context,
            "status": "queued",
            "timestamp": timestamp,
            "rendered_prompt": rendered_prompt,
            "auto_execute": auto_execute,
            "completed_at": None,
            "result": None
        }
        
        return task
    
    def validate_task(self, task: Dict[str, Any]) -> bool:
        """
        Validate that a task object follows the unified schema.
        
        Args:
            task: Task object to validate
            
        Returns:
            True if task is valid, False otherwise
        """
        required_fields = ["id", "template_name", "target_output", "status", "timestamp"]
        
        # Check all required fields exist
        for field in required_fields:
            if field not in task:
                return False
        
        return True
    
    def update_task_status(self, task: Dict[str, Any], status: str, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update a task's status and result.
        
        Args:
            task: Task object to update
            status: New status (queued, running, completed, failed)
            result: Optional result data
            
        Returns:
            Updated task object
        """
        task = task.copy()  # Create a copy to avoid modifying the original
        task["status"] = status
        
        if status in ["completed", "failed"]:
            task["completed_at"] = datetime.utcnow().isoformat()
            
        if result is not None:
            task["result"] = result
            
        return task
    
    def serialize_task(self, task: Dict[str, Any]) -> str:
        """
        Serialize a task object to JSON.
        
        Args:
            task: Task object to serialize
            
        Returns:
            JSON string representation of the task
        """
        return json.dumps(task, indent=2)
    
    def deserialize_task(self, task_json: str) -> Dict[str, Any]:
        """
        Deserialize a JSON string to a task object.
        
        Args:
            task_json: JSON string to deserialize
            
        Returns:
            Task object dictionary
        """
        try:
            task = json.loads(task_json)
            if self.validate_task(task):
                return task
            else:
                raise ValueError("Invalid task schema")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format") 