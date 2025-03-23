import sys
import os
import logging
from typing import Optional, Dict

from PyQt5.QtWidgets import QMainWindow, QTabWidget, QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

from core.ChatManager import ChatManager
from core.AletheiaPromptManager import AletheiaPromptManager
from core.DiscordManager import DiscordManager
from core.ReinforcementEngine import ReinforcementEngine
from core.CycleExecutionService import CycleExecutionService
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.TaskOrchestrator import TaskOrchestrator
from core.UnifiedDreamscapeGenerator import DreamscapeEpisodeGenerator

from .components.prompt_execution_tab import PromptExecutionTab
from .components.discord_tab import DiscordTab
from .components.logs_tab import LogsTab
from gui.components.prompt_panel import PromptPanel
from gui.components.logs_panel import LogsPanel
from gui.components.community_dashboard_tab import CommunityDashboardTab
from services.prompt_service import PromptService
from services.discord_service import DiscordService

# Import community components
from social.community_integration import CommunityIntegrationManager

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DreamscapeGUI(QMainWindow):
    """
    Main GUI window for the ChatMate application.
    
    Integrates all components including prompt management, social media
    interfaces, and community management dashboard.
    """
    
    def __init__(self, services: Dict = None, community_manager = None):
        super().__init__()
        
        # Store references to services
        self.services = services or {}
        self.community_manager = community_manager
        
        # Set up the UI
        self.init_ui()
        
        logger.info("DreamscapeGUI initialized")
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("ChatMate - AI-Powered Community Management")
        self.setMinimumSize(1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Initialize components
        self.prompt_panel = PromptPanel(self)
        
        # Initialize tabs with services
        self.prompt_execution_tab = PromptExecutionTab(
            parent=self,
            prompt_manager=self.services.get('prompt_manager'),
            chat_manager=self.services.get('chat_manager')
        )
        
        self.dreamscape_generation_tab = DreamscapeGenerationTab(
            prompt_manager=self.services.get('prompt_manager'),
            chat_manager=self.services.get('chat_manager'),
            response_handler=None,  # TODO: Add response handler if needed
            memory_manager=None,  # TODO: Add memory manager if needed
            discord_manager=self.services.get('discord_service')
        )
        
        self.discord_tab = DiscordTab(
            parent=self,
            discord_service=self.services.get('discord_service')
        )
        
        # Add community dashboard tab if community manager is available
        if self.community_manager:
            self.community_dashboard_tab = CommunityDashboardTab(
                parent=self,
                community_manager=self.community_manager
            )
            self.tabs.addTab(self.community_dashboard_tab, "Community Dashboard")
        
        # Add tabs
        self.tabs.addTab(self.prompt_panel, "Prompt Manager")
        self.tabs.addTab(self.prompt_execution_tab, "Prompt Execution")
        self.tabs.addTab(self.dreamscape_generation_tab, "Dreamscape Generation")
        self.tabs.addTab(self.discord_tab, "Discord")
        
        logger.info("DreamscapeGUI UI initialized")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Perform cleanup tasks
        if hasattr(self, 'community_dashboard_tab') and self.community_dashboard_tab:
            if hasattr(self.community_dashboard_tab, 'refresh_timer'):
                self.community_dashboard_tab.refresh_timer.stop()
        
        # Clean up services
        if self.services:
            if 'chat_manager' in self.services:
                self.services['chat_manager'].shutdown_driver()
            if 'discord_service' in self.services:
                self.services['discord_service'].stop()
        
        event.accept()

def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create main window
    window = DreamscapeGUI()
    window.show()
    
    # Start event loop
    sys.exit(app.exec_())
