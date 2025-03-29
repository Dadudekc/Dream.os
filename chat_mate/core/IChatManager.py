from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class IChatManager(ABC):
    """Interface for Chat Manager implementations with orchestration capabilities."""

    @abstractmethod
    def start(self):
        """Start the chat manager and all underlying services."""
        pass

    @abstractmethod
    def send_prompt(self, prompt: str) -> str:
        """
        Send a prompt and return the response.

        Args:
            prompt (str): The prompt text.
            
        Returns:
            str: The response received.
        """
        pass

    @abstractmethod
    def get_all_chat_titles(self) -> List[Dict[str, Any]]:
        """Return a list of all available chat titles."""
        pass

    @abstractmethod
    def execute_prompts_single_chat(self, prompts: List[str], cycle_speed: int, interaction_id: Optional[str] = None) -> List[str]:
        """
        Execute multiple prompts in a single chat session.
        
        Args:
            prompts (List[str]): List of prompt texts.
            cycle_speed (int): Speed for cycling through prompts.
            interaction_id (Optional[str]): Optional interaction ID.
            
        Returns:
            List[str]: List of responses.
        """
        pass

    @abstractmethod
    def analyze_execution_response(self, response: str, prompt_text: str) -> Dict[str, Any]:
        """
        Analyze the response from a prompt execution.
        
        Args:
            response (str): The response text.
            prompt_text (str): The original prompt.
            
        Returns:
            Dict[str, Any]: Analysis summary.
        """
        pass

    @abstractmethod
    def shutdown_driver(self) -> None:
        """Shutdown all services and cleanly close the driver."""
        pass

    @abstractmethod
    def send_chat_prompt(self, task: str, context: Optional[Dict] = None) -> Optional[str]:
        """
        Generate and send a prompt.
        
        Args:
            task (str): Task description.
            context (Optional[Dict]): Additional context.
            
        Returns:
            Optional[str]: Generated code or None on error.
        """
        pass

    @abstractmethod
    def execute_prompt_cycle(self, prompt: str) -> str:
        """
        Execute a complete prompt cycle.
        
        Args:
            prompt (str): The prompt to execute.
            
        Returns:
            str: The response.
        """
        pass

    # 🧠 NEW: Multi-Agent Orchestration Enhancements

    @abstractmethod
    def queue_prompts(self, prompts: List[str]) -> None:
        """
        Queue multiple prompts for sequential execution.
        
        Used by CursorPromptQueueAgent or autonomous batch orchestration.
        """
        pass

    @abstractmethod
    def get_last_response(self) -> Optional[str]:
        """
        Get the last received prompt response (post-analysis).
        
        Useful for feedback, audit, or state syncing.
        """
        pass

    @abstractmethod
    def inject_context(self, context: Dict[str, Any]) -> None:
        """
        Inject external context (e.g. dreamscape metadata, memory snapshots) into the next prompt.
        
        Enables tighter integration with other services.
        """
        pass
