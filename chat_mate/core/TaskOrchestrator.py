from typing import Dict, Any
from core.CycleExecutionService import CycleExecutionService
from core.logging.CompositeLogger import CompositeLogger

class TaskOrchestrator:
    """Coordinates task execution between agents and cycle services."""

    def __init__(self, logger: CompositeLogger):
        self.logger = logger
        self.cycle_service = CycleExecutionService()

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task by determining the appropriate service.

        Args:
            task: Task payload with execution parameters.

        Returns:
            Task execution results.
        """
        self.logger.log(f"Executing task: {task.get('type', 'unknown')}", domain="TaskOrchestrator")
        return self.cycle_service.run_cycle(task)
