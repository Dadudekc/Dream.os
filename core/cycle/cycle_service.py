"""
Cycle Service module for managing task cycles.
"""
from typing import Optional, Any, Dict, List
import logging

class CycleService:
    """Service for managing task cycles."""
    
    def __init__(
        self,
        prompt_manager: Any,
        chat_manager: Any,
        config: Any,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the cycle service.
        
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
        self.current_cycle = None
        
    def start_cycle(self, task: Dict) -> bool:
        """
        Start a new task cycle.
        
        Args:
            task: The task configuration
            
        Returns:
            True if cycle started successfully
        """
        try:
            self.current_cycle = {
                "task": task,
                "steps": [],
                "status": "started"
            }
            self.logger.info(f"Started new cycle for task: {task.get('name', 'unnamed')}")
            return True
        except Exception as e:
            self.logger.error(f"Error starting cycle: {e}")
            return False
            
    def add_step(self, step: Dict) -> bool:
        """
        Add a step to the current cycle.
        
        Args:
            step: The step configuration
            
        Returns:
            True if step added successfully
        """
        if not self.current_cycle:
            self.logger.warning("No active cycle to add step to")
            return False
            
        try:
            self.current_cycle["steps"].append(step)
            self.logger.info(f"Added step to cycle: {step.get('name', 'unnamed')}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding step: {e}")
            return False
            
    def get_current_cycle(self) -> Optional[Dict]:
        """
        Get the current cycle state.
        
        Returns:
            The current cycle state or None
        """
        return self.current_cycle
        
    def end_cycle(self, status: str = "completed") -> bool:
        """
        End the current cycle.
        
        Args:
            status: The final status
            
        Returns:
            True if cycle ended successfully
        """
        if not self.current_cycle:
            self.logger.warning("No active cycle to end")
            return False
            
        try:
            self.current_cycle["status"] = status
            self.logger.info(f"Ended cycle with status: {status}")
            self.current_cycle = None
            return True
        except Exception as e:
            self.logger.error(f"Error ending cycle: {e}")
            return False 