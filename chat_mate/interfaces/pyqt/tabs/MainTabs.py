"""
Main tabs container for the DreamOS application.
"""

from PyQt5.QtWidgets import QTabWidget
import logging

class MainTabs(QTabWidget):
    """
    Manages all tabs in the Dreamscape application, providing central control
    via dependency injection and a SignalDispatcher for decoupled interactions.
    
    This implementation uses a data-driven approach to initialize tabs,
    which improves readability and extensibility while retaining all original features.
    """

    def __init__(self, ui_logic=None, config_manager=None, logger=None,
                 prompt_manager=None, chat_manager=None, memory_manager=None,
                 discord_manager=None, cursor_manager=None, **extra_dependencies):
        """
        Initialize MainTabs with all required services and a SignalDispatcher.
        """
        super().__init__()
        self.ui_logic = ui_logic
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger("MainTabs")
        self.prompt_manager = prompt_manager
        self.chat_manager = chat_manager
        self.memory_manager = memory_manager
        self.discord_manager = discord_manager
        self.cursor_manager = cursor_manager
        self.extra_dependencies = extra_dependencies
        
        # Store services passed via extra_dependencies if needed later
        # Combine standard args and extra_dependencies for easier access?
        self.all_services = {
            'ui_logic': ui_logic,
            'config_manager': config_manager,
            'logger': self.logger,
            'prompt_manager': prompt_manager,
            'chat_manager': chat_manager,
            'memory_manager': memory_manager,
            'discord_manager': discord_manager,
            'cursor_manager': cursor_manager,
            **extra_dependencies
        }

        # Get the dispatcher from services
        self.dispatcher = self.all_services.get('dispatcher')
        if not self.dispatcher:
            self.logger.warning("MainTabs did not receive 'dispatcher' in services or extra_dependencies.")

        # Attempt to get the AutomationEngine - it might be in extra_dependencies
        self.engine = self.all_services.get('automation_engine')
        if not self.engine:
             self.logger.warning("MainTabs did not receive 'automation_engine' in services or extra_dependencies.")

        self.init_tabs()
        self.logger.info("MainTabs initialized")

        self.tabs = {}
        self._init_tabs()
        self._connect_signals()

        # Import FileBrowserWidget lazily to avoid circular imports
        from chat_mate.interfaces.pyqt.widgets.file_browser_widget import FileBrowserWidget
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
        
        # Import tab classes lazily to avoid circular imports
        from chat_mate.interfaces.pyqt.tabs.PromptExecutionTab import PromptExecutionTab
        from chat_mate.interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
        from chat_mate.interfaces.pyqt.tabs.LogsTab import LogsTab
        from chat_mate.interfaces.pyqt.tabs.ConfigurationTab import ConfigurationTab
        from chat_mate.interfaces.pyqt.tabs.AIDE import AIDE
        from chat_mate.interfaces.pyqt.tabs.meredith_tab import MeredithTab
        from chat_mate.interfaces.pyqt.tabs.SyncOpsTab import SyncOpsTab
        from chat_mate.interfaces.pyqt.tabs.SocialSetupTab import SocialSetupTab
        
        # Retrieve engine instance safely
        engine_instance = self.engine
        
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
                "name": "Social",
                "widget": SocialSetupTab,
                "label": "Social Setup",
                "kwargs": {
                    "config_manager": self.config_manager,
                    "logger": self.logger
                }
            },
            {
                "name": "AIDE",
                "widget": AIDE,
                "label": "AIDE",
                "kwargs": {
                    "dispatcher": self.dispatcher,
                    "logger": self.logger,
                    "engine": engine_instance,
                    "debug_service": self.all_services.get('debug_service'),
                    "fix_service": self.all_services.get('fix_service'),
                    "rollback_service": self.all_services.get('rollback_service'),
                    "cursor_manager": self.cursor_manager,
                    "project_scanner": self.all_services.get('project_scanner')
                }
            },
            {
                "name": "Logs",
                "widget": LogsTab,
                "label": "Logs",
                "kwargs": {
                    "logger": self.logger
                }
            }
        ]

        # Initialize each tab
        for tab_config in tabs_config:
            try:
                widget = tab_config["widget"](**tab_config["kwargs"])
                self.addTab(widget, tab_config["label"])
                self.tabs[tab_config["name"]] = widget
            except Exception as e:
                self.logger.error(f"Error initializing {tab_config['name']} tab: {e}")

    def _connect_signals(self):
        """
        Connect signals to the corresponding slot methods to keep tabs in sync.
        """
        if not self.dispatcher:
            self.logger.error("Cannot connect signals: dispatcher not available")
            return

        self.dispatcher.prompt_executed.connect(self._on_prompt_executed)
        self.dispatcher.dreamscape_generated.connect(self._on_dreamscape_generated)
        self.dispatcher.discord_event.connect(self._on_discord_event)

        if hasattr(self.dispatcher, "debug_completed"):
            self.dispatcher.debug_completed.connect(self._on_debug_completed)
        if hasattr(self.dispatcher, "cursor_code_generated"):
            self.dispatcher.cursor_code_generated.connect(self._on_cursor_code_generated)
        if hasattr(self.dispatcher, "automation_result"):
            self.dispatcher.automation_result.connect(self._on_automation_result)

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
        self.append_output("[Debug] Completed")

        aide_tab = self.tabs.get("AIDE")
        if aide_tab and hasattr(aide_tab, "handle_debug_completed"):
            aide_tab.handle_debug_completed(result)

    def _on_cursor_code_generated(self, code):
        """
        Handle the cursor_code_generated signal by notifying relevant tabs.
        """
        self.append_output("[Cursor] Code generated")

        aide_tab = self.tabs.get("AIDE")
        if aide_tab and hasattr(aide_tab, "handle_cursor_code_generated"):
            aide_tab.handle_cursor_code_generated(code)

    def _on_automation_result(self, result):
        """
        Handle the automation_result signal by notifying relevant tabs.
        """
        self.append_output("[Automation] Result received")

        aide_tab = self.tabs.get("AIDE")
        if aide_tab and hasattr(aide_tab, "handle_automation_result"):
            aide_tab.handle_automation_result(result)

    def append_output(self, message):
        """
        Append output to the logs tab.
        """
        logs_tab = self.tabs.get("Logs")
        if logs_tab and hasattr(logs_tab, "append_output"):
            logs_tab.append_output(message)

    def broadcast_message(self, message: str):
        """
        Broadcast a message to all tabs via the dispatcher.
        """
        self.dispatcher.emit_log_output(message)
