#!/usr/bin/env python3
"""
Main entry point for the PyQT interface.

This allows running the application with:
    python -m interfaces.pyqt
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication

from interfaces.pyqt.dreamscape_gui import (
    initialize_services,
    initialize_community_manager,
    DreamscapeMainWindow,
    DreamscapeUILogic,
    DreamscapeService
)

from config.ConfigManager import ConfigManager
from core.logging.factories.LoggerFactory import LoggerFactory
from core.micro_factories.chat_factory import create_chat_manager

def main():
    """
    Main function that initializes and runs the application.
    Can be called both from __main__ and as an entry point.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    app = QApplication(sys.argv)

    # Initialize Config & Logger
    config_manager = ConfigManager()
    logger = LoggerFactory.create_standard_logger("Dreamscape", level=logging.INFO)
    config_manager.set_logger(logger)

    # Initialize services and inject chat_manager
    services = initialize_services()
    services['config_manager'] = config_manager
    services['logger'] = logger
    services['chat_manager'] = create_chat_manager(config_manager, logger=logger)

    # Initialize community manager (optional)
    community_manager = initialize_community_manager()

    # UI logic and service binding
    dreamscape_service = DreamscapeService()
    ui_logic = DreamscapeUILogic()
    ui_logic.service = dreamscape_service

    # Create and show main window
    window = DreamscapeMainWindow(
        ui_logic=ui_logic,
        services=services,
        community_manager=community_manager
    )
    window.show()

    # Run event loop
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())
