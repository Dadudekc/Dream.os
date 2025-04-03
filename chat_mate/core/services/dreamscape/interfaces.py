"""
Interface definitions for dreamscape services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IDreamscapeService(ABC):
    """Interface for dreamscape generation services."""

    @abstractmethod
    def generate_episode(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a dreamscape episode from a prompt."""
        pass

    @abstractmethod
    def get_generation_status(self) -> Dict[str, Any]:
        """Get the current status of episode generation."""
        pass

    @abstractmethod
    def cancel_generation(self) -> bool:
        """Cancel the current episode generation."""
        pass 