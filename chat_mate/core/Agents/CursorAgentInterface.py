from abc import ABC, abstractmethod
from typing import Dict, Any
from config.ConfigManager import ConfigManager
from core.interfaces.ILoggingAgent import ILoggingAgent

class CursorAgentInterface(ABC):
    """Base interface for Cursor-based agents."""
    
    def __init__(self, config_manager: ConfigManager, logger: ILoggingAgent):
        self.config_manager = config_manager
        self.logger = logger
        
    @abstractmethod
    def run_task(self, prompt_template: str, target_file: str) -> Dict[str, Any]:
        """
        Run a Cursor task with the given prompt template.
        
        Args:
            prompt_template: Template string for the Cursor prompt
            target_file: Path to the target file
            
        Returns:
            Dict containing task results and metrics
        """
        pass
        
    def _format_prompt(self, prompt_template: str, **kwargs) -> str:
        """Format the prompt template with given parameters."""
        return prompt_template.format(**kwargs)
        
    def _log_task_start(self, task_name: str, target_file: str) -> None:
        """Log the start of a task."""
        self.logger.log_system_event(
            domain="CursorAgent",
            event="TaskStart",
            message=f"Starting {task_name} on {target_file}"
        )
        
    def _log_task_complete(self, task_name: str, target_file: str, result: Dict[str, Any]) -> None:
        """Log the completion of a task."""
        self.logger.log_system_event(
            domain="CursorAgent",
            event="TaskComplete",
            message=f"Completed {task_name} on {target_file}"
        )
        self.logger.log_debug(f"Task result: {result}") 