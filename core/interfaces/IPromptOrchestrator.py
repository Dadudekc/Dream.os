from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from core.IChatManager import IChatManager

class IPromptOrchestrator(ABC):
    """
    Interface for prompt cycle orchestration services.
    Defines standard methods for executing prompt cycles and managing prompts.
    """
    
    @abstractmethod
    def set_chat_manager(self, chat_manager: IChatManager) -> None:
        """
        Set or update the chat manager instance.
        
        Args:
            chat_manager: Chat manager implementation
        """
        pass
        
    @abstractmethod
    def execute_single_cycle(self, prompt_text: str, new_chat: bool = False) -> List[str]:
        """
        Execute a single prompt cycle.
        
        Args:
            prompt_text: The prompt text to execute
            new_chat: Whether to create a new chat for this cycle
            
        Returns:
            List of responses
        """
        pass
        
    @abstractmethod
    def execute_multi_cycle(self, prompts: List[str], reverse_order: bool = False) -> Dict[str, List[str]]:
        """
        Execute multiple prompts across multiple chats.
        
        Args:
            prompts: List of prompts to execute
            reverse_order: Whether to execute in reverse order
            
        Returns:
            Dictionary mapping chat titles to their responses
        """
        pass
        
    @abstractmethod
    def get_available_prompts(self) -> List[str]:
        """
        Get list of available prompts.
        
        Returns:
            List of prompt types
        """
        pass
        
    @abstractmethod
    def get_prompt(self, prompt_type: str) -> Optional[str]:
        """
        Get a specific prompt by type.
        
        Args:
            prompt_type: The type of prompt to retrieve
            
        Returns:
            The prompt text or None if not found
        """
        pass
        
    @abstractmethod
    def save_prompt(self, prompt_type: str, prompt_text: str) -> bool:
        """
        Save a prompt.
        
        Args:
            prompt_type: The type of prompt
            prompt_text: The prompt text to save
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    def shutdown(self) -> None:
        """Clean up resources and shut down components."""
        pass 