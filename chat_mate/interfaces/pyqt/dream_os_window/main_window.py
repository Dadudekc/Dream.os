"""
Main window implementation for Dream.OS.
"""

import logging
import signal
from typing import Optional

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QThread, QCoreApplication

from core.system.startup_validator import StartupValidator
from core.PathManager import PathManager

from .services.service_container import ServiceContainer
from .handlers.assistant_handler import AssistantHandler
from .ui.window_ui import WindowUI
from .ui.signal_handlers import SignalHandlers


class DreamOsMainWindow(QMainWindow):
    """
    Main window for the Dreamscape application.
    Provides a decoupled interface with signal dispatching and async task support.
    """

    def __init__(self, ui_logic, dispatcher, services=None, event_loop_manager=None):
        """
        Initialize the main window with UI logic, signal dispatcher, and services.
        
        Args:
            ui_logic: UI logic instance
            dispatcher: Signal dispatcher instance
            services: Optional dictionary of service instances
            event_loop_manager: Optional event loop manager instance
        """
        super().__init__()
        
        # Initialize core attributes
        self.ui_logic = ui_logic
        self.dispatcher = dispatcher
        self.event_loop_manager = event_loop_manager
        
        # Initialize service container
        self.service_container = ServiceContainer()
        self.service_container.initialize_services(services)
        self.logger = self.service_container.get_service('logger') or logging.getLogger("DreamOsMainWindow")
        
        # Run startup validation
        self._run_startup_validation()
        
        # Initialize UI components
        self.window_ui = WindowUI(self, self.logger)
        self.signal_handlers = SignalHandlers(self.window_ui, self.logger)
        
        # Initialize assistant handler
        self.assistant_handler = AssistantHandler(self.window_ui, self.logger)
        self.assistant_handler.set_services(
            self.service_container.openai_client,
            self.service_container.assistant_controller,
            self.service_container.engine
        )
        
        # Set up UI and signals
        self._verify_services()
        self._setup_ui()
        self._setup_signals()
        
        self.logger.info("DreamOsMainWindow initialized")
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
    def _run_startup_validation(self) -> None:
        """Run startup validation and handle results."""
        validator = StartupValidator(PathManager(), logger=self.logger)
        startup_report = validator.run_all_checks()
        
        if startup_report["errors"]:
            self.logger.error("❌ Critical startup validation errors occurred:")
            for error in startup_report["errors"]:
                self.logger.error(f"  - {error}")
        else:
            self.logger.info("✅ Dream.OS validated and ready.")
            
        # Store warnings for display in status area
        self.startup_warnings = startup_report.get("warnings", [])
        
    def _verify_services(self) -> None:
        """Verify that essential services are available."""
        validation_results = self.service_container.validate_services()
        self.service_warnings = validation_results['warnings']
        
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.window_ui.setup_ui(self.service_container.services, self.dispatcher, self.ui_logic)
        if self.startup_warnings:
            self.window_ui.show_startup_warnings(self.startup_warnings)
            
    def _setup_signals(self) -> None:
        """Set up signal connections."""
        self.signal_handlers.setup_signals(self.dispatcher, self.ui_logic)
        
        # Connect button signals to assistant handler
        self.window_ui.openai_login_button.clicked.connect(self.assistant_handler.handle_openai_login)
        self.window_ui.scan_button.clicked.connect(self.assistant_handler.handle_scan)
        self.window_ui.start_button.clicked.connect(self.assistant_handler.start_assistant)
        self.window_ui.stop_button.clicked.connect(self.assistant_handler.stop_assistant)
        self.window_ui.send_button.clicked.connect(self.assistant_handler.send_message)
        
    def closeEvent(self, event) -> None:
        """
        Handle the window close event.
        
        Args:
            event: Close event instance
        """
        self.logger.info("🛑 Shutting down DreamOs...")
        
        # Shutdown all services
        self.service_container.shutdown_services()
        
        # Accept the event
        event.accept()
        
        # Ensure application exits
        QCoreApplication.exit(0)
        
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            self.logger.info("Received interrupt signal, shutting down...")
            self.close()
            
        # Only set handler if in the main thread
        if QThread.currentThread() == QCoreApplication.instance().thread():
            signal.signal(signal.SIGINT, signal_handler)
            self.logger.info("Signal handlers set up successfully") 