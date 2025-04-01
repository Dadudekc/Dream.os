"""Chat tab widget module."""

from typing import Dict, Any
from PyQt5.QtWidgets import QTabWidget
from .ChatTab import ChatTab

class ChatTabWidget(QTabWidget):
    """Widget for managing chat tabs."""
    
    def __init__(self, services: Dict[str, Any]):
        """Initialize the chat tab widget.
        
        Args:
            services: Dictionary containing services
        """
        super().__init__()
        self.services = services
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._on_tab_close)
        
    def add_tab(self, tab: ChatTab, title: str = "New Chat"):
        """Add a chat tab.
        
        Args:
            tab: Chat tab to add
            title: Tab title
        """
        self.addTab(tab, title)
        self.setCurrentWidget(tab)
        
    def _on_tab_close(self, index: int):
        """Handle tab close request.
        
        Args:
            index: Index of tab to close
        """
        widget = self.widget(index)
        self.removeTab(index)
        if widget:
            widget.deleteLater() 