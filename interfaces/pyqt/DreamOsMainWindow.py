#!/usr/bin/env python3
import sys
import os
import logging
import asyncio
import warnings
import signal
from PyQt5 import QtCore, QtWidgets

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QApplication, QLabel, QHBoxLayout,
    QPushButton, QTextEdit, QMessageBox, QTabWidget
)
from PyQt5.QtCore import pyqtSlot, Qt, QThread

from qasync import QEventLoop

# Import our tab container and UI logic
from interfaces.pyqt.tabs.MainTabs import MainTabs
from interfaces.pyqt.dreamscape_ui_logic import DreamscapeUILogic

# Import our centralized signal dispatcher
from utils.signal_dispatcher import SignalDispatcher

# Import configuration and service loader
from config.ConfigManager import ConfigManager
from interfaces.pyqt.dreamscape_services import DreamscapeService
from core.chatgpt_automation.automation_engine import AutomationEngine
from core.chatgpt_automation.controllers.assistant_mode_controller import AssistantModeController
from core.chatgpt_automation.OpenAIClient import OpenAIClient
from core.system.startup_validator import StartupValidator
from core.PathManager import PathManager
from core.micro_factories.chat_factory import create_chat_manager
from core.PromptCycleOrchestrator import PromptCycleOrchestrator

# Suppress SIP deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning)

