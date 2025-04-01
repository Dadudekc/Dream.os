"""
Configuration Tab Module

This module provides the configuration and settings interface for Dream.OS.
"""

import logging
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QHBoxLayout,
    QFrame, QScrollArea, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

try:
    from ..components.dialogs.exclusions_dialog import ExclusionsDialog
    from ..components.dialogs.discord_settings import DiscordSettingsDialog
    from ..components.dialogs.reinforcement_dialog import ReinforcementToolsDialog
    DIALOGS_AVAILABLE = True
except ImportError:
    DIALOGS_AVAILABLE = False

class ConfigurationTab(QWidget):
    """
    Configuration & Discord Settings tab.
    Manages dialogs for exclusions, Discord setup, and reinforcement tools.
    """
    # Signals
    config_updated = pyqtSignal(str, dict)  # section, updated_config
    log_message = pyqtSignal(str)
    
    def __init__(
        self,
        config_manager=None,
        dispatcher=None,
        service=None,
        command_handler=None,
        logger=None,
        parent=None
    ):
        super().__init__(parent)
        self.config_manager = config_manager
        self.dispatcher = dispatcher
        self.service = service
        self.command_handler = command_handler
        self.logger = logger or logging.getLogger(__name__)
        self.parent = parent

        self.initUI()
        
    def initUI(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Add header
        header = QLabel("Configuration")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        if DIALOGS_AVAILABLE:
            # Section: Exclusions Manager
            exclusions_group = self._create_section_group(
                "Exclusions Manager",
                "Manage prompt exclusions and filters.",
                "Open Exclusions Manager",
                self.open_exclusions_dialog
            )
            scroll_layout.addWidget(exclusions_group)
            scroll_layout.addSpacing(20)

            # Section: Discord Settings
            discord_group = self._create_section_group(
                "Discord Settings",
                "Configure Discord Bot and Channel Settings.",
                "Open Discord Settings",
                self.open_discord_settings_dialog
            )
            scroll_layout.addWidget(discord_group)
            scroll_layout.addSpacing(20)

            # Section: Reinforcement Tools
            reinforcement_group = self._create_section_group(
                "Reinforcement Tools",
                "Reinforcement Learning Tools.",
                "Open Reinforcement Tools",
                self.open_reinforcement_tools_dialog
            )
            scroll_layout.addWidget(reinforcement_group)
        else:
            # Show message about missing dialogs
            message = QLabel(
                "Configuration dialogs are not available.\n"
                "Please ensure all required modules are installed."
            )
            message.setStyleSheet("font-size: 16px; color: #666;")
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll_layout.addWidget(message)
            
            retry_button = QPushButton("Retry Loading Dialogs")
            retry_button.clicked.connect(self._retry_loading_dialogs)
            scroll_layout.addWidget(retry_button)

        # Add stretch at the bottom
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        
    def _create_section_group(self, title: str, description: str, button_text: str, button_slot) -> QGroupBox:
        """Create a section group with title, description, and button."""
        group = QGroupBox(title)
        layout = QVBoxLayout()
        
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        
        button = QPushButton(button_text)
        button.clicked.connect(button_slot)
        button.setMinimumHeight(30)
        layout.addWidget(button)
        
        group.setLayout(layout)
        return group

    @pyqtSlot()
    def open_exclusions_dialog(self) -> None:
        """Open the exclusions manager dialog."""
        try:
            dialog = ExclusionsDialog(self)
            if dialog.exec():
                self.log_action("Updated exclusions settings.")
            else:
                self.log_action("Cancelled exclusions update.")
        except Exception as e:
            self.logger.error(f"Failed to open exclusions dialog: {e}")
            self._show_error("Dialog Error", f"Failed to open exclusions dialog: {e}")

    @pyqtSlot()
    def open_discord_settings_dialog(self) -> None:
        """Open the Discord settings dialog."""
        try:
            dialog = DiscordSettingsDialog(self)
            if dialog.exec():
                self.log_action("Updated Discord settings.")
            else:
                self.log_action("Cancelled Discord settings update.")
        except Exception as e:
            self.logger.error(f"Failed to open Discord settings dialog: {e}")
            self._show_error("Dialog Error", f"Failed to open Discord settings dialog: {e}")

    @pyqtSlot()
    def open_reinforcement_tools_dialog(self) -> None:
        """Open the reinforcement tools dialog."""
        try:
            ui_logic = self.parent.ui_logic if self.parent else None
            if not ui_logic:
                raise ValueError("UI Logic not available")
                
            dialog = ReinforcementToolsDialog(ui_logic, parent=self)
            if dialog.exec():
                self.log_action("Updated reinforcement settings.")
            else:
                self.log_action("Cancelled reinforcement settings update.")
        except Exception as e:
            self.logger.error(f"Failed to open reinforcement tools dialog: {e}")
            self._show_error("Dialog Error", f"Failed to open reinforcement tools dialog: {e}")
            
    def _retry_loading_dialogs(self) -> None:
        """Attempt to reload dialog components."""
        try:
            from ..components.dialogs.exclusions_dialog import ExclusionsDialog
            from ..components.dialogs.discord_settings import DiscordSettingsDialog
            from ..components.dialogs.reinforcement_dialog import ReinforcementToolsDialog
            
            # Clear and rebuild UI
            while self.layout().count():
                child = self.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                    
            self.initUI()
            self.logger.info("Successfully reloaded configuration dialogs")
            
        except ImportError as e:
            self.logger.error(f"Failed to reload dialogs: {e}")
            self._show_error("Dialog Load Failed", f"Failed to load configuration dialogs: {e}")

    def log_action(self, message: str) -> None:
        """Log an action to both logger and UI."""
        self.logger.info(message)
        self.log_message.emit(f"[CONFIG TAB]: {message}")
        
        # Try to use parent's signal if available
        try:
            if hasattr(self.parent, 'append_output_signal'):
                self.parent.append_output_signal.emit(f"[CONFIG TAB]: {message}")
        except Exception:
            pass
            
    def _show_error(self, title: str, message: str) -> None:
        """Show an error message box."""
        QMessageBox.critical(self, title, message)

