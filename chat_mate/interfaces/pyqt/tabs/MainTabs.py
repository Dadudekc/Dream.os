from PyQt5.QtWidgets import QTabWidget
from interfaces.pyqt.tabs.PromptExecutionTab import PromptExecutionTab
from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
from interfaces.pyqt.components.discord_tab import DiscordTab
from interfaces.pyqt.tabs.LogsTab import LogsTab
from interfaces.pyqt.tabs.ConfigurationTab import ConfigurationTab
from interfaces.pyqt.tabs.SocialDashboardTab import SocialDashboardTab
from interfaces.pyqt.tabs.AIDE import AIDE

class MainTabs(QTabWidget):
    """
    Manages all tabs in the Dreamscape application, providing central control
    through dependency injection and the SignalDispatcher for decoupled interactions.
    """

    def __init__(self, dispatcher, ui_logic=None, config_manager=None, logger=None, 
                 prompt_manager=None, chat_manager=None, memory_manager=None, 
                 discord_manager=None, cursor_manager=None, **extra_dependencies):
        """
        Initialize MainTabs with explicitly injected services and SignalDispatcher.

        Args:
            dispatcher (SignalDispatcher): Centralized event dispatcher.
            ui_logic: UI logic controller instance.
            config_manager: Configuration manager service.
            logger: Logger service instance.
            prompt_manager: Prompt management service.
            chat_manager: Chat interaction manager.
            memory_manager: Memory service manager.
            discord_manager: Discord integration manager.
            cursor_manager: Cursor session manager for debugging.
            **extra_dependencies: Optional additional services.
        """
        super().__init__()

        # Central dispatcher for signals
        self.dispatcher = dispatcher
        self.ui_logic = ui_logic
        self.logger = logger
        self.config_manager = config_manager
        self.prompt_manager = prompt_manager
        self.chat_manager = chat_manager
        self.memory_manager = memory_manager
        self.discord_manager = discord_manager
        self.cursor_manager = cursor_manager
        self.extra_dependencies = extra_dependencies

        # Initialize tabs dictionary
        self.tabs = {}

        # Initialize UI
        self._init_tabs()
        self._connect_signals()

    def _init_tabs(self):
        """Initialize and add all tabs."""
        # Prompt Execution Tab
        self.tabs["Prompt"] = PromptExecutionTab(
            dispatcher=self.dispatcher,
            config=self.config_manager,
            logger=self.logger,
            prompt_manager=self.prompt_manager
        )
        self.addTab(self.tabs["Prompt"], "Prompt Execution")

        # Dreamscape Generation Tab
        self.tabs["Dreamscape"] = DreamscapeGenerationTab(
            dispatcher=self.dispatcher,
            prompt_manager=self.prompt_manager,
            chat_manager=self.chat_manager,
            memory_manager=self.memory_manager,
            discord_manager=self.discord_manager,
            ui_logic=self.ui_logic,
            config_manager=self.config_manager,
            logger=self.logger
        )
        self.addTab(self.tabs["Dreamscape"], "Dreamscape")

        # Discord Tab
        self.tabs["Discord"] = DiscordTab(
            dispatcher=self.dispatcher,
            config=self.config_manager,
            logger=self.logger,
            discord_manager=self.discord_manager
        )
        self.addTab(self.tabs["Discord"], "Discord")

        # AIDE Tab
        self.tabs["AIDE"] = AIDE(
            dispatcher=self.dispatcher,
            logger=self.logger,
            debug_service=self.extra_dependencies.get('debug_service'),
            fix_service=self.extra_dependencies.get('fix_service'),
            rollback_service=self.extra_dependencies.get('rollback_service'),
            cursor_manager=self.cursor_manager
        )
        self.addTab(self.tabs["AIDE"], "AIDE")

        # Logs Tab (Centralized logging)
        self.tabs["Logs"] = LogsTab(
            logger=self.logger
        )
        self.addTab(self.tabs["Logs"], "Logs")

        # Social Dashboard Tab
        self.tabs["Social Dashboard"] = SocialDashboardTab(
            dispatcher=self.dispatcher,
            config_manager=self.config_manager,
            discord_manager=self.discord_manager if self.discord_manager else 
                           (self.extra_dependencies.get('service').discord if 
                            self.extra_dependencies.get('service') else None),
            logger=self.logger
        )
        self.addTab(self.tabs["Social Dashboard"], "Social Dashboard")
        
    def _connect_signals(self):
        """Connect signals between tabs via the dispatcher."""
        # Route prompt_executed signal to relevant tabs
        self.dispatcher.prompt_executed.connect(self._on_prompt_executed)
        
        # Route dreamscape_generated signal to relevant tabs
        self.dispatcher.dreamscape_generated.connect(self._on_dreamscape_generated)
        
        # Route discord_event signal to relevant tabs
        self.dispatcher.discord_event.connect(self._on_discord_event)
        
        # Route debug events to relevant tabs
        if hasattr(self.dispatcher, "debug_completed"):
            self.dispatcher.debug_completed.connect(self._on_debug_completed)
        if hasattr(self.dispatcher, "cursor_code_generated"):
            self.dispatcher.cursor_code_generated.connect(self._on_cursor_code_generated)
            
        # Connect automation-related signals if available
        if hasattr(self.dispatcher, "automation_result"):
            self.dispatcher.automation_result.connect(self._on_automation_result)
        
    def _on_prompt_executed(self, prompt_name, response_data):
        """Handle prompt_executed signal by notifying appropriate tabs."""
        # Log the event
        self.append_output(f"[Prompt] Executed: {prompt_name}")
        
        # Notify Dreamscape tab if it has a handle_prompt_executed method
        dreamscape_tab = self.tabs.get("Dreamscape")
        if dreamscape_tab and hasattr(dreamscape_tab, "handle_prompt_executed"):
            dreamscape_tab.handle_prompt_executed(prompt_name, response_data)
            
        # Notify Discord tab if needed
        discord_tab = self.tabs.get("Discord")
        if discord_tab and hasattr(discord_tab, "handle_prompt_executed"):
            discord_tab.handle_prompt_executed(prompt_name, response_data)
            
    def _on_dreamscape_generated(self, data):
        """Handle dreamscape_generated signal by notifying appropriate tabs."""
        # Log the event
        self.append_output(f"[Dreamscape] Generated new content")
        
        # Notify Discord tab for potential sharing
        discord_tab = self.tabs.get("Discord")
        if discord_tab and hasattr(discord_tab, "handle_dreamscape_generated"):
            discord_tab.handle_dreamscape_generated(data)
            
    def _on_discord_event(self, event_type, event_data):
        """Handle discord_event signal by notifying appropriate tabs."""
        # Log the event
        self.append_output(f"[Discord] Event: {event_type}")
        
        # Notify Dreamscape tab for potential response
        dreamscape_tab = self.tabs.get("Dreamscape")
        if dreamscape_tab and hasattr(dreamscape_tab, "handle_discord_event"):
            dreamscape_tab.handle_discord_event(event_type, event_data)

    def _on_debug_completed(self, result):
        """Handle debug_completed signal by notifying appropriate tabs."""
        # Log the event
        self.append_output(f"[Debug] Completed with result: {result}")
        
        # Notify AIDE tab if needed
        aide_tab = self.tabs.get("AIDE")
        if aide_tab and hasattr(aide_tab, "handle_debug_completed"):
            aide_tab.handle_debug_completed(result)

    def _on_cursor_code_generated(self, code):
        """Handle cursor_code_generated signal by notifying appropriate tabs."""
        # Log the event
        self.append_output(f"[Cursor] Generated new code")
        
        # Notify AIDE tab if needed
        aide_tab = self.tabs.get("AIDE")
        if aide_tab and hasattr(aide_tab, "handle_cursor_code_generated"):
            aide_tab.handle_cursor_code_generated(code)
            
    def _on_automation_result(self, result):
        """Handle automation_result signal by notifying appropriate tabs."""
        # Log the event
        self.append_output(f"[Automation] {result}")
        
        # Notify AIDE tab if needed
        aide_tab = self.tabs.get("AIDE")
        if aide_tab and hasattr(aide_tab, "on_automation_result"):
            aide_tab.on_automation_result(result)

    def append_output(self, message: str):
        """
        Append a message to Logs tab; fallback to logger if unavailable.

        Args:
            message (str): Message to log or display.
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
        
        Args:
            message (str): Message to broadcast
        """
        self.dispatcher.emit_log_output(message)
