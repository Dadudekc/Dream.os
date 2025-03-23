#!/usr/bin/env python3
"""
Main entry point for the PyQT interface.

This allows running the application with:
    python -m interfaces.pyqt
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication

from interfaces.pyqt.dreamscape_gui import initialize_services, initialize_community_manager, DreamscapeMainWindow, DreamscapeUILogic, DreamscapeService

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
    window = DreamscapeMainWindow(
        ui_logic=ui_logic,
        services=services,
        community_manager=community_manager
    )
    window.show()
    
    # Start event loop
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main()) 