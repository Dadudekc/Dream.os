from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QHBoxLayout
)
import logging

from interfaces.pyqt.components.dialogs.exclusions_dialog import ExclusionsDialog
from interfaces.pyqt.components.dialogs.discord_settings import DiscordSettingsDialog
from interfaces.pyqt.components.dialogs.reinforcement_dialog import ReinforcementToolsDialog

class ConfigurationTab(QWidget):
    """
    Configuration & Discord Settings tab.
    Manages dialogs for exclusions, Discord setup, and reinforcement tools.
    """
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
        self.parent = parent  # This should be DreamscapeGUI (has append_output_signal)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Section: Exclusions Manager
        exclusions_label = QLabel("Manage prompt exclusions and filters.")
        exclusions_button = QPushButton("Open Exclusions Manager")
        exclusions_button.clicked.connect(self.open_exclusions_dialog)

        # Section: Discord Settings
        discord_label = QLabel("Configure Discord Bot and Channel Settings.")
        discord_button = QPushButton("Open Discord Settings")
        discord_button.clicked.connect(self.open_discord_settings_dialog)

        # Section: Reinforcement Tools
        reinforcement_label = QLabel("Reinforcement Learning Tools.")
        reinforcement_button = QPushButton("Open Reinforcement Tools")
        reinforcement_button.clicked.connect(self.open_reinforcement_tools_dialog)

        # Layout: Exclusions
        exclusions_layout = QVBoxLayout()
        exclusions_layout.addWidget(exclusions_label)
        exclusions_layout.addWidget(exclusions_button)

        # Layout: Discord
        discord_layout = QVBoxLayout()
        discord_layout.addWidget(discord_label)
        discord_layout.addWidget(discord_button)

        # Layout: Reinforcement
        reinforcement_layout = QVBoxLayout()
        reinforcement_layout.addWidget(reinforcement_label)
        reinforcement_layout.addWidget(reinforcement_button)

        # Combine everything
        layout.addLayout(exclusions_layout)
        layout.addSpacing(20)
        layout.addLayout(discord_layout)
        layout.addSpacing(20)
        layout.addLayout(reinforcement_layout)

        # Add stretch at the bottom
        layout.addStretch()

        self.setLayout(layout)

    # ---------------------------------------
    # Dialog Openers
    # ---------------------------------------
    def open_exclusions_dialog(self):
        dialog = ExclusionsDialog(self)
        dialog.exec_()
        self.log_action("Opened Exclusions Manager.")

    def open_discord_settings_dialog(self):
        dialog = DiscordSettingsDialog(self)
        dialog.exec_()
        self.log_action("Opened Discord Settings.")

    def open_reinforcement_tools_dialog(self):
        # Needs to pass ui_logic from parent window
        try:
            ui_logic = self.parent.parent().ui_logic
        except Exception as e:
            QMessageBox.warning(self, "Error", "Unable to access UI Logic.")
            print(f"[ERROR] Failed to get ui_logic: {e}")
            return

        dialog = ReinforcementToolsDialog(ui_logic, parent=self)
        dialog.exec_()
        self.log_action("Opened Reinforcement Tools.")

    # ---------------------------------------
    # Logging Helper
    # ---------------------------------------
    def log_action(self, message: str):
        """
        Log action into LogsTab via signal (optional).
        """
        try:
            self.parent.append_output_signal.emit(f"[CONFIG TAB]: {message}")
        except Exception as e:
            print(f"[ERROR] Failed to log action: {e}")

