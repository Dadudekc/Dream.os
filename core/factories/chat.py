"""
Chat Factory Module

This module provides a unified factory for creating chat-related services.
"""
from typing import Optional, Any
from . import BaseFactory, FactoryRegistry

class ChatFactory(BaseFactory):
    """Factory for creating chat-related services."""
    
    @classmethod
    def create(cls, registry: Any) -> Optional[Any]:
        """
        Create and return a configured chat service instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A configured chat service instance
        """
        try:
            # Get common dependencies
            deps = cls.get_dependencies(registry)
            logger = deps["logger"]
            config = deps["config"]
            
            # Get additional dependencies
            prompt_manager = registry.get("prompt_manager")
            openai_client = registry.get("openai_client")
            
            # Import here to avoid circular imports
            from core.chat.chat_manager import ChatManager
            
            # Create and return the chat manager
            chat_manager = ChatManager(
                prompt_manager=prompt_manager,
                config=config,
                openai_client=openai_client,
                logger=logger
            )
            
            if logger:
                logger.info("✅ Chat manager created successfully")
                
            return chat_manager
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create chat manager: {e}")
            return None

# Register the factory
FactoryRegistry.register("chat_manager", ChatFactory) 