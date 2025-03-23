import sys
import os
import logging

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QAction, QMessageBox, QApplication, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QTextEdit, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QFont, QIcon

from interfaces.pyqt.tabs.MainTabs import MainTabs
from interfaces.pyqt.components.dialogs.exclusions_dialog import ExclusionsDialog
from interfaces.pyqt.components.dialogs.discord_settings import DiscordSettingsDialog
from interfaces.pyqt.components.dialogs.reinforcement_dialog import ReinforcementToolsDialog
from interfaces.pyqt.dreamscape_ui_logic import DreamscapeUILogic


class DreamscapeMainWindow(QMainWindow):
    """
    Main window for the Dreamscape application.
    Provides a modern, user-friendly interface for interacting with the application.
    Integrates all components including prompt management, social media
    interfaces, and community management dashboard.
    """

    # Define signals for UI updates
    append_output_signal = pyqtSignal(str)
    append_discord_log_signal = pyqtSignal(str)
    status_update_signal = pyqtSignal(str)

    def __init__(self, ui_logic: DreamscapeUILogic, services=None, community_manager=None):
        """
        Initialize the main window.
        
        :param ui_logic: The UI logic instance that handles backend interactions
        :param services: Dictionary of available services
        :param community_manager: Optional community integration manager
        """
        super().__init__()
        self.ui_logic = ui_logic
        self.services = services or {}
        self.community_manager = community_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize UI
        self.setup_ui()
        self.setup_connections()
        
        self.logger.info("DreamscapeMainWindow initialized")

    def setup_ui(self):
        """Set up the user interface components."""
        self.setWindowTitle("Dreamscape - AI-Powered Community Management")
        self.setMinimumSize(1200, 800)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create main tab container
        self.tabs = MainTabs(
            ui_logic=self.ui_logic,
            prompt_manager=self.services.get('prompt_manager'),
            config_manager=self.services.get('config_manager'),
            logger=self.logger,
            discord_manager=self.services.get('discord_service'),
            memory_manager=self.services.get('memory_manager'),
            chat_manager=self.services.get('chat_manager')
        )
        
        main_layout.addWidget(self.tabs)
        
        # Create status bar
        self.statusBar().showMessage("Ready")

    def setup_connections(self):
        """Set up signal connections for UI elements."""
        # Connect UI logic callbacks
        self.ui_logic.set_output_signal(self.append_output)
        self.ui_logic.set_status_update_signal(self.update_status)
        self.ui_logic.set_discord_log_signal(self.append_discord_log)

    def append_output(self, message):
        """Append a message to the output display."""
        self.tabs.append_output(message)

    def update_status(self, message=None):
        """Update the status display."""
        if message:
            self.statusBar().showMessage(message)
            self.tabs.append_output(f"[Status] {message}")

    def append_discord_log(self, message):
        """Append a Discord log message to the output display."""
        self.append_output(f"[Discord] {message}")
        
    def closeEvent(self, event):
        """Handle window close event."""
        # Perform cleanup tasks
        for tab_name, tab in self.tabs.tabs.items():
            if hasattr(tab, 'refresh_timer') and tab.refresh_timer:
                tab.refresh_timer.stop()
        
        # Clean up services
        if self.services:
            if 'chat_manager' in self.services:
                self.services['chat_manager'].shutdown_driver()
            if 'discord_service' in self.services:
                self.services['discord_service'].stop()
                
        # Call UI logic shutdown
        if self.ui_logic:
            self.ui_logic.shutdown()
        
        event.accept()


# -------------------------------------------------------------------------
# Entry point for testing standalone run
# -------------------------------------------------------------------------
if __name__ == "__main__":
    from dreamscape_services import DreamscapeService

    app = QApplication(sys.argv)

    def ui_output(msg):
        print(f"[UI OUTPUT]: {msg}")

    service = DreamscapeService()
    ui_logic = DreamscapeUILogic(output_callback=ui_output)
    ui_logic.service = service

    window = DreamscapeMainWindow(ui_logic)
    window.show()

    sys.exit(app.exec_())
