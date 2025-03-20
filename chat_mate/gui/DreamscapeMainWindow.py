import sys
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QAction, QMessageBox, QApplication, QWidget, QVBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal

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
        self.dreamscape_generation_tab = DreamscapeGenerationTab(self,"chat_manager=", "response_handler")
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
    Main application window, integrates UI components, tabs, and menus.
    """
    def __init__(self, ui_logic: DreamscapeUILogic):
        super().__init__()
        self.ui_logic = ui_logic

        self.setWindowTitle("Digital Dreamscape Automation")
        self.setGeometry(100, 100, 1000, 800)

        self._setup_menu()
        self._setup_tabs()

    def _setup_menu(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")

        exclusions_action = QAction("Exclusions Manager", self)
        exclusions_action.triggered.connect(self.show_exclusions_dialog)
        tools_menu.addAction(exclusions_action)

        discord_action = QAction("Discord Settings", self)
        discord_action.triggered.connect(self.open_discord_settings)
        tools_menu.addAction(discord_action)

        reinforcement_action = QAction("Reinforcement Tools", self)
        reinforcement_action.triggered.connect(self.open_reinforcement_tools)
        tools_menu.addAction(reinforcement_action)

    def _setup_tabs(self):
        self.tabs = MainTabs(self.ui_logic)
        self.setCentralWidget(self.tabs)

    # --- Menu Actions ---
    def show_exclusions_dialog(self):
        dialog = ExclusionsDialog(self)
        dialog.exec_()

    def open_discord_settings(self):
        dialog = DiscordSettingsDialog(self)
        dialog.exec_()

    def open_reinforcement_tools(self):
        dialog = ReinforcementToolsDialog(self.ui_logic, parent=self)
        dialog.exec_()

    # --- Output callback ---
    def append_output(self, message: str):
        self.tabs.append_output(message)


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
