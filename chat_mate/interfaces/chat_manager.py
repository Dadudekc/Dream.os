from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IChatManager(ABC):
    """Interface defining the contract for chat management implementations."""
    
    @abstractmethod
    def execute_prompts_single_chat(self, prompts: List[str], cycle_speed: int, interaction_id: Optional[str] = None) -> List[str]:
        """Execute a series of prompts in a single chat session."""
        pass

    @abstractmethod
    def shutdown_driver(self) -> None:
        """Clean up and shutdown any active driver sessions."""
        pass

    @abstractmethod
    def get_all_chat_titles(self) -> List[Dict[str, Any]]:
        """Get all available chat titles."""
        pass

    @abstractmethod
    def execute_prompt_cycle(self, prompt: str) -> str:
        """Execute a single prompt cycle."""
        pass 