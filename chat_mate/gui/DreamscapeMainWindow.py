import sys
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QAction, QMessageBox, QApplication, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QTextEdit, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QFont, QIcon

from gui.tabs.MainTabs import MainTabs
from gui.components.dialogs.exclusions_dialog import ExclusionsDialog
from gui.components.dialogs.discord_settings import DiscordSettingsDialog
from gui.components.dialogs.reinforcement_dialog import ReinforcementToolsDialog
from gui.dreamscape_ui_logic import DreamscapeUILogic
from gui.tabs.PromptExecutionTab import PromptExecutionTab
from gui.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
from gui.tabs.ConfigurationTab import ConfigurationTab
from gui.tabs.LogsTab import LogsTab


class DreamscapeGUI(QWidget):
    append_output_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Dreamscape Automation")
        self.setGeometry(100, 100, 1000, 800)
        self.initUI()

    def initUI(self):
        self.tabs = QTabWidget()

        # Instantiate Tabs
        self.prompt_execution_tab = PromptExecutionTab(self)
        self.dreamscape_generation_tab = DreamscapeGenerationTab(self, "chat_manager=", "response_handler")
        self.configuration_tab = ConfigurationTab(self)
        self.logs_tab = LogsTab(self)

        # Add Tabs
        self.tabs.addTab(self.prompt_execution_tab, "Prompt Execution")
        self.tabs.addTab(self.dreamscape_generation_tab, "Dreamscape Generation")
        self.tabs.addTab(self.configuration_tab, "Configuration & Discord")
        self.tabs.addTab(self.logs_tab, "Logs")

        # Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

        # Connect signals
        self.append_output_signal.connect(self.logs_tab.append_log)


class DreamscapeMainWindow(QMainWindow):
    """
    Main window for the Dreamscape application.
    Provides a modern, user-friendly interface for interacting with the application.
    """

    # --- Define signals for UI updates ---
    append_output_signal = pyqtSignal(str)
    append_discord_log_signal = pyqtSignal(str)
    status_update_signal = pyqtSignal(str)

    def __init__(self, ui_logic: DreamscapeUILogic):
        """
        Initialize the main window.
        
        :param ui_logic: The UI logic instance that handles backend interactions
        """
        super().__init__()
        self.ui_logic = ui_logic
        self.logger = logging.getLogger(__name__)
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Set up the user interface components."""
        self.setWindowTitle("Dreamscape")
        self.setMinimumSize(800, 600)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Add tabs
        tabs.addTab(self.create_prompt_tab(), "Prompts")
        tabs.addTab(self.create_settings_tab(), "Settings")
        tabs.addTab(self.create_status_tab(), "Status")

    def create_prompt_tab(self):
        """Create the prompts tab with input and output areas."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Prompt input area
        input_group = QGroupBox("Prompt Input")
        input_layout = QVBoxLayout()
        
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Enter your prompt here...")
        input_layout.addWidget(self.prompt_input)

        # Prompt type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Prompt Type:"))
        self.prompt_type = QComboBox()
        self.prompt_type.addItems(["General", "Creative", "Technical"])
        type_layout.addWidget(self.prompt_type)
        input_layout.addLayout(type_layout)

        # Execute button
        self.execute_button = QPushButton("Execute Prompt")
        input_layout.addWidget(self.execute_button)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Output area
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        output_layout.addWidget(self.output_display)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        return tab

    def create_settings_tab(self):
        """Create the settings tab with configuration options."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # General settings
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout()
        
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(1, 4000)
        self.max_tokens.setValue(1000)
        general_layout.addRow("Max Tokens:", self.max_tokens)
        
        self.temperature = QSpinBox()
        self.temperature.setRange(0, 100)
        self.temperature.setValue(70)
        general_layout.addRow("Temperature:", self.temperature)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Save/Reset buttons
        button_layout = QHBoxLayout()
        self.save_settings_button = QPushButton("Save Settings")
        self.reset_settings_button = QPushButton("Reset to Defaults")
        button_layout.addWidget(self.save_settings_button)
        button_layout.addWidget(self.reset_settings_button)
        layout.addLayout(button_layout)

        return tab

    def create_status_tab(self):
        """Create the status tab showing application state."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Status display
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        layout.addWidget(self.status_display)

        # Refresh button
        self.refresh_status = QPushButton("Refresh Status")
        layout.addWidget(self.refresh_status)

        return tab

    def setup_connections(self):
        """Set up signal connections for UI elements."""
        # Connect buttons to their handlers
        self.execute_button.clicked.connect(self.execute_prompt)
        self.save_settings_button.clicked.connect(self.save_settings_handler)
        self.reset_settings_button.clicked.connect(self.reset_settings_handler)
        self.refresh_status.clicked.connect(self.update_status)

        # Connect UI logic callbacks
        self.ui_logic.set_output_signal(self.append_output)
        self.ui_logic.set_status_update_signal(self.update_status)
        self.ui_logic.set_discord_log_signal(self.append_discord_log)

    def execute_prompt(self):
        """Execute the current prompt and display results."""
        prompt_text = self.prompt_input.toPlainText()
        if not prompt_text:
            QMessageBox.warning(self, "Warning", "Please enter a prompt first.")
            return

        self.execute_button.setEnabled(False)
        self.append_output("Executing prompt...")
        
        # Execute prompt in a separate thread
        responses = self.ui_logic.execute_prompt(prompt_text)
        
        # Display results
        for response in responses:
            self.append_output(f"\nResponse:\n{response}")
        
        self.execute_button.setEnabled(True)

    def save_settings_handler(self):
        """Handle saving settings."""
        try:
            # Example: Retrieve settings from UI elements (assumed to be defined in your configuration tab)
            excluded_chats = self.excluded_chats_text.toPlainText().split('\n') if hasattr(self, 'excluded_chats_text') else []
            model = self.model_combo.currentText() if hasattr(self, 'model_combo') else "General"
            headless = self.headless_check.isChecked() if hasattr(self, 'headless_check') else False
            
            # Initialize chat manager with new settings through UI logic service
            self.ui_logic.service.initialize_chat_manager(excluded_chats, model, headless)
            
            # Show success message
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def reset_settings_handler(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self, "Confirm Reset",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.ui_logic.reset_prompts()
                QMessageBox.information(self, "Success", "Settings reset to defaults.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset settings: {str(e)}")

    def update_status(self, message=None):
        """Update the status display."""
        if message:
            self.status_display.append(message)
        else:
            # Refresh status from services
            status = "Application Status:\n"
            if self.ui_logic.is_service_available('prompt_manager'):
                status += "✓ Prompt Manager: Active\n"
            else:
                status += "✗ Prompt Manager: Not Available\n"
            self.status_display.setText(status)

    def append_output(self, message):
        """Append a message to the output display."""
        self.output_display.append(message)
        # Auto-scroll to bottom
        self.output_display.verticalScrollBar().setValue(
            self.output_display.verticalScrollBar().maximum()
        )

    def append_discord_log(self, message):
        """Append a Discord log message to the output display."""
        self.append_output(f"[Discord] {message}")


# -------------------------------------------------------------------------
# Entry point for testing standalone run
# -------------------------------------------------------------------------
if __name__ == "__main__":
    from gui.dreamscape_services import DreamscapeService

    app = QApplication(sys.argv)

    def ui_output(msg):
        print(f"[UI OUTPUT]: {msg}")

    service = DreamscapeService()
    ui_logic = DreamscapeUILogic(output_callback=ui_output)

    window = DreamscapeMainWindow(ui_logic)
    window.show()

    sys.exit(app.exec_())
