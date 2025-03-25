#!/usr/bin/env python3
import sys
import os
import logging
import asyncio

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication, QLabel
from PyQt5.QtCore import pyqtSlot
from qasync import QEventLoop

# Import our tab container and UI logic
from interfaces.pyqt.tabs.MainTabs import MainTabs
from interfaces.pyqt.dreamscape_ui_logic import DreamscapeUILogic

# Import our centralized signal dispatcher
from utils.signal_dispatcher import SignalDispatcher

# Import configuration and service loader
from core.ConfigManager import ConfigManager
from interfaces.pyqt.dreamscape_services import DreamscapeService


class DreamscapeMainWindow(QMainWindow):
    """
    Main window for the Dreamscape application.
    Provides a modern, decoupled interface with signal dispatching and async task support.
    """

    def __init__(self, ui_logic: DreamscapeUILogic, dispatcher: SignalDispatcher, services=None):
        """
        Initialize the main window with UI logic, signal dispatcher, and services.
        
        Args:
            ui_logic: The UI logic controller for business logic delegation
            dispatcher: Signal dispatcher for communication between components
            services: Dictionary of service objects for dependency injection
        """
        super().__init__()
        self.ui_logic = ui_logic
        self.dispatcher = dispatcher
        self.services = services or {}
        self.logger = self.services.get('logger', logging.getLogger("DreamscapeMainWindow"))

        # Verify essential services
        self.verify_services()
        
        self.setup_ui()
        self.setup_signals()

        self.logger.info("DreamscapeMainWindow initialized")

    def verify_services(self):
        """
        Verify that essential services are available and log any issues.
        This helps identify missing dependencies early.
        """
        essential_services = [
            'prompt_manager', 'chat_manager', 'response_handler', 
            'memory_manager', 'discord_service'
        ]
        
        for service_name in essential_services:
            service = self.services.get(service_name)
            if service is None:
                self.logger.error(f"Error: Service '{service_name}' not available - services not initialized")
            elif isinstance(service, EmptyService):
                # This is an EmptyService stub
                self.logger.warning(f"Warning: Service '{service_name}' is using an empty implementation")
                
        # Also check if extra_dependencies has the necessary services
        extra_deps = self.services.get('extra_dependencies', {})
        if not extra_deps:
            self.logger.warning("No extra dependencies provided - some functionality may be limited")
            return
            
        extra_essentials = ['cycle_service', 'task_orchestrator', 'dreamscape_generator']
        for dep_name in extra_essentials:
            if dep_name not in extra_deps or extra_deps[dep_name] is None:
                self.logger.warning(f"Missing extra dependency: '{dep_name}'")

    def setup_ui(self):
        """
        Set up the user interface components.
        Initializes the main layout and tabs.
        """
        self.setWindowTitle("Dreamscape - AI-Powered Community Management")
        self.setMinimumSize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Instantiate MainTabs with injected services and dispatcher
        try:
            self.tabs = MainTabs(
                dispatcher=self.dispatcher,
                config_manager=self.services.get('config_manager'),
                logger=self.services.get('logger'),
                extra_dependencies={
                    'service': self.services.get('dreamscape_service'),
                    'command_handler': self.services.get('response_handler'),
                    'discord_manager': self.services.get('discord_manager')
                }
            )
            layout.addWidget(self.tabs)
        except Exception as e:
            self.logger.error(f"Failed to initialize tabs: {str(e)}")
            error_label = QLabel(f"Error initializing application: {str(e)}")
            error_label.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(error_label)
            
        self.statusBar().showMessage("Ready")

    def setup_signals(self):
        """
        Connect signals between components for event-driven communication.
        Uses dispatcher to decouple signal sources from handlers.
        """
        try:
            # Connect dispatcher signals to local slots for centralized handling
            self.dispatcher.append_output.connect(self.on_append_output)
            self.dispatcher.status_update.connect(self.on_status_update)
            self.dispatcher.discord_log.connect(self.on_discord_log)

            # Connect task-related signals for async operation feedback
            self.dispatcher.task_started.connect(self.on_task_started)
            self.dispatcher.task_progress.connect(self.on_task_progress)
            self.dispatcher.task_completed.connect(self.on_task_completed)
            self.dispatcher.task_failed.connect(self.on_task_failed)

            # Let UI logic emit signals via the dispatcher
            if self.ui_logic:
                self.ui_logic.set_output_signal(self.dispatcher.emit_append_output)
                self.ui_logic.set_status_update_signal(self.dispatcher.emit_status_update)
                self.ui_logic.set_discord_log_signal(self.dispatcher.emit_discord_log)
        except Exception as e:
            self.logger.error(f"Failed to set up signals: {str(e)}")

    @pyqtSlot(str)
    def on_append_output(self, message):
        self.tabs.append_output(message)

    @pyqtSlot(str)
    def on_status_update(self, message):
        self.statusBar().showMessage(message)
        self.tabs.append_output(f"[Status] {message}")

    @pyqtSlot(str)
    def on_discord_log(self, message):
        self.tabs.append_output(f"[Discord] {message}")

    @pyqtSlot(str)
    def on_task_started(self, task_id):
        self.statusBar().showMessage(f"Task {task_id} started")
        self.tabs.append_output(f"[Task] {task_id} started")

    @pyqtSlot(str, int, str)
    def on_task_progress(self, task_id, progress, message):
        self.statusBar().showMessage(f"Task {task_id}: {progress}% - {message}")
        self.tabs.append_output(f"[Task] {task_id}: {progress}% - {message}")

    @pyqtSlot(str, dict)
    def on_task_completed(self, task_id, result):
        self.statusBar().showMessage(f"Task {task_id} completed")
        self.tabs.append_output(f"[Task] {task_id} completed successfully")

    @pyqtSlot(str, str)
    def on_task_failed(self, task_id, error):
        error_msg = f"Task {task_id} failed: {error}"
        self.statusBar().showMessage(error_msg)
        self.tabs.append_output(f"[Error] {error_msg}")

    def closeEvent(self, event):
        """
        Handle window close event.
        Ensures proper shutdown of all services and resources.
        
        Args:
            event: The close event
        """
        # Diagnostic output
        self.logger.info("Shutting down application and cleaning up services...")
        
        # Stop any refresh timers in tabs
        try:
            for tab in getattr(self.tabs, 'tabs', {}).values():
                timer = getattr(tab, 'refresh_timer', None)
                if timer:
                    timer.stop()
                    self.logger.debug(f"Stopped refresh timer for tab {tab}")
        except Exception as e:
            self.logger.error(f"Error stopping refresh timers: {str(e)}")

        # Shutdown services gracefully with error handling
        services_to_shutdown = [
            ('chat_manager', 'shutdown_driver'),
            ('discord_service', 'stop'),
            ('cursor_manager', 'shutdown_all'),
            ('task_orchestrator', 'stop'),
            ('cycle_service', 'stop'),
        ]
        
        for service_name, method_name in services_to_shutdown:
            try:
                service = self.services.get(service_name)
                if service and hasattr(service, method_name):
                    self.logger.info(f"Shutting down {service_name}...")
                    method = getattr(service, method_name)
                    method()
            except Exception as e:
                self.logger.error(f"Error shutting down {service_name}: {str(e)}")
            
        # Shutdown UI logic last
        try:
            if self.ui_logic and hasattr(self.ui_logic, 'shutdown'):
                self.logger.info("Shutting down UI logic...")
                self.ui_logic.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down UI logic: {str(e)}")
                
        self.logger.info("All services shutdown completed.")
        event.accept()


