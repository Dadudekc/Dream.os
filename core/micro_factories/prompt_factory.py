"""
Factory for creating PromptManager instances.
Using a micro-factory pattern with service registry integration.
"""
import logging
from typing import Optional, Any
from core.interfaces.IPromptManager import IPromptManager

logger = logging.getLogger(__name__)

class PromptFactory:
    """Factory for creating PromptManager instances."""
    
    @staticmethod
    def create() -> Any:
        """
        Create and return a PromptManager instance with
        dependencies injected from the service registry.
        
        Returns:
            An instance of a class implementing IPromptManager
        """
        try:
            # Import here to avoid circular dependencies
            from core.services.service_registry import ServiceRegistry
            from core.AletheiaPromptManager import AletheiaPromptManager
            
            # Get dependencies from registry
            config_manager = ServiceRegistry.get("config_manager")
            path_manager = ServiceRegistry.get("path_manager")
            
            # Resolve paths from the path manager
            memory_file = path_manager.get_memory_path() / "prompt_memory.json"
            template_path = path_manager.get_template_path()
            conversation_memory_file = path_manager.get_memory_path() / "conversation_memory.json"
            cycle_memory_file = path_manager.get_memory_path() / "cycle_memory.json"
            
            # Override with config values if specified
            if config_manager:
                memory_file = config_manager.get("memory_file", str(memory_file))
                template_path = config_manager.get("template_path", str(template_path))
                conversation_memory_file = config_manager.get("conversation_memory_file", str(conversation_memory_file))
                cycle_memory_file = config_manager.get("cycle_memory_file", str(cycle_memory_file))
            
            # Create the instance
            prompt_manager = AletheiaPromptManager(
                memory_file=str(memory_file),
                template_path=str(template_path),
                conversation_memory_file=str(conversation_memory_file),
                cycle_memory_file=str(cycle_memory_file)
            )
            
            logger.info("✅ PromptManager created successfully via factory")
            return prompt_manager
            
        except Exception as e:
            logger.error(f"❌ Failed to create PromptManager: {e}")
            return None
    
    @staticmethod
    def create_prompt_manager(
        memory_file: Optional[str] = None,
        template_path: Optional[str] = None,
        conversation_memory_file: Optional[str] = None,
        cycle_memory_file: Optional[str] = None
    ) -> IPromptManager:
        """
        Create and return a configured PromptManager instance with explicit parameters.
        
        Args:
            memory_file: Path to the memory file
            template_path: Path to the templates directory
            conversation_memory_file: Path to the conversation memory file
            cycle_memory_file: Path to the cycle memory file
            
        Returns:
            An instance of a class implementing IPromptManager
        """
        try:
            # Import here to avoid circular dependencies
            from core.AletheiaPromptManager import AletheiaPromptManager
            
            # Create and return the prompt manager
            prompt_manager = AletheiaPromptManager(
                memory_file=memory_file,
                template_path=template_path,
                conversation_memory_file=conversation_memory_file,
                cycle_memory_file=cycle_memory_file
            )
            
            logger.info("✅ PromptManager created successfully with explicit parameters")
            return prompt_manager
            
        except Exception as e:
            logger.error(f"❌ Failed to create PromptManager with explicit parameters: {e}")
            return None 