"""
Factory for creating PromptManager instances.
Using a factory pattern to handle the creation of PromptManager implementations
and resolve circular dependencies.
"""
from typing import Optional
from core.interfaces.IPromptManager import IPromptManager

class PromptFactory:
    """Factory for creating PromptManager instances."""
    
    @staticmethod
    def create_prompt_manager(
        memory_file: Optional[str] = None,
        template_path: Optional[str] = None,
        conversation_memory_file: Optional[str] = None,
        cycle_memory_file: Optional[str] = None
    ) -> IPromptManager:
        """
        Create and return a configured PromptManager instance.
        
        Args:
            memory_file: Path to the memory file
            template_path: Path to the templates directory
            conversation_memory_file: Path to the conversation memory file
            cycle_memory_file: Path to the cycle memory file
            
        Returns:
            An instance of a class implementing IPromptManager
        """
        # Import here to avoid circular dependencies
        from core.AletheiaPromptManager import AletheiaPromptManager
        
        # Create and return the prompt manager
        return AletheiaPromptManager(
            memory_file=memory_file,
            template_path=template_path,
            conversation_memory_file=conversation_memory_file,
            cycle_memory_file=cycle_memory_file
        ) 