class DreamscapeMainWindow(QMainWindow):
    """
    Main window for the Dreamscape application.
    Provides a decoupled interface with signal dispatching and async task support.
    """

    def __init__(self, ui_logic: DreamscapeUILogic, dispatcher: SignalDispatcher, services=None, event_loop_manager=None):
        """
        Initialize the main window with UI logic, signal dispatcher, and services.
        """
        super().__init__()
        self.ui_logic = ui_logic
        self.dispatcher = dispatcher
        self.services = services or {}
        self.logger = self.services.get('logger', logging.getLogger("DreamscapeMainWindow"))
        self.event_loop_manager = event_loop_manager
        
        self.path_manager = PathManager()
        
        # Initialize OpenAI client
        try:
            profile_dir = os.path.join(self.path_manager.get_path("cache"), "openai_profile")
            self.openai_client = OpenAIClient(profile_dir=profile_dir)
            self.logger.info("OpenAI client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None
        
        # Initialize assistant controller
        try:
            self.assistant_controller = AssistantModeController(engine=self.openai_client)
            self.logger.info("Assistant controller initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize assistant controller: {e}")
            self.assistant_controller = None
        
        # Run startup validation
        self._run_startup_validation()
        
        self.verify_services()
        self.setup_ui()
        self.setup_signals()

        self.logger.info("DreamscapeMainWindow initialized")

        self.engine = AutomationEngine()  # Initialize engine for project scanning

        self._setup_signal_handlers()

    def verify_services(self):
        """
        Verify that essential services are available and log any issues.
        """
        essential_services = [
            'prompt_manager', 'chat_manager', 'response_handler',
            'memory_manager', 'discord_service'
        ]
        for service_name in essential_services:
            service = self.services.get(service_name)
            if service is None:
                self.logger.error(f"Error: Service '{service_name}' not available - services not initialized")
            elif hasattr(service, '__class__') and service.__class__.__name__ == "EmptyService":
                self.logger.warning(f"Warning: Service '{service_name}' is using an empty implementation")
        extra_deps = self.services.get('extra_dependencies', {})
        if not extra_deps:
            self.logger.warning("No extra dependencies provided - some functionality may be limited")
        else:
            extra_essentials = ['cycle_service', 'task_orchestrator', 'dreamscape_generator']
            for dep_name in extra_essentials:
                if dep_name not in extra_deps or extra_deps[dep_name] is None:
                    self.logger.warning(f"Missing extra dependency: '{dep_name}'")

    def setup_ui(self):
        """
        Set up the user interface components.
        """
        self.setWindowTitle("Dreamscape - AI-Powered Community Management")
        self.setMinimumSize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        try:
            self.tabs = MainTabs(
                dispatcher=self.dispatcher,
                ui_logic=self.ui_logic,
                config_manager=self.services.get('config_manager'),
                logger=self.services.get('logger'),
                prompt_manager=self.services.get('prompt_manager'),
                chat_manager=self.services.get('chat_manager'),
                memory_manager=self.services.get('memory_manager'),
                discord_manager=self.services.get('discord_service'),
                cursor_manager=self.services.get('cursor_manager'),
                **self.services.get('extra_dependencies', {})
            )
            layout.addWidget(self.tabs)
            self.logger.info("MainTabs initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize MainTabs: {e}")
            self.tabs = None
            fallback_tabs = QTabWidget()
            layout.addWidget(fallback_tabs)
            fallback_text = QTextEdit()
            fallback_text.setReadOnly(True)
            fallback_text.append("Tab initialization failed. Check logs for details.")
            fallback_text.append(f"Error: {str(e)}")
            fallback_tabs.addTab(fallback_text, "Error Info")
            self.fallback_output = fallback_text

        self.button_layout = QHBoxLayout()

        # Add OpenAI Login Button
        self.openai_login_button = QPushButton("🔓 Check OpenAI Login")
        self.openai_login_button.clicked.connect(self.handle_openai_login)
        self.button_layout.addWidget(self.openai_login_button)

        self.scan_button = QPushButton("Scan Project")
        self.scan_button.clicked.connect(self.handle_scan)
        self.button_layout.addWidget(self.scan_button)

        self.start_button = QPushButton("Start Assistant")
        self.start_button.clicked.connect(self.start_assistant)
        self.button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Assistant")
        self.stop_button.clicked.connect(self.stop_assistant)
        self.stop_button.setEnabled(False)
        self.button_layout.addWidget(self.stop_button)

        layout.addLayout(self.button_layout)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        self.input_layout = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(100)
        self.input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.input_layout.addWidget(self.send_button)

        layout.addLayout(self.input_layout)

        self.statusBar().showMessage("Ready")

    def setup_signals(self):
        """
        Connect signals between components.
        """
        try:
            self.dispatcher.append_output.connect(self.on_append_output)
            self.dispatcher.status_update.connect(self.on_status_update)
            self.dispatcher.discord_log.connect(self.on_discord_log)
            self.dispatcher.task_started.connect(self.on_task_started)
            self.dispatcher.task_progress.connect(self.on_task_progress)
            self.dispatcher.task_completed.connect(self.on_task_completed)
            self.dispatcher.task_failed.connect(self.on_task_failed)
            if self.ui_logic:
                self.ui_logic.set_output_signal(self.dispatcher.emit_append_output)
                self.ui_logic.set_status_update_signal(self.dispatcher.emit_status_update)
                self.ui_logic.set_discord_log_signal(self.dispatcher.emit_discord_log)
        except Exception as e:
            self.logger.error(f"Failed to set up signals: {str(e)}")

    @pyqtSlot(str)
    def on_append_output(self, message):
        """
        Append a message to the output area.
        """
        if self.tabs:
            self.tabs.append_output(message)
        else:
            self.chat_display.append(message)
        self.statusBar().showMessage(message.split('\n')[0])

    @pyqtSlot(str)
    def on_status_update(self, message):
        """
        Update the status bar with a message.
        """
        if self.tabs:
            self.tabs.append_output(f"[Status] {message}")
        else:
            self.statusBar().showMessage(message)
        self.statusBar().showMessage(message)

    @pyqtSlot(str)
    def on_discord_log(self, message):
        """
        Log a Discord-related message.
        """
        output_text = f"[Discord] {message}"
        if self.tabs:
            self.tabs.append_output(output_text)
        elif hasattr(self, 'fallback_output'):
            self.fallback_output.append(output_text)
        else:
            self.chat_display.append(output_text)
        self.logger.info(output_text)

    @pyqtSlot(str)
    def on_task_started(self, task_id):
        status_message = f"Task {task_id} started"
        self.statusBar().showMessage(status_message)
        output_text = f"[Task] {task_id} started"
        if self.tabs:
            self.tabs.append_output(output_text)
        elif hasattr(self, 'fallback_output'):
            self.fallback_output.append(output_text)
        else:
            self.chat_display.append(output_text)
        self.logger.info(output_text)

    @pyqtSlot(str, int, str)
    def on_task_progress(self, task_id, progress, message):
        status_message = f"Task {task_id}: {progress}% - {message}"
        self.statusBar().showMessage(status_message)
        output_text = f"[Task] {task_id}: {progress}% - {message}"
        if self.tabs:
            self.tabs.append_output(output_text)
        elif hasattr(self, 'fallback_output'):
            self.fallback_output.append(output_text)
        else:
            self.chat_display.append(output_text)
        self.logger.info(output_text)

    @pyqtSlot(str, dict)
    def on_task_completed(self, task_id, result):
        status_message = f"Task {task_id} completed"
        self.statusBar().showMessage(status_message)
        output_text = f"[Task] {task_id} completed successfully"
        if self.tabs:
            self.tabs.append_output(output_text)
        elif hasattr(self, 'fallback_output'):
            self.fallback_output.append(output_text)
        else:
            self.chat_display.append(output_text)
        self.logger.info(output_text)

    @pyqtSlot(str, str)
    def on_task_failed(self, task_id, error):
        error_msg = f"Task {task_id} failed: {error}"
        self.statusBar().showMessage(error_msg)
        output_text = f"[Error] {error_msg}"
        if self.tabs:
            self.tabs.append_output(output_text)
        elif hasattr(self, 'fallback_output'):
            self.fallback_output.append(output_text)
        else:
            self.chat_display.append(output_text)
        self.logger.error(output_text)

    def handle_openai_login(self):
        """Handle OpenAI login process with proper initialization sequence."""
        try:
            if not self.openai_client:
                self.logger.error("OpenAI client not initialized")
                self.statusBar().showMessage("OpenAI client not initialized", 5000)
                return
                
            if not self.openai_client.is_ready():
                self.logger.info("Booting OpenAI client...")
                self.openai_client.boot()

            if self.openai_client.login_openai():
                self.logger.info("✅ OpenAI login successful")
                self.statusBar().showMessage("OpenAI login successful", 5000)
            else:
                self.logger.error("❌ OpenAI login failed")
                self.statusBar().showMessage("OpenAI login failed", 5000)
        except Exception as e:
            self.logger.error(f"OpenAI login error: {e}")
            try:
                if self.openai_client:
                    self.openai_client.shutdown()
            except Exception as shutdown_error:
                self.logger.error(f"OpenAI shutdown error: {shutdown_error}")
            self.statusBar().showMessage(f"OpenAI error: {str(e)}", 5000)

    def handle_scan(self):
        """Handle the scan project button click."""
        success, message = self.engine.scan_project_gui()
        QMessageBox.information(self, "Project Scan", message)

    def start_assistant(self):
        """Start the assistant mode and monitor browser login."""
        if not self.assistant_controller:
            self.logger.error("Cannot start assistant: AssistantModeController not initialized")
            QMessageBox.warning(self, "Error", "Assistant controller not initialized. Please check logs.")
            return
            
        self.assistant_controller.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        try:
            if self.engine and hasattr(self.engine, 'chat_manager'):
                chat_manager = self.engine.chat_manager
                if hasattr(chat_manager, 'is_logged_in') and chat_manager.is_logged_in():
                    self.logger.info("Browser login verified. Enabling voice mode...")
                    if hasattr(self.engine, 'enable_voice_mode'):
                        self.engine.enable_voice_mode()
                else:
                    self.logger.warning("Browser login not verified. Voice mode not enabled.")
        except Exception as e:
            self.logger.error(f"Error monitoring browser login: {str(e)}")

    def stop_assistant(self):
        """Stop the assistant mode."""
        if not self.assistant_controller:
            self.logger.error("Cannot stop assistant: AssistantModeController not initialized")
            return
            
        self.assistant_controller.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def send_message(self):
        """Send a message to the assistant."""
        message = self.input_field.toPlainText()
        if message:
            self.chat_display.append(f"You: {message}")
            response = self.engine.get_chatgpt_response(message)
            self.chat_display.append(f"Assistant: {response}")
            self.input_field.clear()

    def closeEvent(self, event):
        """
        Handle the window close event to ensure proper shutdown of all resources
        """
        self.logger.info("🛑 Shutting down DreamOs...")
        
        # Shutdown any OpenAI clients
        if hasattr(self, 'openai_client') and self.openai_client:
            try:
                self.openai_client.shutdown()
                self.logger.info("✅ OpenAI client shut down successfully")
            except Exception as e:
                self.logger.error(f"❌ Error shutting down OpenAI client: {e}")
        
        # Shutdown any service containers
        if hasattr(self, 'container') and self.container:
            try:
                for service_name in ['orchestrator', 'prompt_manager', 'chat_manager']:
                    service = getattr(self.container, service_name, None)
                    if service and hasattr(service, 'shutdown'):
                        service.shutdown()
                        self.logger.info(f"✅ Service {service_name} shut down successfully")
            except Exception as e:
                self.logger.error(f"❌ Error shutting down services: {e}")
        
        # Accept the event to close the window
        event.accept()
        
        # Ensure application fully exits
        QtWidgets.QApplication.exit(0)

    def _run_startup_validation(self):
        """Run startup validation and handle results."""
        validator = StartupValidator(self.path_manager, logger=self.logger)
        startup_report = validator.run_all_checks()

        if startup_report["errors"]:
            self.logger.error("❌ Critical startup validation errors occurred:")
            for error in startup_report["errors"]:
                self.logger.error(f"  - {error}")
        else:
            self.logger.info("✅ Dream.OS validated and ready.")

        # Store warnings for display in status area
        self.startup_warnings = startup_report.get("warnings", [])

    def _init_ui(self):
        """Initialize the main UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Add status bar for startup warnings
        if self.startup_warnings:
            warning_label = QLabel("⚠️ Startup Warnings Present")
            warning_label.setStyleSheet("color: orange;")
            layout.addWidget(warning_label)
        
        # Initialize tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

    def _init_tabs(self):
        """Initialize and add all tab widgets."""
        
        
    def log_message(self, message: str, level: str = "info"):
        """Log a message to both logger and relevant UI components."""
        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)
            
        # Update status bar or relevant UI component
        self.statusBar().showMessage(message, 5000)  # Show for 5 seconds

    def edit_file(self, target_file: str, instructions: str, code_edit: str) -> None:
        """Edit a file with the given instructions and code edit."""
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(code_edit)
        except Exception as e:
            self.logger.error(f"Failed to edit file {target_file}: {e}")

    def _setup_signal_handlers(self):
        """
        Set up signal handlers to ensure proper application shutdown
        on Ctrl+C or SIGINT events.
        """
        def signal_handler(sig, frame):
            self.logger.info("Received interrupt signal, shutting down...")
            if hasattr(self, 'window') and self.window:
                self.window.close()
            else:
                QtWidgets.QApplication.quit()
        
        # Only set handler if in the main thread
        if QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread():
            signal.signal(signal.SIGINT, signal_handler)
            self.logger.info("Signal handlers set up successfully")


class EmptyService:
    """
    Empty service implementation for graceful fallback when a service is unavailable.
    """
    def __init__(self, name):
        self.service_name = name
        self.logger = logging.getLogger(f"EmptyService.{name}")

    def __getattr__(self, attr_name):
        def method(*args, **kwargs):
            self.logger.warning(
                f"Call to unavailable service '{self.service_name}.{attr_name}()'. Service not initialized."
            )
            return None
        return method


def main():
    """
    Main entry point for the DreamscapeMainWindow application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger()
    logger.info("Starting DreamscapeMainWindow application")

    app = QApplication(sys.argv)

    # Create and configure event loop
    from utils.qasync_event_loop_manager import QAsyncEventLoopManager
    event_loop_manager = QAsyncEventLoopManager(app, logger=logging.getLogger("QAsyncEventLoop"))
    logger.info("Async event loop initialized")

    dispatcher = SignalDispatcher()

    try:
        # Initialize core services with proper dependency injection
        services = initialize_services()
        config_manager = services['config_manager']
        chat_manager = services['chat_manager']
        orchestrator = services['orchestrator']
        logger.info("Core services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize core services: {str(e)}")
        config_manager = ConfigManager()
        chat_manager = None
        orchestrator = None

    try:
        config = ConfigManager(config_name="base.yaml")
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        config = type('ConfigStub', (), {'get': lambda *args, **kwargs: None})

    try:
        service = DreamscapeService(config=config)
        logger.info("DreamscapeService initialized successfully")
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

    ui_logic = DreamscapeUILogic()
    ui_logic.service = service
    logger.info("UI logic initialized")

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
        'cursor_manager': None,
        'extra_dependencies': {
            'cycle_service': _ensure_service(service.get_service('cycle_service'), "cycle_service", logger),
            'task_orchestrator': _ensure_service(service.get_service('task_orchestrator'), "task_orchestrator", logger),
            'dreamscape_generator': _ensure_service(service.get_service('dreamscape_generator'), "dreamscape_generator", logger),
            'prompt_handler': _ensure_service(service.get_service('prompt_handler'), "prompt_handler", logger),
            'response_handler': _ensure_service(service.get_service('prompt_handler'), "response_handler", logger),
            'service': service
        }
    }

    try:
        from core.refactor.CursorSessionManager import CursorSessionManager
        cursor_url = config.get("cursor_url", "http://localhost:8000") if hasattr(config, "get") else getattr(config, "cursor_url", "http://localhost:8000")
        services['cursor_manager'] = CursorSessionManager(config, services['memory_manager'])
        logger.info("Cursor manager initialized successfully")
    except (ImportError, Exception) as e:
        logger.warning(f"Cursor manager could not be initialized: {str(e)}")
        services['cursor_manager'] = _create_empty_service("cursor_manager", logger)

    for service_name, service_obj in services.items():
        if service_name != 'extra_dependencies':
            status = "available" if service_obj is not None else "unavailable"
            logger.info(f"Service '{service_name}' is {status}")

    try:
        # Create and show main window
        window = DreamscapeMainWindow(ui_logic=DreamscapeUILogic(), 
                                    dispatcher=dispatcher, 
                                    services=services,
                                    event_loop_manager=event_loop_manager)
        window.show()  # Make window visible
        window.raise_()  # Bring window to front
        window.activateWindow()  # Give window focus
        logger.info("Main window initialized and displayed")
        
        # Start event loop
        event_loop_manager.start()
        logger.info("Application event loop started")
        
        # Run main loop
        return app.exec_()
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        return 1


def _ensure_service(service, service_name, logger):
    if service is None:
        logger.warning(f"Service '{service_name}' not available - creating empty implementation")
        return _create_empty_service(service_name, logger)
    return service


def _create_empty_service(service_name, logger):
    return EmptyService(service_name)


def initialize_services():
    """Initialize and connect core services with proper dependency injection."""
    try:
        # Use the SystemLoader to initialize all services
        from core.system_loader import SystemLoader
        
        # Create and boot the system loader
        loader = SystemLoader()
        services = loader.boot()
        
        # Get a reference to the ServiceRegistry for registering any additional services
        from core.services.service_registry import ServiceRegistry
        registry = ServiceRegistry()
        
        # Log initialization status
        logger = logging.getLogger("Services")
        for name, service in services.items():
            status = "✅ Available" if service else "⚠️ Empty implementation"
            logger.info(f"Service '{name}': {status}")
        
        return services
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


if __name__ == "__main__":
    sys.exit(main())
