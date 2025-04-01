"""
Factory for creating Cycle Service instances.
"""
from typing import Optional, Any
from core.services.service_registry import ServiceRegistry

class CycleFactory:
    """Factory for creating Cycle Service instances."""
    
    @staticmethod
    def create(registry: ServiceRegistry) -> Optional[Any]:
        """
        Create and return a configured Cycle Service instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured Cycle Service instance
        """
        try:
            # Get dependencies
            logger = registry.get("logger")
            config = registry.get("config_manager")
            prompt_manager = registry.get("prompt_manager")
            chat_manager = registry.get("chat_manager")
            
            # Import here to avoid circular dependencies
            from core.cycle.cycle_service import CycleService
            
            # Create and return the cycle service
            cycle_service = CycleService(
                prompt_manager=prompt_manager,
                chat_manager=chat_manager,
                config=config,
                logger=logger
            )
            
            if logger:
                logger.info("✅ Cycle Service created successfully")
                
            return cycle_service
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create Cycle Service: {e}")
            return None 