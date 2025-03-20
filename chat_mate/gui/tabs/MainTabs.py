from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from gui.tabs.PromptExecutionTab import PromptExecutionTab
from gui.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
from gui.tabs.ConfigurationTab import ConfigurationTab
from gui.tabs.LogsTab import LogsTab

class MainTabs(QWidget):
    """
    MainTabs class manages the full tab layout of the Dreamscape application.
    """

    def __init__(self, ui_logic):
        super().__init__()
        self.ui_logic = ui_logic
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Create the QTabWidget that holds all the tabs
        self.tab_widget = QTabWidget()

        # Initialize and add each tab
        self.prompt_execution_tab = PromptExecutionTab(self.ui_logic)
        self.dreamscape_generation_tab = DreamscapeGenerationTab(self.ui_logic)
        self.configuration_tab = ConfigurationTab(self.ui_logic)
        self.logs_tab = LogsTab()

        self.tab_widget.addTab(self.prompt_execution_tab, "Prompt Execution")
        self.tab_widget.addTab(self.dreamscape_generation_tab, "Dreamscape Generation")
        self.tab_widget.addTab(self.configuration_tab, "Configuration & Discord")
        self.tab_widget.addTab(self.logs_tab, "Logs & Dashboard")

        # Add tab widget to the main layout
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def append_output(self, message: str):
        """
        Sends output to the Logs tab or other active tab as needed.
        """
        if hasattr(self.logs_tab, 'append_output'):
            self.logs_tab.append_output(message)
