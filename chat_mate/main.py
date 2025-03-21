#!/usr/bin/env python3
import sys
import logging
import os
from PyQt5.QtWidgets import QApplication

# Core Imports
from core.bootstrap import get_bootstrap_paths
from core.PathManager import PathManager
from core.AletheiaPromptManager import AletheiaPromptManager
from core.ChatManager import ChatManager
from core.UnifiedDiscordService import UnifiedDiscordService
from core.FileManager import FileManager

# GUI
from gui.dreamscape_gui import DreamscapeGUI

# Social + Community
from social.community_integration import CommunityIntegrationManager
from social.UnifiedCommunityDashboard import UnifiedCommunityDashboard

# Logging Config
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========================
# CONFIG LOADER
# ========================
def load_config():
    """Load app config. Env + paths."""
    return {
        "platforms": {
            "twitter": {
                "enabled": True,
                "api_key": os.getenv("TWITTER_API_KEY"),
                "api_secret": os.getenv("TWITTER_API_SECRET"),
                "access_token": os.getenv("TWITTER_ACCESS_TOKEN"),
                "access_token_secret": os.getenv("TWITTER_ACCESS_SECRET"),
                "feedback_file": "social/data/twitter_feedback.json"
            },
            "facebook": {
                "enabled": True,
                "page_id": os.getenv("FACEBOOK_PAGE_ID"),
                "access_token": os.getenv("FACEBOOK_ACCESS_TOKEN"),
                "feedback_file": "social/data/facebook_feedback.json"
            },
            "reddit": {
                "enabled": True,
                "client_id": os.getenv("REDDIT_CLIENT_ID"),
                "client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
                "username": os.getenv("REDDIT_USERNAME"),
                "password": os.getenv("REDDIT_PASSWORD"),
                "feedback_file": "social/data/reddit_feedback.json"
            }
        }
    }

# ========================
# SERVICES INITIALIZER
# ========================
def initialize_services():
    """Initialize core services and return as a dict."""
    logger.info("Bootstrapping paths...")
    paths = get_bootstrap_paths()
    logger.info(f"Bootstrap paths loaded: {paths}")

    # Initialize memory paths
    memory_base = os.path.join(os.path.dirname(__file__), "memory")
    os.makedirs(memory_base, exist_ok=True)

    # Managers / Services
    prompt_manager = AletheiaPromptManager(
        memory_file=os.path.join(memory_base, "persistent_memory.json")
    )

    # Start a new system cycle for this session
    system_cycle_id = prompt_manager.start_conversation_cycle("system_startup")
    logger.info(f"Started system conversation cycle: {system_cycle_id}")

    chat_manager = ChatManager(
        driver_options={
            "headless": False,
            "window_size": (1920, 1080),
            "disable_gpu": True,
            "no_sandbox": True,
            "disable_dev_shm": True
        },
        cycle_id=system_cycle_id  # Pass the cycle ID to track chat interactions
    )

    discord_service = UnifiedDiscordService()
    file_manager = FileManager()

    logger.info("Services initialized.")
    return {
        "prompt_manager": prompt_manager,
        "chat_manager": chat_manager,
        "discord_service": discord_service,
        "file_manager": file_manager,
        "system_cycle_id": system_cycle_id  # Include the cycle ID in services
    }

# ========================
# MAIN FUNCTION
# ========================
def main():
    """Main Dreamscape App Launcher."""
    try:
        logger.info("Starting Dreamscape System...")

        # Start Qt App
        app = QApplication(sys.argv)

        # Config + Services
        config = load_config()
        services = initialize_services()

        # Community Layer
        community_manager = CommunityIntegrationManager(config)
        logger.info("Community manager initialized.")

        # Launch GUI
        window = DreamscapeGUI(
            services=services,
            community_manager=community_manager
        )
        window.show()

        # Register cleanup for the conversation cycle
        app.aboutToQuit.connect(lambda: services['prompt_manager'].end_conversation_cycle(services['system_cycle_id']))

        logger.info("Event loop started.")
        return app.exec_()

    except Exception as e:
        logger.exception(f"Dreamscape Launch Error: {e}")
        return 1

# ========================
# ENTRY POINT
# ========================
if __name__ == "__main__":
    sys.exit(main())
