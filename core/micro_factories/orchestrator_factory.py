# core/micro_factories/orchestrator_factory.py

"""
Factory for creating orchestrator-related services:
- PromptCycleOrchestrator (for prompt execution cycles)
- TaskOrchestrator (for task management automation)

Uses service registry for dynamic dependency injection.
Supports both service-type routing and explicit creation patterns.
"""

import logging
from typing import Optional, Any
from config.ConfigManager import ConfigManager
from core.IChatManager import IChatManager
from core.interfaces.IPromptOrchestrator import IPromptOrchestrator

logger = logging.getLogger(__name__)


class OrchestratorFactory:
    """Micro-factory for creating orchestrator services."""

    @staticmethod
    def create(service_type: Optional[str] = None) -> Optional[Any]:
        """
        Create an orchestrator instance using the service registry.

        Args:
            service_type: One of 'cycle' (default) or 'task'

        Returns:
            An orchestrator instance or None if creation fails
        """
        try:
            from core.services.service_registry import ServiceRegistry
            from core.PromptCycleOrchestrator import PromptCycleOrchestrator
            from core.TaskOrchestrator import TaskOrchestrator

            config_manager = ServiceRegistry.get("config_manager")
            prompt_service = ServiceRegistry.get("prompt_service")
            prompt_manager = ServiceRegistry.get("prompt_manager")
            feedback_engine = ServiceRegistry.get("feedback_engine")

            if service_type == "task":
                orchestrator = TaskOrchestrator(
                    config=config_manager,
                    feedback=feedback_engine
                )
                logger.info("✅ TaskOrchestrator created via factory")
                return orchestrator
            else:
                orchestrator = PromptCycleOrchestrator(
                    config_manager=config_manager,
                    prompt_service=prompt_service,
                    prompt_manager=prompt_manager,
                    feedback_engine=feedback_engine
                )
                logger.info("✅ PromptCycleOrchestrator created via factory")
                return orchestrator

        except Exception as e:
            logger.error(f"❌ Failed to create orchestrator ({service_type}): {e}")
            return None

    @staticmethod
    def create_cycle_orchestrator() -> Optional[IPromptOrchestrator]:
        """Create and return a PromptCycleOrchestrator via registry."""
        return OrchestratorFactory.create(service_type="cycle")

    @staticmethod
    def create_task_orchestrator() -> Optional[Any]:
        """Create and return a TaskOrchestrator via registry."""
        return OrchestratorFactory.create(service_type="task")

    @staticmethod
    def create_with_explicit_deps(
        config_manager: ConfigManager,
        chat_manager: Optional[IChatManager] = None,
        prompt_service: Optional[Any] = None,
        prompt_manager: Optional[Any] = None,
        feedback_engine: Optional[Any] = None,
        orchestrator_type: str = "cycle"
    ) -> Optional[Any]:
        """
        Explicit factory method to create orchestrators with manually provided dependencies.

        Args:
            config_manager: Required ConfigManager instance
            chat_manager: Optional IChatManager
            prompt_service: Optional prompt service
            prompt_manager: Optional prompt manager
            feedback_engine: Optional feedback engine
            orchestrator_type: "cycle" or "task"

        Returns:
            An orchestrator instance
        """
        try:
            from core.PromptCycleOrchestrator import PromptCycleOrchestrator
            from core.TaskOrchestrator import TaskOrchestrator

            if orchestrator_type == "task":
                return TaskOrchestrator(
                    config=config_manager,
                    feedback=feedback_engine
                )
            else:
                return PromptCycleOrchestrator(
                    config_manager=config_manager,
                    chat_manager=chat_manager,
                    prompt_service=prompt_service,
                    prompt_manager=prompt_manager,
                    feedback_engine=feedback_engine
                )
        except Exception as e:
            logger.error(f"❌ Failed to create orchestrator with explicit deps ({orchestrator_type}): {e}")
            return None
