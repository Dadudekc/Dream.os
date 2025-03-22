import sys
import logging
from PyQt5.QtWidgets import QApplication
from gui.DreamscapeMainWindow import DreamscapeMainWindow
from gui.dreamscape_ui_logic import DreamscapeUILogic
from services.config_service import ConfigService
from services.prompt_service import PromptService

def test_gui():
    """Test the GUI functionality."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize services
    config_service = ConfigService()
    prompt_service = PromptService(config_service)
    
    # Create UI logic
    ui_logic = DreamscapeUILogic()
    ui_logic.service = prompt_service
    
    # Create and show main window
    app = QApplication(sys.argv)
    main_window = DreamscapeMainWindow(ui_logic)
    main_window.show()
    
    # Start the event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_gui() 