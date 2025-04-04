"""
Main Window Module

This module provides the main window implementation for the Dream.OS PyQt interface.
"""

import sys
import logging
import warnings
import time
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Suppress specific warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*found in sys.modules after import of package.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*sipPyTypeDict.*")

logger = logging.getLogger(__name__)

# PyQt imports
from PyQt5.QtWidgets import (
    QApplication, 
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QLabel,
    QMenuBar,
    QStatusBar,
    QAbstractButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

# Import core components
from core.TemplateManager import TemplateManager
from core.config.config_manager import ConfigManager
from core.PathManager import PathManager
from core.recovery.recovery_engine import RecoveryEngine
from core.chat_engine.chat_engine_manager import ChatEngineManager
from core.factories.prompt_factory import PromptFactory
from core.chatgpt_automation.OpenAIClient import OpenAIClient
from .mock_service import MockService # <-- Import from new file
# Import tabs
from .tabs.prompt_sync.PromptSyncTab import PromptSyncTab
from .tabs.chat_tab.ChatTabWidget import ChatTabWidget
from .tabs.chat_tab.ChatTabWidgetManager import ChatTabWidgetManager
from .tabs.contextual_chat.ContextualChatTab import ContextualChatTab
from .tabs.task_board.TaskBoardTab import TaskBoardTab
from .tabs.ConfigurationTab import ConfigurationTab
from .tabs.settings_tab import SettingsTab
from .tabs.main_tab import MainTab
from .tabs.SyncOpsTab import SyncOpsTab
from .tabs.SocialDashboardTab import SocialDashboardTab
from .tabs.PromptExecutionTab import PromptExecutionTab
from .tabs.LogsTab import LogsTab
from .tabs.DependencyMapTab import DependencyMapTab
from .tabs.voice_mode_tab import VoiceModeTab
from .tabs.unified_dashboard.UnifiedDashboardTab import UnifiedDashboardTab
from .tabs.meredith_tab import MeredithTab
from .tabs.draggable_prompt_board_tab import DraggablePromptBoardTab
from micro_factories.cursor_execution_tab_factory import CursorExecutionTabFactory
from .tabs.dream_os_tab_factory import (
    TaskStatusIntegrationFactory, 
    PromptPreviewIntegrationFactory,
    SuccessDashboardIntegrationFactory
)
from .services.MetricsService import MetricsService
from .widgets.RecoveryDashboardWidget import RecoveryDashboardWidget
from .services.AdaptiveRecoveryService import AdaptiveRecoveryService
from .tabs.metrics_viewer.MetricsViewerTab import MetricsViewerTab
from interfaces.pyqt.tabs.dreamscape.DreamscapeGenerationTab import DreamscapeTab
from .services.TabValidatorService import TabValidatorService
from core.meredith.meredith_dispatcher import MeredithDispatcher
from core.meredith.profile_scraper import ScraperManager
from core.meredith.resonance_scorer import ResonanceScorer
from core.memory.MeritChainManager import MeritChainManager
from core.init.service_initializer import ServiceInitializer, ServiceInitializationError

# --- Import the correct Discord Manager ---
import asyncio
import discord
import time # Add import for time.sleep
from core.services.discord.DiscordManager import DiscordManager

class DreamOsMainWindow(QMainWindow):
    """Main window for the Dream.OS interface."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Configure logging and initialize self.logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__) 
        
        self.setWindowTitle("Dream.OS")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize core managers
        self.config_manager = ConfigManager()
        self.path_manager = PathManager()
        
        # --- Initialize Discord Manager CORRECTLY ---
        self.discord_manager = None # Renamed from discord_bot_manager
        discord_client = None
        loop = None
        try:
            # Instantiate the correct DiscordManager
            # It loads token/channel from config internally if not provided
            self.discord_manager = DiscordManager()
            self.discord_manager.run_bot() # Start the bot thread
            # Wait briefly for thread/loop to potentially initialize
            # A more robust solution might use signals or futures
            time.sleep(1.0) 
            discord_client = self.discord_manager.bot # Get the client instance
            loop = self.discord_manager.get_loop() # Get the loop instance

            if not discord_client or not loop:
                 self.logger.warning("DiscordManager did not provide client or loop after start. Discord features may be limited.")
            else:
                 self.logger.info("DiscordManager initialized and bot started.")
        except Exception as e:
            self.logger.error(f"Failed to initialize or start DiscordManager: {e}. Discord features disabled.", exc_info=True)
            # Non-fatal, continue without discord features

        # Initialize services using the new initializer, passing client and loop
        try:
            self.services = ServiceInitializer.initialize_all(
                self.logger, 
                self.path_manager,
                discord_client=discord_client, 
                loop=loop
            )
        except ServiceInitializationError as e:
            self.logger.critical(f"Fatal error during service initialization: {e}", exc_info=True)
            QMessageBox.critical(self, "Initialization Error", f"A critical service failed to initialize: {e}. Application will now exit.")
            # Exit the application gracefully if possible
            # For PyQt, closing the main window might trigger shutdown.
            # If running from a script, sys.exit might be needed.
            self.close() # Attempt to close the window
            sys.exit(1) # Ensure exit if close doesn't suffice
        except Exception as e: # Catch any other unexpected errors during init
             self.logger.critical(f"Unexpected fatal error during service initialization: {e}", exc_info=True)
             QMessageBox.critical(self, "Initialization Error", f"An unexpected error occurred during initialization: {e}. Application will now exit.")
             self.close()
             sys.exit(1)
        
        # --- Assign critical services to attributes AFTER initialization ---
        # This ensures they are available before _init_ui is called
        self.metrics_service = self.services.get('metrics')
        if not self.metrics_service:
             # Handle case where metrics service failed init (though initializer should raise)
             self.logger.error("Metrics service not found after initialization!")
             # Decide how to handle - maybe assign a mock or raise error?
             # For now, let's allow it to proceed but log error.
             pass 
        # Assign other services needed directly by the main window here if necessary
        # e.g., self.some_other_service = self.services.get('some_other_key')
        # ------------------------------------------------------------------
        
        # Validate tab constructors (only if services initialized successfully)
        self.tab_validator = TabValidatorService(self.services)
        validation_results = self.tab_validator.validate_all_tabs()
        
        # Initialize UI
        self._init_ui()
        
        # Log validation results
        for tab_name, is_valid in validation_results.items():
            status = "✅" if is_valid else "❌"
            self.logger.info(f"{status} Tab '{tab_name}' validation: {'passed' if is_valid else 'failed'}")
        
        # Show ready status
        self.statusBar().showMessage("Dream.OS Ready")
        
    def _init_ui(self):
        """Initialize the user interface."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Initialize tab managers
        self.chat_tab_manager = ChatTabWidgetManager(self.services)
        
        # Create and add tabs in logical groups
        
        # Group 1: Main Development Interface
        config_mgr = self.services.get('config_manager', self.services.get('component_managers', {}).get('config_manager')) # Check both locations
        service_mgr = self.services.get('system_loader') # Assuming system_loader acts as service manager
        main_tab_logger = self.services.get('logger', self.logger) # Use main logger if specific not found
        
        self.main_tab = MainTab(
            config_manager=config_mgr,
            service_manager=service_mgr, # Pass system_loader as service_manager
            logger=main_tab_logger,
            parent=self
        )
        self.tab_widget.addTab(self.main_tab, "Main")
        
        self.task_board_tab = TaskBoardTab(self.services)
        self.tab_widget.addTab(self.task_board_tab, "Task Board")
        
        self.cursor_execution_tab = CursorExecutionTabFactory.create(services=self.services, parent=self)
        self.tab_widget.addTab(self.cursor_execution_tab, "Cursor Execution")
        
        # Create the task status tab for orchestration monitoring
        self.task_status_tab = TaskStatusIntegrationFactory.create(services=self.services, parent=self)
        self.tab_widget.addTab(self.task_status_tab, "Task Status")
        
        # Create the prompt preview tab for template and task management
        self.prompt_preview_tab = PromptPreviewIntegrationFactory.create(services=self.services, parent=self)
        self.tab_widget.addTab(self.prompt_preview_tab, "Prompt Preview")
        
        # Create the success dashboard tab for metrics visualization
        self.success_dashboard_tab = SuccessDashboardIntegrationFactory.create(services=self.services, parent=self)
        self.tab_widget.addTab(self.success_dashboard_tab, "Success Dashboard")
        
        # Group 2: Chat and Communication
        self.contextual_chat_tab = ContextualChatTab(self.services)
        self.tab_widget.addTab(self.contextual_chat_tab, "Contextual Chat")
        
        # REVIEW: Added Voice Mode Tab - V.P. 2024-04-03
        self.voice_mode_tab = VoiceModeTab(self.services)
        self.tab_widget.addTab(self.voice_mode_tab, "Voice Mode")
        # END REVIEW
        
        self.chat_widget = self.chat_tab_manager.get_widget()
        self.tab_widget.addTab(self.chat_widget, "Chat")
        
        # Group 3: Content Generation
        # Retrieve ChatEngineManager instance
        chat_manager_instance = self.services.get('chat_manager')
        
        if chat_manager_instance and not isinstance(chat_manager_instance, MockService):
            try:
                # Pass the ChatEngineManager instance as both dreamscape_service and chat_manager
                self.dreamscape_tab = DreamscapeTab(
                    dreamscape_service=chat_manager_instance, 
                    chat_manager=chat_manager_instance,
                    logger=self.logger # Pass logger if DreamscapeTab accepts it
                )
                self.tab_widget.addTab(self.dreamscape_tab, "Dreamscape")
                self.logger.info("DreamscapeTab added successfully.")
            except Exception as e:
                self.logger.error(f"Failed to initialize or add DreamscapeTab: {e}", exc_info=True)
                # Add a placeholder tab indicating the error
                error_tab = QWidget()
                error_layout = QVBoxLayout()
                error_label = QLabel("Error loading Dreamscape Tab. Check logs.")
                error_layout.addWidget(error_label)
                error_tab.setLayout(error_layout)
                self.tab_widget.addTab(error_tab, "Dreamscape (Error)")
        else:
            self.logger.error("Chat Manager service not found or is a mock. Cannot initialize DreamscapeTab.")
            # Add a placeholder tab indicating the error
            error_tab = QWidget()
            error_layout = QVBoxLayout()
            error_label = QLabel("Error loading Dreamscape Tab (Chat Manager missing/mocked)")
            error_layout.addWidget(error_label)
            error_tab.setLayout(error_layout)
            self.tab_widget.addTab(error_tab, "Dreamscape (Error)")
        
        self.prompt_execution_tab = PromptExecutionTab(self.services)
        self.tab_widget.addTab(self.prompt_execution_tab, "Prompt Execution")
        
        # Group 4: Social and Dashboard
        self.social_dashboard_tab = SocialDashboardTab(self.services)
        self.tab_widget.addTab(self.social_dashboard_tab, "Social Dashboard")
        
        # REVIEW: Added Unified Dashboard Tab - V.P. 2024-04-03
        self.unified_dashboard_tab = UnifiedDashboardTab(self.services)
        self.tab_widget.addTab(self.unified_dashboard_tab, "Unified Dashboard")
        # END REVIEW
        
        self.metrics_viewer_tab = MetricsViewerTab(self.services)
        self.tab_widget.addTab(self.metrics_viewer_tab, "Metrics Viewer")
        
        # Group 5: System and Configuration
        self.settings_tab = SettingsTab(self.services)
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        self.configuration_tab = ConfigurationTab(self.services)
        self.tab_widget.addTab(self.configuration_tab, "Configuration")
        
        self.sync_ops_tab = SyncOpsTab(self.services)
        self.tab_widget.addTab(self.sync_ops_tab, "Sync Operations")
        
        self.prompt_sync_tab = PromptSyncTab(self.services)
        self.tab_widget.addTab(self.prompt_sync_tab, "Prompt Sync")
        
        # Group 6: Development Tools
        self.dependency_map_tab = DependencyMapTab(self.services)
        self.tab_widget.addTab(self.dependency_map_tab, "Dependency Map")

        # REVIEW: Added Draggable Prompt Board Tab - V.P. 2024-04-03
        self.draggable_prompt_board_tab = DraggablePromptBoardTab(self.services)
        self.tab_widget.addTab(self.draggable_prompt_board_tab, "Prompt Board")
        # END REVIEW
        
        self.logs_tab = LogsTab(self.services)
        self.tab_widget.addTab(self.logs_tab, "Logs")
        
        # Group 7: Experimental/Other
        # REVIEW: Added Meredith Tab - V.P. 2024-04-03
        self.meredith_tab = MeredithTab(self.services)
        self.tab_widget.addTab(self.meredith_tab, "Meredith")
        # END REVIEW
        
        # Create recovery dashboard
        self.recovery_dashboard = RecoveryDashboardWidget(self.metrics_service)
        self.tab_widget.addTab(self.recovery_dashboard, "Recovery Dashboard")
        
        # Connect signals
        self.task_board_tab.task_queued.connect(self._handle_queued_task)
        self._connect_tab_signals()
        self.recovery_dashboard.refresh_requested.connect(self._on_recovery_dashboard_refresh)
        
        # Add tab widget to layout
        layout.addWidget(self.tab_widget)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create status bar
        self.setStatusBar(QStatusBar())
        
        # REVIEW: Enable button debugging for all tabs - V.P. 2024-04-03
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if widget: # Ensure widget exists
                self._enable_button_debugging(widget)
        # END REVIEW

    # REVIEW: Added method for button debugging - V.P. 2024-04-03
    def _enable_button_debugging(self, widget: QWidget):
        """Recursively find buttons and connect their clicked signal to a logger."""
        try:
            tab_index = self.tab_widget.indexOf(widget)
            tab_name = "Unknown Tab"
            if tab_index != -1:
                tab_name = self.tab_widget.tabText(tab_index)
            else: # Maybe it's a top-level widget not directly in tabs?
                if hasattr(widget, 'windowTitle'):
                    tab_name = widget.windowTitle() or tab_name

            for button in widget.findChildren(QAbstractButton):
                # Generate a meaningful name for the button
                button_identifier = button.objectName() or button.text() or f"Unnamed_{type(button).__name__}"
                # Sanitize name (remove newlines etc.)
                button_identifier = button_identifier.replace('\n', ' ').strip()
                
                # Use a lambda with default argument to capture current button name and tab name
                try:
                    # Disconnect first to prevent duplicate connections if called multiple times
                    button.clicked.disconnect()
                except TypeError: # No connection exists
                    pass
                button.clicked.connect(lambda checked=False, btn_id=button_identifier, tb_name=tab_name:
                    self.logger.info(f"[🟣 Button Clicked | {tb_name}] → {btn_id}"))
        except Exception as e:
             self.logger.error(f"Error setting up button debugging for widget {widget}: {e}")
    # END REVIEW

    def _connect_tab_signals(self):
        """Connect signals between tabs for inter-tab communication."""
        # Connect TaskBoard to CursorExecution
        if hasattr(self.task_board_tab, 'task_queued') and hasattr(self.cursor_execution_tab, 'execute_task'):
            self.task_board_tab.task_queued.connect(self.cursor_execution_tab.execute_task)
        
        # Connect PromptExecution to Logs
        if hasattr(self.prompt_execution_tab, 'log_message') and hasattr(self.logs_tab, 'add_log'):
            self.prompt_execution_tab.log_message.connect(self.logs_tab.add_log)
        
        # Connect SyncOps to SocialDashboard
        if hasattr(self.sync_ops_tab, 'sync_completed') and hasattr(self.social_dashboard_tab, 'refresh_data'):
            self.sync_ops_tab.sync_completed.connect(self.social_dashboard_tab.refresh_data)
        
    def _create_menu_bar(self):
        """Create the application menu bar."""
        menu_bar = QMenuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("Exit", self.close)
        
        # View menu
        view_menu = menu_bar.addMenu("View")
        view_menu.addAction("Reset Layout", self._reset_layout)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction("About", self._show_about)
        
        self.setMenuBar(menu_bar)
        
    def _reset_layout(self):
        """Reset the window layout to default."""
        self.resize(1200, 800)
        self.prompt_sync_tab.main_splitter.setSizes([800, 200])
        
    def _show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About Dream.OS",
            "Dream.OS - The AI Content Generation Studio\n\n"
            "Version: 0.1.0\n"
            "© 2024 Dream.OS Team"
        )
        
    def closeEvent(self, event):
        """Handle window close event."""
        self.logger.info("Close event triggered. Initiating shutdown sequence...")

        # Attempt to gracefully shut down services
        shutdown_errors = []
        if hasattr(self, 'services') and self.services:
            # Shutdown order might matter. Reverse of initialization could be safer.
            # Example: Shutdown chat manager last if it uses other services.
            service_shutdown_order = [
                # Start with UI-related or less critical first?
                'cursor_session_manager', 
                'chat_manager', # Depends on others, maybe later?
                'meredith_dispatcher', 
                'scraper_manager', 
                'openai_client',
                # Add other services that need explicit shutdown
            ]

            for service_name in service_shutdown_order:
                 service = self.services.get(service_name)
                 if service and hasattr(service, 'shutdown'):
                     try:
                         self.logger.info(f"Shutting down {service_name}...")
                         if asyncio.iscoroutinefunction(service.shutdown):
                              # If shutdown is async, need to handle it appropriately.
                              # Running it synchronously here might block UI.
                              # This needs a proper async shutdown strategy if required.
                              self.logger.warning(f"Async shutdown for {service_name} not fully supported in sync closeEvent.")
                              # asyncio.run(service.shutdown()) # Avoid this in sync event handler
                         else:
                             service.shutdown()
                         self.logger.info(f"{service_name} shut down.")
                     except Exception as e:
                         self.logger.error(f"Error shutting down service '{service_name}': {e}", exc_info=True)
                         shutdown_errors.append(f"{service_name}: {e}")
        else:
             self.logger.warning("Services dictionary not found or empty during closeEvent.")

        # --- Shutdown Discord Manager CORRECTLY ---
        if self.discord_manager: # Check if instance exists
            try:
                self.logger.info("Shutting down Discord Manager...")
                self.discord_manager.stop_bot() # Call the correct stop method
                self.logger.info("Discord Manager shut down.")
            except Exception as e:
                self.logger.error(f"Error shutting down Discord Manager: {e}", exc_info=True)
                shutdown_errors.append(f"DiscordManager: {e}")

        # --- Save Config (if applicable) ---
        config_mgr = self.services.get('config_manager') if hasattr(self, 'services') else self.config_manager
        if config_mgr and hasattr(config_mgr, 'save_config'):
            try:
                self.logger.info("Saving configuration...")
                config_mgr.save_config()
                self.logger.info("Configuration saved.")
            except Exception as e:
                self.logger.error(f"Error saving configuration: {e}", exc_info=True)
                shutdown_errors.append(f"ConfigManager save: {e}")

        if shutdown_errors:
            error_msg = "Errors occurred during shutdown:\n" + "\n".join(shutdown_errors)
            self.logger.error(error_msg)
            # Optionally show a message box, but be careful not to block exit
            # QMessageBox.warning(self, "Shutdown Error", error_msg)

        self.logger.info("Shutdown sequence complete. Accepting close event.")
        super().closeEvent(event)

    def _handle_queued_task(self, task: Dict[str, Any]):
        """Handle a queued task with metrics tracking."""
        task_id = task.get("id", str(uuid.uuid4()))
        start_time = time.time()
        
        try:
            # Update initial metrics
            self.metrics_service.update_task_metrics(
                task_id,
                "queued",
                task_type=task.get("action", "unknown"),
                title=task.get("title", "Untitled Task")
            )
            
            # Create new chat tab
            chat_tab = self.chat_tab_manager.create_new_tab(
                title=f"Task: {task.get('title', 'New Task')}"
            )
            self.tab_widget.setCurrentWidget(chat_tab)
            
            # Gather context and build prompt
            context = self._gather_task_context(task)
            prompt = self._build_task_prompt(task, context)
            
            # Initialize task context for recovery
            task_context = {
                "task_id": task_id,
                "max_retries": 3,
                "retry_delay": 5,
                "timeout": 300,
                "metrics": {
                    "retry_count": 0,
                    "start_time": datetime.now().isoformat(),
                    "status": "queued"
                },
                "error_type": "unknown"  # Will be updated if error occurs
            }
            
            # Queue task to cursor with recovery handling
            cursor_session = self.services.get("cursor_session_manager")
            if not cursor_session:
                raise RuntimeError("CursorSessionManager not available")
                
            result = cursor_session.queue_prompt(
                prompt,
                isolation_level="high",
                on_stall=lambda: self.recovery_engine.handle_stall(task_context),
                timeout=task_context["timeout"]
            )
            
            # Update completion metrics
            execution_time = time.time() - start_time
            self.metrics_service.update_task_metrics(
                task_id,
                "completed",
                execution_time=execution_time,
                result=result
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            self.metrics_service.update_task_metrics(
                task_id,
                "error",
                error=str(e),
                execution_time=time.time() - start_time
            )
            raise
    
    def _gather_task_context(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Gather context for task execution with metrics."""
        context = {
            "conversation": self._gather_conversation_context(task),
            "project": self._gather_project_context(task),
            "metrics": self.metrics_service.get_global_metrics(),
            "task_history": self.metrics_service.get_task_metrics(task.get("id", ""))
        }
        return context
    
    def _gather_conversation_context(self, task: Dict[str, Any]) -> str:
        """
        Gather conversation context for the task.
        
        Args:
            task: The task dictionary
            
        Returns:
            String containing conversation context
        """
        conversation_context = ""
        episode_generator = self.services.get('component_managers', {}).get('episode_generator')
        
        if episode_generator and task.get("conversation_id"):
            try:
                history = episode_generator.get_episode_history(task["conversation_id"])
                if isinstance(history, list) and history:
                    conversation_context = "\n".join(history[-3:])  # Last 3 messages
                elif isinstance(history, str):
                    conversation_context = history
                self.logger.debug(f"Retrieved conversation context for task {task['id']}")
            except Exception as e:
                self.logger.warning(f"Failed to get conversation history: {e}")
        
        return conversation_context
    
    def _gather_project_context(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gather project context using ProjectScanner.
        
        Args:
            task: The task dictionary
            
        Returns:
            Dictionary containing project context
        """
        project_context = {}
        project_scanner = self.services.get('project_scanner')
        
        if project_scanner:
            try:
                # First try to load from cache
                project_context = project_scanner.load_cache()
                
                # If cache is empty or task requires fresh scan
                if not project_context.get("files") or task.get("force_rescan"):
                    project_context = project_scanner.scan_project(max_files=100)
                    
                self.logger.debug(f"Retrieved project context for task {task['id']}")
            except Exception as e:
                self.logger.warning(f"Failed to get project context: {e}")
        
        return project_context
    
    def _build_task_prompt(self, task: Dict[str, Any], conversation_context: str, project_context: Dict[str, Any]) -> str:
        """
        Build the dynamic prompt for task execution based on task type.
        
        Args:
            task: The task dictionary
            conversation_context: String containing conversation history
            project_context: Dictionary containing project analysis
            
        Returns:
            String containing the complete prompt
        """
        template_manager = self.services.get('component_managers', {}).get('template_manager')
        action = task.get("action", "Continue Thought").lower()
        
        if template_manager and hasattr(template_manager, "render_template_by_action"):
            try:
                # Build template context with all available data
                template_context = {
                    "conversation": conversation_context,
                    "project": project_context,
                    "task": task,
                    "metrics": self._get_task_metrics(task["id"]) if task.get("id") else {},
                    "cursor_rules": self._get_cursor_rules()
                }
                
                # Try to use a specific template for the action type
                if hasattr(template_manager, f"render_{action}_template"):
                    prompt = getattr(template_manager, f"render_{action}_template")(template_context)
                else:
                    # Fallback to generic template with action-specific sections
                    prompt = template_manager.render_template_by_action(action, template_context)
                
                self.logger.debug(f"Built prompt using template for task {task['id']} (action: {action})")
                return prompt
            except Exception as e:
                self.logger.warning(f"Failed to render template: {e}")
                return self._build_action_specific_fallback(task, conversation_context, project_context)
        else:
            return self._build_action_specific_fallback(task, conversation_context, project_context)
    
    def _build_action_specific_fallback(self, task: Dict[str, Any], conversation_context: str, project_context: Dict[str, Any]) -> str:
        """Build action-specific fallback prompts when template manager is unavailable."""
        action = task.get("action", "Continue Thought").lower()
        base_prompt = (
            f"Task ID: {task['id']}\n"
            f"Action: {task.get('action', 'Continue Thought')}\n\n"
            f"Task Description:\n{task.get('title', 'No title')}\n\n"
            f"Task Prompt:\n{task.get('prompt', 'No prompt provided')}\n\n"
            f"Conversation Context:\n{conversation_context}\n\n"
            f"Project Context Summary:\n"
            f"Files analyzed: {len(project_context.get('files', []))}\n"
            f"Project root: {project_context.get('project_root', 'Unknown')}\n\n"
        )
        
        # Add action-specific instructions
        if action == "implement":
            base_prompt += (
                "Implementation Instructions:\n"
                "1. Analyze requirements and project context\n"
                "2. Design a modular, testable solution\n"
                "3. Implement with proper error handling\n"
                "4. Add necessary documentation\n"
                "5. Consider adding unit tests\n"
            )
        elif action == "refactor":
            base_prompt += (
                "Refactoring Instructions:\n"
                "1. Analyze current code structure\n"
                "2. Identify code smells and improvement areas\n"
                "3. Apply SOLID principles\n"
                "4. Ensure test coverage is maintained\n"
                "5. Document architectural decisions\n"
            )
        elif action == "test":
            base_prompt += (
                "Testing Instructions:\n"
                "1. Identify critical test scenarios\n"
                "2. Write comprehensive unit tests\n"
                "3. Include edge cases and error conditions\n"
                "4. Ensure proper test isolation\n"
                "5. Add test documentation\n"
            )
        elif action == "debug":
            base_prompt += (
                "Debugging Instructions:\n"
                "1. Analyze error symptoms and context\n"
                "2. Add strategic logging/debugging\n"
                "3. Identify and fix root cause\n"
                "4. Add regression tests\n"
                "5. Document the fix and prevention\n"
            )
        else:
            base_prompt += (
                "General Instructions:\n"
                "1. Analyze the task and context\n"
                "2. Execute the required changes\n"
                "3. Provide clear documentation\n"
            )
        
        return base_prompt
    
    def _get_task_metrics(self, task_id: str) -> Dict[str, Any]:
        """Get metrics for a specific task."""
        metrics = {
            "prompt_count": 0,
            "execution_cycles": 0,
            "average_completion_time": 0,
            "success_rate": 0.0
        }
        
        # Try to get metrics from services
        metrics_service = self.services.get('metrics_service')
        if metrics_service and hasattr(metrics_service, 'get_task_metrics'):
            try:
                metrics.update(metrics_service.get_task_metrics(task_id))
            except Exception as e:
                self.logger.warning(f"Failed to get metrics for task {task_id}: {e}")
        
        return metrics
    
    def _get_cursor_rules(self) -> Dict[str, Any]:
        """Get current Cursor rules and constraints."""
        rules = {
            "max_file_length": 400,
            "require_tests": True,
            "enforce_architecture": True
        }
        
        # Try to get rules from services
        rules_service = self.services.get('rules_service')
        if rules_service and hasattr(rules_service, 'get_current_rules'):
            try:
                rules.update(rules_service.get_current_rules())
            except Exception as e:
                self.logger.warning(f"Failed to get Cursor rules: {e}")
        
        return rules

    def _on_recovery_dashboard_refresh(self):
        """Handle recovery dashboard refresh request."""
        try:
            stats = self.recovery_engine.get_recovery_stats()
            self.statusBar().showMessage(
                f"Recovery insights updated - Success rate: {stats['global_metrics']['recovery_success_rate']:.1f}%"
            )
        except Exception as e:
            self.logger.error(f"Failed to refresh recovery insights: {e}")

if __name__ == "__main__":
    try:
        # Create the application
        app = QApplication(sys.argv)
        
        # Create and show the main window
        window = DreamOsMainWindow()
        window.show()
        
        self.logger.info("Dream.OS application started")
        
        # Start the event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        self.logger.error(f"Failed to start Dream.OS: {e}")
        raise
