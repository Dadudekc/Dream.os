"""
Factory for creating Memory Manager instances.
"""
from typing import Optional, Any
from core.services.service_registry import ServiceRegistry

class MemoryFactory:
    """Factory for creating Memory Manager instances."""
    
    @staticmethod
    def create(registry: ServiceRegistry) -> Optional[Any]:
        """
        Create and return a configured Memory Manager instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured Memory Manager instance
        """
        try:
            # Get dependencies
            logger = registry.get("logger")
            config = registry.get("config_manager")
            
            # Import here to avoid circular dependencies
            from core.memory.memory_manager import MemoryManager
            
            # Create and return the memory manager
            memory_manager = MemoryManager(
                config=config,
                logger=logger
            )
            
            if logger:
                logger.info("✅ Memory Manager created successfully")
                
            return memory_manager
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create Memory Manager: {e}")
            return None 