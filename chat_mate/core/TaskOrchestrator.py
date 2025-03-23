from typing import Dict, Any
from core.AgentDispatcher import AgentDispatcher
from core.cycle.CycleExecutionService import CycleExecutionService
from core.ConfigManager import ConfigManager
from core.logging.CompositeLogger import CompositeLogger

class TaskOrchestrator:
    """Coordinates task execution between Agents and Cycle services."""

    def __init__(self, config_manager: ConfigManager, logger: CompositeLogger):
        self.config_manager = config_manager
        self.logger = logger
        self.agent_dispatcher = AgentDispatcher(config_manager, logger)
        self.cycle_executor = CycleExecutionService(config_manager, logger)

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an incoming task through the appropriate service.

        Args:
            task: Task payload.

        Returns:
            Task execution result.
        """
        self.logger.log(f"Orchestrating task of type {task.get('type')}", domain="TaskOrchestrator")

        task_type = task.get("type")
        if task_type in {"single_cycle", "multi_cycle"}:
            return self.cycle_executor.run_cycle(task.get("payload"), cycle_type=task_type)
        else:
            return self.agent_dispatcher.dispatch_task(task)
