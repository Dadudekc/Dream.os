"""
Task Orchestrator module for managing tasks.
"""
from typing import Optional, Any, Dict, List
import logging

class TaskOrchestrator:
    """Orchestrator for managing tasks."""
    
    def __init__(
        self,
        prompt_manager: Any,
        chat_manager: Any,
        config: Any,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the task orchestrator.
        
        Args:
            prompt_manager: The prompt manager instance
            chat_manager: The chat manager instance
            config: The configuration manager
            logger: Optional logger instance
        """
        self.prompt_manager = prompt_manager
        self.chat_manager = chat_manager
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.tasks = []
        
    def create_task(self, task_config: Dict) -> Optional[Dict]:
        """
        Create a new task.
        
        Args:
            task_config: The task configuration
            
        Returns:
            The created task or None
        """
        try:
            task = {
                "config": task_config,
                "status": "created",
                "steps": []
            }
            self.tasks.append(task)
            self.logger.info(f"Created task: {task_config.get('name', 'unnamed')}")
            return task
        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            return None
            
    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        Get a task by ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task or None
        """
        try:
            for task in self.tasks:
                if task.get("config", {}).get("id") == task_id:
                    return task
            return None
        except Exception as e:
            self.logger.error(f"Error getting task: {e}")
            return None
            
    def update_task_status(self, task_id: str, status: str) -> bool:
        """
        Update a task's status.
        
        Args:
            task_id: The task ID
            status: The new status
            
        Returns:
            True if updated successfully
        """
        try:
            task = self.get_task(task_id)
            if task:
                task["status"] = status
                self.logger.info(f"Updated task {task_id} status to: {status}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating task status: {e}")
            return False
            
    def get_all_tasks(self) -> List[Dict]:
        """
        Get all tasks.
        
        Returns:
            List of all tasks
        """
        return self.tasks 