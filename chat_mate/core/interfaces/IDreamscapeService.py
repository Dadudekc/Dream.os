from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class IDreamscapeService(ABC):
    """
    Interface for Dreamscape generation services.
    Defines standard methods for episode generation and rendering.
    """
    
    @abstractmethod
    def load_context_from_file(self, json_path: str) -> Dict[str, Any]:
        """
        Load rendering context from JSON file.
        
        Args:
            json_path: Path to the JSON context file
            
        Returns:
            Dictionary containing the loaded context
        """
        pass
        
    @abstractmethod
    def generate_context_from_memory(self) -> Dict[str, Any]:
        """
        Constructs a context dict from the injected memory structure.
        
        Returns:
            Dictionary with context generated from memory
        """
        pass
        
    @abstractmethod
    def render_episode(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a Dreamscape episode from a template and context.
        
        Args:
            template_name: Name of the template to render
            context: Dictionary of context values for rendering
            
        Returns:
            Rendered episode content
        """
        pass
        
    @abstractmethod
    def save_episode(self, name: str, content: str, format: str = "md") -> Path:
        """
        Save the rendered episode to disk.
        
        Args:
            name: Name for the episode file
            content: Content of the episode
            format: File format extension
            
        Returns:
            Path object pointing to the saved file
        """
        pass
        
    @abstractmethod
    def generate_episode_from_template(self, template_name: str, context_path: str, output_name: str) -> Optional[Path]:
        """
        Load context from JSON, render it with template, and save output.
        
        Args:
            template_name: Name of the template to use
            context_path: Path to the context JSON file
            output_name: Name for the output file
            
        Returns:
            Path to the saved episode file or None if failed
        """
        pass
        
    @abstractmethod
    def generate_episode_from_memory(self, template_name: str, output_name: Optional[str] = None) -> Optional[Path]:
        """
        Render and save an episode using memory-driven context.
        
        Args:
            template_name: Name of the template to use
            output_name: Optional name for the output file
            
        Returns:
            Path to the saved episode file or None if failed
        """
        pass 