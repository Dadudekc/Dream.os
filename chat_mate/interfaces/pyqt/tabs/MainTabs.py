from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from interfaces.pyqt.tabs.PromptExecutionTab import PromptExecutionTab
from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
from interfaces.pyqt.tabs.ConfigurationTab import ConfigurationTab
from interfaces.pyqt.tabs.LogsTab import LogsTab

class MainTabs(QWidget):
    """
    Manages the full tab layout of the Dreamscape application.
    Provides access to core services across all tabs.
    """

    def __init__(self, ui_logic=None, prompt_manager=None, config_manager=None, logger=None, 
                 discord_manager=None, memory_manager=None, chat_manager=None, **kwargs):
        """
        Initialize the main tabs container.

        Args:
            ui_logic: Core UI logic/controller object.
            prompt_manager: Manages prompt templates and execution.
            config_manager: Manages configuration settings.
            logger: Logging instance for consistent output across tabs.
            discord_manager: Manages Discord-related tasks.
            memory_manager: Manages memory-related tasks.
            chat_manager: Manages chat interactions.
            kwargs: Additional dependencies to pass to individual tabs.
        """
        super().__init__()

        self.ui_logic = ui_logic
        self.prompt_manager = prompt_manager
        self.config_manager = config_manager
        self.logger = logger
        self.discord_manager = discord_manager
        self.memory_manager = memory_manager
        self.chat_manager = chat_manager
        self.extra_dependencies = kwargs  # Any other services

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        # Create the tab container widget
        self.tab_widget = QTabWidget()

        # Initialize and register each tab (future-proofed for scaling)
        self.tabs = {}

        # Prompt Execution Tab
        self._register_tab(
            "Prompt Execution",
            PromptExecutionTab(
                prompt_manager=self.prompt_manager,
                config_manager=self.config_manager,
                logger=self.logger,
                chat_manager=self.chat_manager,
                memory_manager=self.memory_manager,
                discord_manager=self.discord_manager,
                **self.extra_dependencies
            )
        )

        # Dreamscape Generation Tab
        dreamscape_tab_kwargs = {}
        if self.ui_logic:  # Support both initialization styles
            dreamscape_tab_kwargs['ui_logic'] = self.ui_logic
            dreamscape_tab_kwargs['config_manager'] = self.config_manager
            dreamscape_tab_kwargs['logger'] = self.logger
        else:
            dreamscape_tab_kwargs['prompt_manager'] = self.prompt_manager
            dreamscape_tab_kwargs['chat_manager'] = self.chat_manager
            dreamscape_tab_kwargs['response_handler'] = self.extra_dependencies.get('response_handler')
            dreamscape_tab_kwargs['memory_manager'] = self.memory_manager
            dreamscape_tab_kwargs['discord_manager'] = self.discord_manager
            
        self._register_tab(
            "Dreamscape Generation",
            DreamscapeGenerationTab(**dreamscape_tab_kwargs)
        )

        # Configuration Tab
        self._register_tab(
            "Configuration & Discord",
            ConfigurationTab(
                ui_logic=self.ui_logic,
                config_manager=self.config_manager,
                logger=self.logger
            )
        )

        # Logs Tab
        self._register_tab(
            "Logs",
            LogsTab(logger=self.logger)
        )

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def _register_tab(self, name: str, tab_widget: QWidget):
        """
        Registers and adds a tab to the tab widget.

        Args:
            name (str): The tab label.
            tab_widget (QWidget): The tab's widget.
        """
        self.tab_widget.addTab(tab_widget, name)
        self.tabs[name] = tab_widget

    def append_output(self, message: str):
        """
        Sends output to the Logs tab or any other log handler tabs.

        Args:
            message (str): The message to append.
        """
        logs_tab = self.tabs.get("Logs")
        if logs_tab and hasattr(logs_tab, "append_output"):
            logs_tab.append_output(message)
        elif logs_tab and hasattr(logs_tab, "append_log"):
            logs_tab.append_log(message)
        elif self.logger:
            self.logger.info(message)
