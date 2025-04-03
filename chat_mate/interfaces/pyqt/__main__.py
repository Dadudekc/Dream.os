#!/usr/bin/env python3
"""
Main entry point for the PyQT interface.

This allows running the application with:
    python -m interfaces.pyqt
"""

# Bootstrap must be imported first to register paths
from chat_mate.core import bootstrap

import sys
import logging
from PyQt5.QtWidgets import QApplication

from chat_mate.core.config.ConfigManager import ConfigManager
from chat_mate.core.logging.factories.LoggerFactory import LoggerFactory
from chat_mate.core.micro_factories.chat_factory import create_chat_manager
from chat_mate.core.micro_factories.prompt_factory import PromptFactory
from chat_mate.interfaces.pyqt.dream_os_window.services.service_factory import ServiceFactory
from chat_mate.interfaces.pyqt.DreamOsMainWindow import DreamOsMainWindow
from chat_mate.utils.signal_dispatcher import SignalDispatcher

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

    # Create Service Factory
    service_factory = ServiceFactory(config_manager)

    # Create Prompt Manager
    try:
        prompt_manager = PromptFactory.create_prompt_manager()
        if not prompt_manager:
            logger.error("Failed to create Prompt Manager from factory.")
            sys.exit(1)
        logger.info("Prompt Manager created successfully.")
    except Exception as e:
        logger.error(f"Error creating Prompt Manager: {e}")
        sys.exit(1)

    # Create UI Logic and Services using factory
    ui_logic = service_factory.create_ui_logic()

    # Create and inject chat manager
    chat_manager = create_chat_manager(config_manager, logger=logger, prompt_manager=prompt_manager)

    # Create signal dispatcher
    dispatcher = SignalDispatcher()

    # Create main window with injected dependencies
    window = DreamOsMainWindow(
        ui_logic=ui_logic,
        services={
            'config_manager': config_manager,
            'logger': logger,
            'prompt_manager': prompt_manager,
            'chat_manager': chat_manager,
            'dispatcher': dispatcher
        }
    )
    window.show()

    # Run event loop
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())
