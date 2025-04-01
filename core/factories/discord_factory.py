"""
Factory for creating Discord service instances.
"""
from typing import Optional, Any
from core.services.service_registry import ServiceRegistry

class DiscordFactory:
    """Factory for creating Discord service instances."""
    
    @staticmethod
    def create(registry: ServiceRegistry) -> Optional[Any]:
        """
        Create and return a configured Discord service instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured Discord service instance
        """
        try:
            # Get dependencies
            logger = registry.get("logger")
            config = registry.get("config_manager")
            
            # Import here to avoid circular dependencies
            from core.social.discord_service import UnifiedDiscordService
            
            # Create and return the discord service
            discord_service = UnifiedDiscordService(
                config=config,
                logger=logger
            )
            
            if logger:
                logger.info("✅ Discord service created successfully")
                
            return discord_service
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create Discord service: {e}")
            return None 