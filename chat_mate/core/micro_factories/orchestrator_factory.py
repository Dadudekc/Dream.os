"""
Factory for creating PromptCycleOrchestrator instances.
Using a factory pattern to handle the creation of PromptCycleOrchestrator implementations
and resolve circular dependencies.
"""
from typing import Optional, Any
from config.ConfigManager import ConfigManager
from core.IChatManager import IChatManager
from core.interfaces.IPromptOrchestrator import IPromptOrchestrator

class OrchestratorFactory:
    """Factory for creating PromptCycleOrchestrator instances."""
    
    @staticmethod
    def create_orchestrator(
        config_manager: ConfigManager,
        chat_manager: Optional[IChatManager] = None,
        prompt_service: Optional[Any] = None
    ) -> IPromptOrchestrator:
        """
        Create and return a configured PromptCycleOrchestrator instance.
        
        Args:
            config_manager: The configuration manager instance
            chat_manager: Optional chat manager implementation
            prompt_service: Optional prompt service/manager implementation
            
        Returns:
            An instance of a class implementing IPromptOrchestrator
        """
        # Import here to avoid circular dependencies
        from core.PromptCycleOrchestrator import PromptCycleOrchestrator
        
        # Create and return the orchestrator
        return PromptCycleOrchestrator(
            config_manager=config_manager,
            chat_manager=chat_manager,
            prompt_service=prompt_service
        ) 