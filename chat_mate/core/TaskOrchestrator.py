from typing import Dict, Any, TYPE_CHECKING
from chat_mate.core.config.ConfigManager import ConfigManager
from chat_mate.core.interfaces import ILoggingAgent

if TYPE_CHECKING:
    from chat_mate.core.CycleExecutionService import CycleExecutionService

class TaskOrchestrator:
    """Coordinates task execution between agents and cycle services."""

    def __init__(self, config_manager: ConfigManager, logger: ILoggingAgent):
        self.config_manager = config_manager
        self.logger = logger
        self.cycle_service = None

    def set_cycle_service(self, cycle_service: 'CycleExecutionService'):
        """
        Set the cycle service instance to be used by the orchestrator.
        
        Args:
            cycle_service: An initialized CycleExecutionService instance.
        """
        self.cycle_service = cycle_service

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task by determining the appropriate service.

        Args:
            task: Task payload with execution parameters.

        Returns:
            Task execution results.
        """
        if self.cycle_service is None:
            self.logger.log("Task execution failed: CycleExecutionService not initialized", 
                           domain="TaskOrchestrator", level="ERROR")
            return {"status": "error", "message": "CycleExecutionService not initialized"}
            
        self.logger.log(f"Executing task: {task.get('type', 'unknown')}", domain="TaskOrchestrator")
        return self.cycle_service.run_cycle(task)
