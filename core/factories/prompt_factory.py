"""
Factory for creating PromptManager instances.
Using a factory pattern to handle the creation of PromptManager implementations
and resolve circular dependencies.
"""
from typing import Optional, Any
from pathlib import Path
from core.config.config_manager import ConfigManager
from core.PathManager import PathManager

class PromptFactory:
    """Factory for creating PromptManager instances."""
    
    @staticmethod
    def create(registry):
        """
        Create and return a configured PromptManager instance from a service registry.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured PromptManager instance
        """
        # Extract dependencies from registry
        config_manager = registry.get("config_manager")
        logger = registry.get("logger")
        
        # Get required paths using PathManager
        try:
            path_manager = PathManager()
            memory_path = str(path_manager.get_memory_path("prompt_memory.json"))
            template_path = str(path_manager.get_template_path())
            conversation_memory_path = str(path_manager.get_memory_path("conversation_memory.json"))
            cycle_memory_path = str(path_manager.get_memory_path("cycle_memory.json"))
            
            # Log path resolution
            if logger:
                logger.info(f"Resolved paths from PathManager:")
                logger.info(f"  - memory_path: {memory_path}")
                logger.info(f"  - template_path: {template_path}")
                logger.info(f"  - conversation_memory_path: {conversation_memory_path}")
                logger.info(f"  - cycle_memory_path: {cycle_memory_path}")
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ Error getting paths from PathManager: {e}")
            memory_path = "memory/prompt_memory.json"
            template_path = "templates"
            conversation_memory_path = "memory/conversation_memory.json" 
            cycle_memory_path = "memory/cycle_memory.json"
        
        # Create and return the prompt manager
        try:
            # Import here to avoid circular dependencies
            from core.AletheiaPromptManager import AletheiaPromptManager
            
            prompt_manager = AletheiaPromptManager(
                memory_file=memory_path,  # Already a string from above
                template_path=template_path,  # Already a string from above
                conversation_memory_file=conversation_memory_path,  # Already a string from above
                cycle_memory_file=cycle_memory_path  # Already a string from above
            )
            
            if logger:
                logger.info("✅ PromptManager created successfully via factory")
                
            return prompt_manager
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create PromptManager: {e}")
            return None

    @classmethod
    def create_prompt_manager(cls, **kwargs):
        """
        Create a prompt manager instance.
        
        Args:
            **kwargs: Optional arguments to pass to the prompt manager
            
        Returns:
            An instance of AletheiaPromptManager
        """
        # Import here to avoid circular dependencies
        from core.AletheiaPromptManager import AletheiaPromptManager
        
        # Get required paths using PathManager
        try:
            path_manager = PathManager()
            memory_path = str(path_manager.get_memory_path("prompt_memory.json"))
            template_path = str(path_manager.get_template_path())
            conversation_memory_path = str(path_manager.get_memory_path("conversation_memory.json"))
            cycle_memory_path = str(path_manager.get_memory_path("cycle_memory.json"))
        except Exception:
            memory_path = "memory/prompt_memory.json"
            template_path = "templates"
            conversation_memory_path = "memory/conversation_memory.json" 
            cycle_memory_path = "memory/cycle_memory.json"
        
        # Create and return the prompt manager
        return AletheiaPromptManager(
            memory_file=memory_path,
            template_path=template_path,
            conversation_memory_file=conversation_memory_path,
            cycle_memory_file=cycle_memory_path,
            **kwargs
        ) 
