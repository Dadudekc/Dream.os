from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class IPromptManager(ABC):
    """
    Interface for prompt management services.
    Defines standard methods for prompt retrieval, storage and memory management.
    """
    
    @abstractmethod
    def get_prompt(self, prompt_type: str, cycle_id: str = None) -> str:
        """
        Retrieve and render a prompt for a given type.
        
        Args:
            prompt_type: The type/name of the prompt to retrieve
            cycle_id: Optional ID to associate with a conversation cycle
            
        Returns:
            The rendered prompt text
        """
        pass
        
    @abstractmethod
    def list_available_prompts(self) -> List[str]:
        """
        List all available prompt templates.
        
        Returns:
            List of prompt type names
        """
        pass
        
    @abstractmethod
    def load_memory_state(self) -> None:
        """Load memory state from persistent storage."""
        pass
        
    @abstractmethod
    def save_memory_state(self) -> None:
        """Save memory state to persistent storage."""
        pass
        
    @abstractmethod
    def record_conversation(self, cycle_id: str, prompt_type: str, response: str) -> str:
        """
        Record a conversation and return its ID.
        
        Args:
            cycle_id: The ID of the current conversation cycle
            prompt_type: The type of prompt that was executed
            response: The response received
            
        Returns:
            The ID of the recorded conversation
        """
        pass
        
    @abstractmethod
    def start_conversation_cycle(self, cycle_type: str) -> str:
        """
        Start a new conversation cycle.
        
        Args:
            cycle_type: The type of cycle to start
            
        Returns:
            The ID of the new cycle
        """
        pass
        
    @abstractmethod
    def end_conversation_cycle(self, cycle_id: str) -> None:
        """
        End a conversation cycle and update memory.
        
        Args:
            cycle_id: The ID of the cycle to end
        """
        pass 
