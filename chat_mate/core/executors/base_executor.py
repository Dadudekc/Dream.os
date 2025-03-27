from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseExecutor(ABC):
    """Base interface for prompt executors."""
    
    @abstractmethod
    async def execute(self,
                     prompt: str,
                     test_file: Optional[str] = None,
                     generate_tests: bool = False,
                     **kwargs) -> Dict[str, Any]:
        """
        Execute a prompt and return the results.
        
        Args:
            prompt: The prompt to execute
            test_file: Optional path to test file
            generate_tests: Whether to generate tests
            **kwargs: Additional executor-specific parameters
            
        Returns:
            Dict containing:
                - success: bool
                - response: str
                - error: Optional[str]
                - artifacts: Dict[str, Any]
        """
        pass
        
    @abstractmethod
    def shutdown(self):
        """Clean up resources used by the executor."""
        pass 