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
    QStatusBar
)
from PyQt5.QtCore import Qt, pyqtSignal

# Import core components
from core.TemplateManager import TemplateManager
from core.config.config_manager import ConfigManager
from core.PathManager import PathManager
from core.recovery.recovery_engine import RecoveryEngine

# Import tabs
from .tabs.dreamscape.DreamscapeGenerationTab import DreamscapeGenerationTab
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
from .services.TabValidatorService import TabValidatorService

class MockService:
    """Mock service for development/testing."""
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"mock.{name}")
        
    def __getattr__(self, name):
        def mock_method(*args, **kwargs):
            self.logger.warning(f"Mock {self.name}.{name} called")
            return None
        return mock_method

class DreamOsMainWindow(QMainWindow):
    """Main window for the Dream.OS interface."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        self.setWindowTitle("Dream.OS")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize core managers
        self.config_manager = ConfigManager()
        self.path_manager = PathManager()
        
        # Initialize services
        self.services = self._initialize_services()
        
        # Validate tab constructors
        self.tab_validator = TabValidatorService(self.services)
        validation_results = self.tab_validator.validate_all_tabs()
        
        # Initialize UI
        self._init_ui()
        
        # Log validation results
        for tab_name, is_valid in validation_results.items():
            status = "✅" if is_valid else "❌"
            logger.info(f"{status} Tab '{tab_name}' validation: {'passed' if is_valid else 'failed'}")
        
        # Show ready status
        self.statusBar().showMessage("Dream.OS Ready")
        
    def _initialize_services(self) -> Dict[str, Any]:
        """Initialize required services.
        
        Returns:
            Dictionary of initialized services
        """
        services = {
            'core_services': {},
            'component_managers': {}
        }
        
        # Initialize template manager
        try:
            template_manager = TemplateManager(
                template_dir=self.path_manager.get_path('templates'),
                logger=logger
            )
            services['component_managers']['template_manager'] = template_manager
            logger.info("Template manager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize template manager: {str(e)}")
            services['component_managers']['template_manager'] = MockService('template_manager')
            
        # Initialize system loader for dependency injection
        try:
            from core.system_loader import DreamscapeSystemLoader
            system_loader = DreamscapeSystemLoader.get_instance()
            system_loader.load_config()
            services['system_loader'] = system_loader
            logger.info("DreamscapeSystemLoader initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize DreamscapeSystemLoader: {str(e)}")
            services['system_loader'] = MockService('system_loader')
        
        # Initialize prompt cycle orchestrator
        try:
            from core.prompt_cycle_orchestrator import PromptCycleOrchestrator
            orchestrator = PromptCycleOrchestrator()
            services['prompt_cycle_orchestrator'] = orchestrator
            
            # Register with system loader
            if 'system_loader' in services and not isinstance(services['system_loader'], MockService):
                services['system_loader'].register_service('prompt_cycle_orchestrator', orchestrator)
                
            logger.info("PromptCycleOrchestrator initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize PromptCycleOrchestrator: {str(e)}")
            services['prompt_cycle_orchestrator'] = MockService('prompt_cycle_orchestrator')
            
        # Initialize other critical core services (mock if needed)
        core_service_names = ['task_orchestrator']
        for name in core_service_names:
             if name not in services['core_services']:
                 services['core_services'][name] = MockService(name)
                 logger.info(f"Using mock {name} for development")

        # Initialize other component managers (mock if needed)
        component_manager_names = ['episode_generator', 'ui_manager'] # Add others as needed
        for name in component_manager_names:
             if name not in services['component_managers']:
                 services['component_managers'][name] = MockService(name)
                 logger.info(f"Using mock {name} for development")
            
        # Keep flat structure for other base services if used directly
        base_service_names = [
            'prompt_service',
            'web_scraper',
            'episode_service', # Keep this if PromptSyncTab uses it directly
            'export_service'
        ]
        for name in base_service_names:
            if name not in services:
                 services[name] = MockService(name)
                 logger.info(f"Using mock {name} for development")
        
        # Initialize CursorSessionManager
        try:
            from chat_mate.core.refactor.CursorSessionManager import CursorSessionManager
            cursor_session_manager = CursorSessionManager(
                project_root=str(self.path_manager.get_path('project_root')),
                dry_run=False  # Set to True for testing without actual UI interaction
            )
            # Start the background loop
            cursor_session_manager.start_loop()
            services['cursor_session_manager'] = cursor_session_manager
            logger.info("CursorSessionManager initialized and started")
        except Exception as e:
            logger.warning(f"Failed to initialize CursorSessionManager: {str(e)}")
            services['cursor_session_manager'] = MockService('cursor_session_manager')
            
        # Initialize ProjectScanner
        try:
            from interfaces.pyqt.services.ProjectScanner import ProjectScanner
            project_scanner = ProjectScanner(
                project_root=str(self.path_manager.get_path('project_root')),
                cache_path=str(self.path_manager.get_path('cache') / 'analysis_cache.json')
            )
            # Load existing cache or perform initial scan
            if not project_scanner.load_cache()["files"]:
                # Perform initial scan with limited scope for speed
                project_scanner.scan_project(max_files=100)
            services['project_scanner'] = project_scanner
            logger.info("ProjectScanner initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize ProjectScanner: {str(e)}")
            services['project_scanner'] = MockService('project_scanner')
            
        # Initialize metrics service
        try:
            metrics_dir = Path("metrics")
            self.metrics_service = MetricsService(metrics_dir)
            logger.info("Initialized metrics service")
            
            # Initialize recovery engine
            self.recovery_engine = RecoveryEngine(
                cursor_session=services.get('cursor_session_manager'),
                metrics_service=self.metrics_service
            )
            logger.info("Initialized recovery engine")
            
            # Add services to services dict
            services["metrics"] = self.metrics_service
            services["recovery"] = self.recovery_engine
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
        
        return services
        
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
        self.main_tab = MainTab(self.services)
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
        
        self.chat_widget = self.chat_tab_manager.get_widget()
        self.tab_widget.addTab(self.chat_widget, "Chat")
        
        # Group 3: Content Generation
        self.dreamscape_tab = DreamscapeGenerationTab(self.services)
        self.tab_widget.addTab(self.dreamscape_tab, "Dreamscape Generation")
        
        self.prompt_execution_tab = PromptExecutionTab(self.services)
        self.tab_widget.addTab(self.prompt_execution_tab, "Prompt Execution")
        
        # Group 4: Social and Dashboard
        self.social_dashboard_tab = SocialDashboardTab(self.services)
        self.tab_widget.addTab(self.social_dashboard_tab, "Social Dashboard")
        
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
        
        self.logs_tab = LogsTab(self.services)
        self.tab_widget.addTab(self.logs_tab, "Logs")
        
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
        # Save any necessary state
        if hasattr(self.prompt_sync_tab, '_save_state'):
            self.prompt_sync_tab._save_state()
            
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
            logger.error(f"Task execution failed: {e}")
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
            logger.error(f"Failed to refresh recovery insights: {e}")

if __name__ == "__main__":
    try:
        # Create the application
        app = QApplication(sys.argv)
        
        # Create and show the main window
        window = DreamOsMainWindow()
        window.show()
        
        logger.info("Dream.OS application started")
        
        # Start the event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"Failed to start Dream.OS: {e}")
        raise
