"""
Factory for creating PromptManager instances.
Using a factory pattern to handle the creation of PromptManager implementations
and resolve circular dependencies.
"""
from typing import Optional, Any
from pathlib import Path
from config.ConfigManager import ConfigManager
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
            memory_path = path_manager.get_memory_path("prompt_memory.json")
            template_path = path_manager.get_template_path()
            conversation_memory_path = path_manager.get_memory_path("conversation_memory.json")
            cycle_memory_path = path_manager.get_memory_path("cycle_memory.json")
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ Error getting paths from PathManager: {e}")
            memory_path = Path("memory/prompt_memory.json")
            template_path = Path("templates")
            conversation_memory_path = Path("memory/conversation_memory.json") 
            cycle_memory_path = Path("memory/cycle_memory.json")
        
        # Create and return the prompt manager
        try:
            # Import here to avoid circular dependencies
            from core.AletheiaPromptManager import AletheiaPromptManager
            
            prompt_manager = AletheiaPromptManager(
                memory_file=str(memory_path),
                template_path=str(template_path),
                conversation_memory_file=str(conversation_memory_path),
                cycle_memory_file=str(cycle_memory_path)
            )
            
            if logger:
                logger.info("✅ PromptManager created successfully via factory")
                
            return prompt_manager
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create PromptManager: {e}")
            return None

    @staticmethod
    def create_prompt_manager(
        memory_file: Optional[str] = None,
        template_path: Optional[str] = None,
        conversation_memory_file: Optional[str] = None,
        cycle_memory_file: Optional[str] = None,
        logger: Optional[Any] = None
    ):
        """
        Legacy method for backward compatibility.
        Create and return a configured PromptManager instance with explicit parameters.
        
        Args:
            memory_file: Path to the memory file
            template_path: Path to the templates directory
            conversation_memory_file: Path to the conversation memory file
            cycle_memory_file: Path to the cycle memory file
            logger: Optional logger instance
            
        Returns:
            An instance of AletheiaPromptManager
        """
        # Default paths if not provided
        try:
            path_manager = PathManager()
            if not memory_file:
                memory_file = str(path_manager.get_memory_path("prompt_memory.json"))
            if not template_path:
                template_path = str(path_manager.get_template_path())
            if not conversation_memory_file:
                conversation_memory_file = str(path_manager.get_memory_path("conversation_memory.json"))
            if not cycle_memory_file:
                cycle_memory_file = str(path_manager.get_memory_path("cycle_memory.json"))
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ Error getting paths from PathManager: {e}")
        
        # Import here to avoid circular dependencies
        from core.AletheiaPromptManager import AletheiaPromptManager
        
        # Create and return the prompt manager
        return AletheiaPromptManager(
            memory_file=memory_file,
            template_path=template_path,
            conversation_memory_file=conversation_memory_file,
            cycle_memory_file=cycle_memory_file
        ) 