class EmptyService:
    """
    Empty service implementation for graceful fallback when a service is unavailable.
    Logs warnings when methods are called instead of raising exceptions.
    """
    def __init__(self, name):
        """
        Initialize the empty service.
        
        Args:
            name: The name of the service for logging purposes
        """
        self.service_name = name
        self.logger = logging.getLogger(f"EmptyService.{name}")
        
    def __getattr__(self, attr_name):
        """
        Dynamic method resolution to handle any method call.
        
        Args:
            attr_name: The name of the called method
            
        Returns:
            A function that logs a warning and returns None
        """
        def method(*args, **kwargs):
            self.logger.warning(
                f"Call to unavailable service '{self.service_name}.{attr_name}()'. "
                f"Service not initialized or unavailable."
            )
            return None
        return method


# -------------------------------------------------------------------------
# Unified Entry Point using QAsyncEventLoopManager for async/await support
# -------------------------------------------------------------------------
def main():
    """
    Main entry point for the DreamscapeMainWindow application.
    Handles service initialization, UI setup, and event loop management.
    """
    # Set up logging early
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger()
    logger.info("Starting DreamscapeMainWindow application")

    app = QApplication(sys.argv)

    # Initialize the qasync event loop manager for async task support
    from utils.qasync_event_loop_manager import QAsyncEventLoopManager
    event_loop_manager = QAsyncEventLoopManager(app, logger=logging.getLogger("QAsyncEventLoop"))
    logger.info("Async event loop initialized")

    # Initialize dispatcher for signal/slot communication between components
    dispatcher = SignalDispatcher()
    
    # Load configuration with error handling
    try:
        config = ConfigManager(config_name="dreamscape_config.yaml")
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        config = type('ConfigStub', (), {'get': lambda *args, **kwargs: None})
    
    # Initialize the Dreamscape service with proper error handling
    try:
        service = DreamscapeService(config=config)
        logger.info("DreamscapeService initialized successfully")
        
        # Bootstrap all services with proper dependency handling
        bootstrap_success = service.bootstrap_services()
        if bootstrap_success:
            logger.info("All critical services bootstrapped successfully")
        else:
            logger.warning("Some critical services failed to initialize properly")
    except Exception as e:
        logger.error(f"Failed to initialize DreamscapeService: {str(e)}")
        service = type('ServiceStub', (), {
            'prompt_manager': None,
            'chat_manager': None,
            'prompt_handler': None,
            'discord': None,
            'reinforcement_engine': None,
            'cycle_service': None,
            'task_orchestrator': None,
            'dreamscape_generator': None
        })

    # Initialize UI logic layer
    ui_logic = DreamscapeUILogic()
    ui_logic.service = service  # Connect service to UI logic
    logger.info("UI logic initialized")

    # Create an ordered dictionary of all required services
    # This ensures proper service references are maintained
    services = {
        'config_manager': config,
        'logger': logger,
        'dreamscape_service': service,
        'prompt_manager': _ensure_service(service.get_service('prompt_manager'), "prompt_manager", logger),
        'chat_manager': _ensure_service(service.get_service('chat_manager'), "chat_manager", logger),
        'response_handler': _ensure_service(service.get_service('prompt_handler'), "response_handler", logger),
        'memory_manager': _ensure_service(service.get_service('prompt_manager'), "memory_manager", logger),
        'discord_service': _ensure_service(service.discord, "discord_service", logger),
        'discord_manager': _ensure_service(service.discord, "discord_manager", logger),
        'fix_service': _ensure_service(service.get_service('reinforcement_engine'), "fix_service", logger),
        'rollback_service': _ensure_service(service.get_service('reinforcement_engine'), "rollback_service", logger),
        'cursor_manager': None,  # Will be initialized separately
        'extra_dependencies': {
            # Supporting services that might be needed by tabs
            'cycle_service': _ensure_service(service.get_service('cycle_service'), "cycle_service", logger),
            'task_orchestrator': _ensure_service(service.get_service('task_orchestrator'), "task_orchestrator", logger),
            'dreamscape_generator': _ensure_service(service.get_service('dreamscape_generator'), "dreamscape_generator", logger),
            'prompt_handler': _ensure_service(service.get_service('prompt_handler'), "prompt_handler", logger),
            'response_handler': _ensure_service(service.get_service('prompt_handler'), "response_handler", logger),
            'service': service  # Pass the full service for convenience
        }
    }

    # Initialize cursor manager if needed
    try:
        from core.CursorSessionManager import CursorSessionManager
        cursor_url = config.get("cursor_url", "http://localhost:8000") if hasattr(config, "get") else getattr(config, "cursor_url", "http://localhost:8000")
        services['cursor_manager'] = CursorSessionManager(config, services['memory_manager'])
        logger.info("Cursor manager initialized successfully")
    except (ImportError, Exception) as e:
        logger.warning(f"Cursor manager could not be initialized: {str(e)}")
        services['cursor_manager'] = _create_empty_service("cursor_manager", logger)

    # Log service status
    for service_name, service_obj in services.items():
        if service_name != 'extra_dependencies':
            status = "available" if service_obj is not None else "unavailable"
            logger.info(f"Service '{service_name}' is {status}")
    
    # Create, show and run the main window
    try:
        window = DreamscapeMainWindow(ui_logic, dispatcher, services=services)
        window.show()
        logger.info("Main window initialized and displayed")
        
        # Start the async event loop
        event_loop_manager.start()
        logger.info("Application event loop started")
        
        # Run the application
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        sys.exit(1)


def _ensure_service(service, service_name, logger):
    """
    Ensure a service is available or create an empty service implementation.
    
    Args:
        service: The service object or None
        service_name: The name of the service for logging
        logger: Logger to record issues
        
    Returns:
        The service object or an empty stub implementation
    """
    if service is None:
        logger.warning(f"Service '{service_name}' not available - creating empty implementation")
        return _create_empty_service(service_name, logger)
    return service


def _create_empty_service(service_name, logger):
    """
    Create an empty service implementation that logs warnings when methods are called.
    
    Args:
        service_name: The name of the missing service
        logger: Logger to use for warnings
        
    Returns:
        A dynamic object that implements a warning-logging proxy
    """
    return EmptyService(service_name)


if __name__ == "__main__":
    main()
