"""
Factory for creating Task Orchestrator instances.
"""
from typing import Optional, Any
from core.services.service_registry import ServiceRegistry

class TaskFactory:
    """Factory for creating Task Orchestrator instances."""
    
    @staticmethod
    def create(registry: ServiceRegistry) -> Optional[Any]:
        """
        Create and return a configured Task Orchestrator instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured Task Orchestrator instance
        """
        try:
            # Get dependencies
            logger = registry.get("logger")
            config = registry.get("config_manager")
            prompt_manager = registry.get("prompt_manager")
            chat_manager = registry.get("chat_manager")
            
            # Import here to avoid circular dependencies
            from core.task.task_orchestrator import TaskOrchestrator
            
            # Create and return the task orchestrator
            task_orchestrator = TaskOrchestrator(
                prompt_manager=prompt_manager,
                chat_manager=chat_manager,
                config=config,
                logger=logger
            )
            
            if logger:
                logger.info("✅ Task Orchestrator created successfully")
                
            return task_orchestrator
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create Task Orchestrator: {e}")
            return None 