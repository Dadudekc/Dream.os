#!/usr/bin/env python3
import sys
import os
import logging
import asyncio

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QApplication, QLabel, QHBoxLayout,
    QPushButton, QTextEdit, QMessageBox, QTabWidget
)
from PyQt5.QtCore import pyqtSlot, Qt

from qasync import QEventLoop

# Import our tab container and UI logic
from interfaces.pyqt.tabs.MainTabs import MainTabs
from interfaces.pyqt.dreamscape_ui_logic import DreamscapeUILogic

# Import our centralized signal dispatcher
from utils.signal_dispatcher import SignalDispatcher

# Import configuration and service loader
from core.ConfigManager import ConfigManager
from interfaces.pyqt.dreamscape_services import DreamscapeService
from core.chatgpt_automation.automation_engine import AutomationEngine
from core.chatgpt_automation.controllers.assistant_mode_controller import AssistantModeController


class DreamscapeMainWindow(QMainWindow):
    """
    Main window for the Dreamscape application.
    Provides a decoupled interface with signal dispatching and async task support.
    """

    def __init__(self, ui_logic: DreamscapeUILogic, dispatcher: SignalDispatcher, services=None):
        """
        Initialize the main window with UI logic, signal dispatcher, and services.
        """
        super().__init__()
        self.ui_logic = ui_logic
        self.dispatcher = dispatcher
        self.services = services or {}
        self.logger = self.services.get('logger', logging.getLogger("DreamscapeMainWindow"))

        # Initialize engine and assistant controller
        try:
            self.engine = AutomationEngine(use_local_llm=True, model_name='mistral')
            self.assistant_controller = AssistantModeController(self.engine)
        except Exception as e:
            self.logger.error(f"Failed to initialize automation engine or assistant controller: {str(e)}")

        self.verify_services()
        self.setup_ui()
        self.setup_signals()

        self.logger.info("DreamscapeMainWindow initialized")

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

    def handle_scan(self):
        """Handle the scan project button click."""
        success, message = self.engine.scan_project_gui()
        QMessageBox.information(self, "Project Scan", message)

    def start_assistant(self):
        """Start the assistant mode and monitor browser login."""
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
        Handle window close event.
        Ensures proper shutdown of services and resources.
        """
        self.logger.info("Shutting down application and cleaning up services...")
        try:
            if hasattr(self, 'assistant_controller'):
                self.logger.info("Stopping assistant controller...")
                self.assistant_controller.stop()
            if hasattr(self, 'engine') and self.engine and hasattr(self.engine, 'shutdown'):
                self.logger.info("Shutting down automation engine...")
                self.engine.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down automation components: {str(e)}")
        try:
            if self.tabs and hasattr(self.tabs, 'tabs'):
                for tab_name, tab in self.tabs.tabs.items():
                    if hasattr(tab, 'refresh_timer') and tab.refresh_timer:
                        self.logger.info(f"Stopping refresh timer for {tab_name} tab...")
                        tab.refresh_timer.stop()
                    if hasattr(tab, 'running_tasks'):
                        task_count = len(tab.running_tasks)
                        if task_count > 0:
                            self.logger.info(f"Canceling {task_count} running tasks in {tab_name} tab...")
                            for task in list(tab.running_tasks.values()):
                                try:
                                    task.cancel()
                                except Exception:
                                    pass
                    if hasattr(tab, 'shutdown'):
                        self.logger.info(f"Shutting down {tab_name} tab...")
                        try:
                            tab.shutdown()
                        except Exception as tab_e:
                            self.logger.error(f"Error shutting down {tab_name} tab: {tab_e}")
        except Exception as e:
            self.logger.error(f"Error stopping timers and tasks: {str(e)}")
        services_to_shutdown = [
            ('chat_manager', 'shutdown_driver'),
            ('discord_service', 'stop'),
            ('cursor_manager', 'shutdown_all'),
            ('task_orchestrator', 'stop'),
            ('cycle_service', 'stop'),
            ('dreamscape_generator', 'shutdown')
        ]
        for service_name, method_name in services_to_shutdown:
            try:
                service = self.services.get(service_name)
                if service and hasattr(service, method_name):
                    self.logger.info(f"Shutting down {service_name}...")
                    getattr(service, method_name)()
                else:
                    self.logger.debug(f"Service '{service_name}.{method_name}()' not available for shutdown.")
            except Exception as e:
                self.logger.error(f"Error shutting down {service_name}: {str(e)}")
        try:
            if self.ui_logic and hasattr(self.ui_logic, 'shutdown'):
                self.logger.info("Shutting down UI logic...")
                self.ui_logic.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down UI logic: {str(e)}")
        try:
            if 'chat_manager' in self.services:
                chat_manager = self.services['chat_manager']
                if hasattr(chat_manager, 'driver') and chat_manager.driver:
                    self.logger.info("Forcing browser shutdown...")
                    try:
                        chat_manager.driver.quit()
                    except Exception:
                        pass
        except Exception as e:
            self.logger.error(f"Error forcing browser shutdown: {str(e)}")
        try:
            app = QApplication.instance()
            event_loop_manager = None
            if hasattr(app, 'eventLoop'):
                event_loop_manager = app.eventLoop
            elif 'event_loop_manager' in self.services:
                event_loop_manager = self.services['event_loop_manager']
            if event_loop_manager and hasattr(event_loop_manager, 'shutdown'):
                self.logger.info("Stopping event loop manager...")
                event_loop_manager.shutdown()
            else:
                self.logger.info("No event loop manager found, trying direct asyncio shutdown...")
                try:
                    loop = asyncio.get_event_loop()
                    if loop and loop.is_running():
                        for task in asyncio.all_tasks(loop):
                            if not task.done():
                                task.cancel()
                        loop.call_soon_threadsafe(loop.stop)
                except Exception as loop_e:
                    self.logger.error(f"Error in direct asyncio shutdown: {str(loop_e)}")
        except Exception as e:
            self.logger.error(f"Error stopping event loop: {str(e)}")
        try:
            import threading
            threading.Timer(3.0, lambda: os._exit(0)).start()
            self.logger.info("Force exit timer set for 3 seconds as fallback")
        except Exception as timer_e:
            self.logger.error(f"Error setting force exit timer: {str(timer_e)}")
        self.logger.info("All services shutdown completed. Application closing.")
        event.accept()


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

    from utils.qasync_event_loop_manager import QAsyncEventLoopManager
    event_loop_manager = QAsyncEventLoopManager(app, logger=logging.getLogger("QAsyncEventLoop"))
    logger.info("Async event loop initialized")

    dispatcher = SignalDispatcher()

    try:
        config = ConfigManager(config_name="dreamscape_config.yaml")
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
        from core.CursorSessionManager import CursorSessionManager
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
        window = DreamscapeMainWindow(ui_logic, dispatcher, services=services)
        window.show()
        logger.info("Main window initialized and displayed")
        event_loop_manager.start()
        logger.info("Application event loop started")
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        sys.exit(1)


def _ensure_service(service, service_name, logger):
    if service is None:
        logger.warning(f"Service '{service_name}' not available - creating empty implementation")
        return _create_empty_service(service_name, logger)
    return service


def _create_empty_service(service_name, logger):
    return EmptyService(service_name)


if __name__ == "__main__":
    main()
