"""
Factory for creating Orchestrator instances.
"""
from typing import Optional, Any
from core.services.service_registry import ServiceRegistry

class OrchestratorFactory:
    """Factory for creating Orchestrator instances."""
    
    @staticmethod
    def create(registry: ServiceRegistry) -> Optional[Any]:
        """
        Create and return a configured Orchestrator instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured Orchestrator instance
        """
        try:
            # Get dependencies
            logger = registry.get("logger")
            config = registry.get("config_manager")
            prompt_manager = registry.get("prompt_manager")
            chat_manager = registry.get("chat_manager")
            
            # Import here to avoid circular dependencies
            from core.orchestrator import Orchestrator
            
            # Create and return the orchestrator
            orchestrator = Orchestrator(
                prompt_manager=prompt_manager,
                chat_manager=chat_manager,
                config=config,
                logger=logger
            )
            
            if logger:
                logger.info("✅ Orchestrator created successfully")
                
            return orchestrator
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create Orchestrator: {e}")
            return None 