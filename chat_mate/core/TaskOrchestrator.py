from typing import Dict, Any
from core.CycleExecutionService import CycleExecutionService
from core.logging.CompositeLogger import CompositeLogger

class TaskOrchestrator:
    """Coordinates task execution between agents and cycle services."""

    def __init__(self, logger: CompositeLogger):
        self.logger = logger
        self.cycle_service = None

    def set_cycle_service(self, cycle_service: CycleExecutionService):
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
