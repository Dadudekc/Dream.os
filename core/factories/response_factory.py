"""
Factory for creating Response Handler instances.
"""
from typing import Optional, Any
from core.services.service_registry import ServiceRegistry

class ResponseFactory:
    """Factory for creating Response Handler instances."""
    
    @staticmethod
    def create(registry: ServiceRegistry) -> Optional[Any]:
        """
        Create and return a configured Response Handler instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured Response Handler instance
        """
        try:
            # Get dependencies
            logger = registry.get("logger")
            config = registry.get("config_manager")
            prompt_manager = registry.get("prompt_manager")
            
            # Import here to avoid circular dependencies
            from core.response.response_handler import ResponseHandler
            
            # Create and return the response handler
            response_handler = ResponseHandler(
                prompt_manager=prompt_manager,
                config=config,
                logger=logger
            )
            
            if logger:
                logger.info("✅ Response Handler created successfully")
                
            return response_handler
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create Response Handler: {e}")
            return None 