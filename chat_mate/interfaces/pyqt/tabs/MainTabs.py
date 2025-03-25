from PyQt5.QtWidgets import QTabWidget
from interfaces.pyqt.tabs.PromptExecutionTab import PromptExecutionTab
from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
from interfaces.pyqt.components.discord_tab import DiscordTab
from interfaces.pyqt.tabs.LogsTab import LogsTab
from interfaces.pyqt.tabs.DebuggerTab import DebuggerTab
from interfaces.pyqt.tabs.ConfigurationTab import ConfigurationTab
from interfaces.pyqt.tabs.SocialDashboardTab import SocialDashboardTab

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

        # Scalable tab management
        self.tabs = {}

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Explicitly initialize and register tabs with dispatcher and services."""

        # Configuration Tab
        self.tabs["Configuration"] = ConfigurationTab(
            config_manager=self.config_manager,
            dispatcher=self.dispatcher,
            service=self.extra_dependencies.get('service') if isinstance(self.extra_dependencies, dict) else None,
            command_handler=self.extra_dependencies.get('command_handler') if isinstance(self.extra_dependencies, dict) else None,
            logger=self.logger
        )
        self.addTab(self.tabs["Configuration"], "Configuration")

        # Dreamscape Generation Tab
        self.tabs["Dreamscape"] = DreamscapeGenerationTab(
            dispatcher=self.dispatcher,
            ui_logic=self.ui_logic,
            config_manager=self.config_manager,
            logger=self.logger,
            prompt_manager=self.prompt_manager,
            chat_manager=self.chat_manager,
            memory_manager=self.memory_manager,
            discord_manager=self.discord_manager,
            response_handler=self.extra_dependencies.get('response_handler') if isinstance(self.extra_dependencies, dict) else None
        )
        self.addTab(self.tabs["Dreamscape"], "Dreamscape")

        # Prompt Execution Tab
        self.tabs["Prompt Execution"] = PromptExecutionTab(
            dispatcher=self.dispatcher,
            config=self.config_manager,
            logger=self.logger,
            prompt_manager=self.prompt_manager
        )
        self.addTab(self.tabs["Prompt Execution"], "Prompt Execution")

        # Discord Tab
        self.tabs["Discord"] = DiscordTab(
            dispatcher=self.dispatcher,
            config=self.config_manager,
            logger=self.logger,
            discord_manager=self.discord_manager
        )
        self.addTab(self.tabs["Discord"], "Discord")

        # Debugger Tab
        self.tabs["Debugger"] = DebuggerTab(
            dispatcher=self.dispatcher,
            logger=self.logger,
            cursor_manager=self.cursor_manager
        )
        self.addTab(self.tabs["Debugger"], "Debugger")

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
        
        # Notify Debugger tab if needed
        debugger_tab = self.tabs.get("Debugger")
        if debugger_tab and hasattr(debugger_tab, "handle_debug_completed"):
            debugger_tab.handle_debug_completed(result)

    def _on_cursor_code_generated(self, code):
        """Handle cursor_code_generated signal by notifying appropriate tabs."""
        # Log the event
        self.append_output(f"[Cursor] Generated new code")
        
        # Notify Debugger tab if needed
        debugger_tab = self.tabs.get("Debugger")
        if debugger_tab and hasattr(debugger_tab, "handle_cursor_code_generated"):
            debugger_tab.handle_cursor_code_generated(code)

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
