"""Chat tab manager module."""

from typing import Dict, Any, List
from .ChatTab import ChatTab

class ChatTabManager:
    """Manager for chat tabs."""
    
    def __init__(self, services: Dict[str, Any]):
        """Initialize the chat tab manager.
        
        Args:
            services: Dictionary containing services
        """
        self.services = services
        self.tabs: List[ChatTab] = []
        
    def create_tab(self) -> ChatTab:
        """Create a new chat tab.
        
        Returns:
            New chat tab instance.
        """
        tab = ChatTab(self.services)
        self.tabs.append(tab)
        return tab
        
    def close_tab(self, tab: ChatTab):
        """Close a chat tab.
        
        Args:
            tab: Tab to close
        """
        if tab in self.tabs:
            self.tabs.remove(tab)
            
    def get_tabs(self) -> List[ChatTab]:
        """Get list of chat tabs.
        
        Returns:
            List of chat tabs.
        """
        return self.tabs.copy() 