import sys
import os
import logging
from typing import Optional, Dict

from PyQt5.QtWidgets import QApplication

from chat_mate.core.ChatManager import ChatManager
from chat_mate.core.AletheiaPromptManager import AletheiaPromptManager
from chat_mate.core.services.discord.DiscordManager import DiscordManager
from chat_mate.core.ReinforcementEngine import ReinforcementEngine
from chat_mate.core.CycleExecutionService import CycleExecutionService
from chat_mate.core.PromptResponseHandler import PromptResponseHandler
from chat_mate.core.services.discord.DiscordQueueProcessor import DiscordQueueProcessor
from chat_mate.core.TaskOrchestrator import TaskOrchestrator
from chat_mate.interfaces.pyqt.tabs.dreamscape_generation.DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator

# Import services
from chat_mate.core.services.prompt_execution_service import PromptService
from chat_mate.core.services.discord_service import DiscordService

# Import community components
from chat_mate.core.social.community_integration import CommunityIntegrationManager

# Import the main window from the correct module
from chat_mate.interfaces.pyqt.dream_os_window.main_window import DreamOsMainWindow
from chat_mate.interfaces.pyqt.dreamscape_ui_logic import DreamscapeUILogic
from chat_mate.interfaces.pyqt.dreamscape_services import DreamscapeService

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def initialize_services() -> Dict:
    """
    Initialize and return a dictionary of service instances.
    
    Returns:
        Dict: Dictionary containing initialized service instances
    """
    services = {}
    
    try:
        # Initialize prompt manager
        services['prompt_manager'] = AletheiaPromptManager()
        services['prompt_service'] = PromptService(services['prompt_manager'])
        
        # Initialize chat manager
        services['chat_manager'] = ChatManager(headless=False)
        
        # Initialize Discord service
        services['discord_service'] = DiscordService()
        
        # Initialize config manager
        services['config_manager'] = services['prompt_manager']  # They share the same config for now
        
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
    
    return services

def initialize_community_manager():
    """
    Initialize and return the community integration manager.
    
    Returns:
        CommunityIntegrationManager or None: Initialized community manager or None if initialization fails
    """
    try:
        return CommunityIntegrationManager()
    except Exception as e:
        logger.error(f"Error initializing community manager: {e}")
        return None

def main():
    """
    Main entry point for the Dreamscape GUI application.
    Initializes services, UI logic, and launches the main window.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create application
    app = QApplication(sys.argv)
    
    # Initialize services
    services = initialize_services()
    community_manager = initialize_community_manager()
    
    # Initialize UI logic
    dreamscape_service = DreamscapeService()
    ui_logic = DreamscapeUILogic()
    ui_logic.service = dreamscape_service
    
    # Create main window
    window = DreamOsMainWindow(
        ui_logic=ui_logic,
        services=services,
        community_manager=community_manager
    )
    window.show()
    
    # Start event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
