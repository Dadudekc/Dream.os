from PyQt5.QtWidgets import QTabWidget
from interfaces.pyqt.tabs.PromptExecutionTab import PromptExecutionTab
from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
from interfaces.pyqt.components.discord_tab import DiscordTab
from interfaces.pyqt.tabs.LogsTab import LogsTab
from interfaces.pyqt.tabs.ConfigurationTab import ConfigurationTab
from interfaces.pyqt.tabs.SocialDashboardTab import SocialDashboardTab
from interfaces.pyqt.tabs.AIDE import AIDE
from interfaces.pyqt.tabs.meredith_tab import MeredithTab  # NEW
from interfaces.pyqt.tabs.SyncOpsTab import SyncOpsTab        # ADDED
from interfaces.pyqt.widgets.file_browser_widget import FileBrowserWidget
import logging

class MainTabs(QTabWidget):
    """
    Manages all tabs in the Dreamscape application, providing central control
    via dependency injection and a SignalDispatcher for decoupled interactions.
    
    This implementation uses a data-driven approach to initialize tabs,
    which improves readability and extensibility while retaining all original features.
    """

    def __init__(self, dispatcher=None, ui_logic=None, config_manager=None, logger=None,
                 prompt_manager=None, chat_manager=None, memory_manager=None,
                 discord_manager=None, cursor_manager=None, **extra_dependencies):
        """
        Initialize MainTabs with all required services and a SignalDispatcher.
        """
        super().__init__()
        self.dispatcher = dispatcher
        self.ui_logic = ui_logic
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger("MainTabs")
        self.prompt_manager = prompt_manager
        self.chat_manager = chat_manager
        self.memory_manager = memory_manager
        self.discord_manager = discord_manager
        self.cursor_manager = cursor_manager
        self.extra_dependencies = extra_dependencies
        
        self.init_tabs()
        self.logger.info("MainTabs initialized")

        self.tabs = {}
        self._init_tabs()
        self._connect_signals()

        self.file_browser = FileBrowserWidget()

    def init_tabs(self):
        """Initialize all tab widgets."""
        try:
            # Initialize tabs here
            pass
        except Exception as e:
            self.logger.error(f"Error initializing tabs: {e}")

    def cleanup(self):
        """Gracefully close resources used by tabs."""
        self.logger.info("Starting MainTabs cleanup...")
        
        # Clean up each tab
        for tab_index in range(self.count()):
            try:
                widget = self.widget(tab_index)
                tab_name = self.tabText(tab_index)
                if hasattr(widget, "cleanup"):
                    self.logger.info(f"Cleaning up tab: {tab_name}")
                    widget.cleanup()
                else:
                    self.logger.debug(f"Tab {tab_name} has no cleanup method")
            except Exception as e:
                self.logger.error(f"Error cleaning up tab {tab_index}: {e}")

        # Clean up managers if they have cleanup methods
        managers = {
            'prompt_manager': self.prompt_manager,
            'chat_manager': self.chat_manager,
            'memory_manager': self.memory_manager,
            'discord_manager': self.discord_manager,
            'cursor_manager': self.cursor_manager
        }

        for manager_name, manager in managers.items():
            if manager and hasattr(manager, 'cleanup'):
                try:
                    self.logger.info(f"Cleaning up {manager_name}...")
                    manager.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up {manager_name}: {e}")

        # Clean up extra dependencies
        if self.extra_dependencies:
            for dep_name, dependency in self.extra_dependencies.items():
                if dependency and hasattr(dependency, 'cleanup'):
                    try:
                        self.logger.info(f"Cleaning up extra dependency: {dep_name}")
                        dependency.cleanup()
                    except Exception as e:
                        self.logger.error(f"Error cleaning up {dep_name}: {e}")

        self.logger.info("MainTabs cleanup completed")

    def _init_tabs(self):
        """
        Initialize all tabs using a data-driven method for improved flow.
        The order here determines the order of tabs in the UI.
        """
        tabs_config = [
            {
                "name": "Prompt",
                "widget": PromptExecutionTab,
                "label": "Prompt Execution",
                "kwargs": {
                    "dispatcher": self.dispatcher,
                    "config": self.config_manager,
                    "logger": self.logger,
                    "prompt_manager": self.prompt_manager
                }
            },
            {
                "name": "Dreamscape",
                "widget": DreamscapeGenerationTab,
                "label": "Dreamscape",
                "kwargs": {
                    "dispatcher": self.dispatcher,
                    "prompt_manager": self.prompt_manager,
                    "chat_manager": self.chat_manager,
                    "memory_manager": self.memory_manager,
                    "discord_manager": self.discord_manager,
                    "ui_logic": self.ui_logic,
                    "config_manager": self.config_manager,
                    "logger": self.logger
                }
            },
            {
                "name": "Discord",
                "widget": DiscordTab,
                "label": "Discord",
                "kwargs": {
                    "dispatcher": self.dispatcher,
                    "config": self.config_manager,
                    "logger": self.logger,
                    "discord_manager": self.discord_manager
                }
            },
            {
                "name": "AIDE",
                "widget": AIDE,
                "label": "AIDE",
                "kwargs": {
                    "dispatcher": self.dispatcher,
                    "logger": self.logger,
                    "debug_service": self.extra_dependencies.get('debug_service'),
                    "fix_service": self.extra_dependencies.get('fix_service'),
                    "rollback_service": self.extra_dependencies.get('rollback_service'),
                    "cursor_manager": self.cursor_manager
                }
            },
            {
                "name": "Logs",
                "widget": LogsTab,
                "label": "Logs",
                "kwargs": {
                    "logger": self.logger
                }
            },
            {
                "name": "Social Dashboard",
                "widget": SocialDashboardTab,
                "label": "Social Dashboard",
                "kwargs": {
                    "dispatcher": self.dispatcher,
                    "config_manager": self.config_manager,
                    "discord_manager": (self.discord_manager or 
                        (self.extra_dependencies.get('service').discord 
                         if self.extra_dependencies.get('service') else None)),
                    "logger": self.logger
                }
            },
            {
                "name": "Meredith",
                "widget": MeredithTab,
                "label": "Meredith",
                "kwargs": {
                    "private_mode": True
                }
            },
            {
                "name": "SyncOps",
                "widget": SyncOpsTab,
                "label": "SyncOps",
                "kwargs": {
                    "user_name": getattr(self.config_manager, "user_name", "Victor"),
                    "logger": self.logger
                }
            }
        ]

        # Create and add each tab
        for config in tabs_config:
            widget_instance = config["widget"](**config["kwargs"])
            self.tabs[config["name"]] = widget_instance
            self.addTab(widget_instance, config["label"])

    def _connect_signals(self):
        """
        Connect signals to the corresponding slot methods to keep tabs in sync.
        """
        dispatcher = self.dispatcher
        dispatcher.prompt_executed.connect(self._on_prompt_executed)
        dispatcher.dreamscape_generated.connect(self._on_dreamscape_generated)
        dispatcher.discord_event.connect(self._on_discord_event)

        if hasattr(dispatcher, "debug_completed"):
            dispatcher.debug_completed.connect(self._on_debug_completed)
        if hasattr(dispatcher, "cursor_code_generated"):
            dispatcher.cursor_code_generated.connect(self._on_cursor_code_generated)
        if hasattr(dispatcher, "automation_result"):
            dispatcher.automation_result.connect(self._on_automation_result)

    def _on_prompt_executed(self, prompt_name, response_data):
        """
        Handle the prompt_executed signal by notifying relevant tabs.
        """
        self.append_output(f"[Prompt] Executed: {prompt_name}")

        dreamscape_tab = self.tabs.get("Dreamscape")
        if dreamscape_tab and hasattr(dreamscape_tab, "handle_prompt_executed"):
            dreamscape_tab.handle_prompt_executed(prompt_name, response_data)

        discord_tab = self.tabs.get("Discord")
        if discord_tab and hasattr(discord_tab, "handle_prompt_executed"):
            discord_tab.handle_prompt_executed(prompt_name, response_data)

    def _on_dreamscape_generated(self, data):
        """
        Handle the dreamscape_generated signal by notifying relevant tabs.
        """
        self.append_output("[Dreamscape] Generated new content")

        discord_tab = self.tabs.get("Discord")
        if discord_tab and hasattr(discord_tab, "handle_dreamscape_generated"):
            discord_tab.handle_dreamscape_generated(data)

    def _on_discord_event(self, event_type, event_data):
        """
        Handle the discord_event signal by notifying relevant tabs.
        """
        self.append_output(f"[Discord] Event: {event_type}")

        dreamscape_tab = self.tabs.get("Dreamscape")
        if dreamscape_tab and hasattr(dreamscape_tab, "handle_discord_event"):
            dreamscape_tab.handle_discord_event(event_type, event_data)

    def _on_debug_completed(self, result):
        """
        Handle the debug_completed signal by notifying relevant tabs.
        """
        self.append_output(f"[Debug] Completed with result: {result}")

        aide_tab = self.tabs.get("AIDE")
        if aide_tab and hasattr(aide_tab, "handle_debug_completed"):
            aide_tab.handle_debug_completed(result)

    def _on_cursor_code_generated(self, code):
        """
        Handle the cursor_code_generated signal by notifying relevant tabs.
        """
        self.append_output("[Cursor] Generated new code")

        aide_tab = self.tabs.get("AIDE")
        if aide_tab and hasattr(aide_tab, "handle_cursor_code_generated"):
            aide_tab.handle_cursor_code_generated(code)

    def _on_automation_result(self, result):
        """
        Handle the automation_result signal by notifying relevant tabs.
        """
        self.append_output(f"[Automation] {result}")

        aide_tab = self.tabs.get("AIDE")
        if aide_tab and hasattr(aide_tab, "on_automation_result"):
            aide_tab.on_automation_result(result)

    def append_output(self, message: str):
        """
        Append a message to the Logs tab; fall back to the logger if the Logs tab is unavailable.
        """
        logs_tab = self.tabs.get("Logs")
        if logs_tab and hasattr(logs_tab, "append_output"):
            logs_tab.append_output(message)
        elif self.logger:
            self.logger.info(message)
        else:
            print(f"[Fallback Log]: {message}")

    def broadcast_message(self, message: str):
        """
        Broadcast a message to all tabs via the dispatcher.
        """
        self.dispatcher.emit_log_output(message)