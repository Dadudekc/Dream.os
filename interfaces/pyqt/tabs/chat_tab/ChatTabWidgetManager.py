"""Chat tab widget manager module."""

from typing import Dict, Any
from .ChatTabWidget import ChatTabWidget
from .ChatTabManager import ChatTabManager

class ChatTabWidgetManager:
    """Manager for chat tab widgets."""
    
    def __init__(self, services: Dict[str, Any]):
        """Initialize the chat tab widget manager.
        
        Args:
            services: Dictionary containing services
        """
        self.services = services
        self.tab_manager = ChatTabManager(services)
        self.tab_widget = ChatTabWidget(services)
        
    def create_new_tab(self, title: str = "New Chat"):
        """Create and add a new chat tab.
        
        Args:
            title: Tab title
        """
        tab = self.tab_manager.create_tab()
        self.tab_widget.add_tab(tab, title)
        
    def get_widget(self) -> ChatTabWidget:
        """Get the chat tab widget.
        
        Returns:
            Chat tab widget instance.
        """
        return self.tab_widget 