# core/micro_factories/chat_factory.py
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class ChatFactory:
    """Micro-factory for creating chat service instances."""
    
    @staticmethod
    def create() -> Any:
        """
        Create and return a chat service instance with
        dependencies injected from the service registry.
        
        Returns:
            A chat service instance
        """
        try:
            # Import here to avoid circular dependencies
            from core.services.service_registry import ServiceRegistry
            from core.ChatManager import ChatManager
            
            # Get dependencies from registry
            config_manager = ServiceRegistry.get("config_manager")
            prompt_manager = ServiceRegistry.get("prompt_manager")
            
            # Create the instance
            chat_service = ChatManager(
                prompt_manager=prompt_manager,
                config=config_manager
            )
            
            logger.info("✅ ChatManager created successfully via factory")
            return chat_service
            
        except Exception as e:
            logger.error(f"❌ Failed to create ChatManager: {e}")
            return None
            
    @staticmethod
    def create_with_explicit_deps(prompt_manager=None, config_manager=None) -> Any:
        """
        Create and return a chat service instance with explicitly provided dependencies.
        
        Args:
            prompt_manager: PromptManager instance
            config_manager: Configuration manager instance
            
        Returns:
            A chat service instance
        """
        try:
            if not prompt_manager or not config_manager:
                logger.error("❌ Missing required dependencies for ChatManager")
                return None
                
            # Import here to avoid circular dependencies
            from core.ChatManager import ChatManager
            
            # Create the instance
            chat_service = ChatManager(
                prompt_manager=prompt_manager,
                config=config_manager
            )
            
            logger.info("✅ ChatManager created successfully with explicit dependencies")
            return chat_service
            
        except Exception as e:
            logger.error(f"❌ Failed to create ChatManager with explicit dependencies: {e}")
            return None
