#!/usr/bin/env python3
import sys
import os
import logging
import asyncio

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
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
        super().__init__()
        self.ui_logic = ui_logic
        self.dispatcher = dispatcher
        self.services = services or {}
        self.logger = logging.getLogger("DreamscapeMainWindow")

        self.setup_ui()
        self.setup_signals()

        self.logger.info("DreamscapeMainWindow initialized")

    def setup_ui(self):
        self.setWindowTitle("Dreamscape - AI-Powered Community Management")
        self.setMinimumSize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Instantiate MainTabs with injected services and dispatcher
        self.tabs = MainTabs(
            dispatcher=self.dispatcher,
            ui_logic=self.ui_logic,
            config_manager=self.services.get('config_manager'),
            logger=self.services.get('logger'),
            prompt_manager=self.services.get('prompt_manager'),
            chat_manager=self.services.get('chat_manager'),
            memory_manager=self.services.get('memory_manager'),
            discord_manager=self.services.get('discord_manager'),
            cursor_manager=self.services.get('cursor_manager'),
            **self.services.get('extra_dependencies', {})
        )
        layout.addWidget(self.tabs)
        self.statusBar().showMessage("Ready")

    def setup_signals(self):
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
        self.ui_logic.set_output_signal(self.dispatcher.emit_append_output)
        self.ui_logic.set_status_update_signal(self.dispatcher.emit_status_update)
        self.ui_logic.set_discord_log_signal(self.dispatcher.emit_discord_log)

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
        # Stop any refresh timers in tabs
        for tab in getattr(self.tabs, 'tabs', {}).values():
            timer = getattr(tab, 'refresh_timer', None)
            if timer:
                timer.stop()

        # Shutdown services gracefully
        chat_manager = self.services.get('chat_manager')
        discord_service = self.services.get('discord_service')
        if chat_manager:
            chat_manager.shutdown_driver()
        if discord_service:
            discord_service.stop()
        if self.ui_logic:
            self.ui_logic.shutdown()

        event.accept()


# -------------------------------------------------------------------------
# Unified Entry Point using QAsyncEventLoopManager for async/await support
# -------------------------------------------------------------------------
def main():
    # Set up logging early
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    app = QApplication(sys.argv)

    # Initialize the qasync event loop manager
    from utils.qasync_event_loop_manager import QAsyncEventLoopManager
    event_loop_manager = QAsyncEventLoopManager(app, logger=logging.getLogger("QAsyncEventLoop"))

    # Initialize dispatcher, configuration, and services
    dispatcher = SignalDispatcher()
    config = ConfigManager(config_name="dreamscape_config.yaml")
    service = DreamscapeService(config=config)

    # Pass explicit services to DreamscapeUILogic for maximum modularity
    ui_logic = DreamscapeUILogic()

    # Remove config_manager from the services dict because it's passed separately.
    services = {
        'prompt_manager': service.prompt_manager,
        'chat_manager': service.chat_manager,
    }

    window = DreamscapeMainWindow(ui_logic, dispatcher, services=services)
    window.show()

    # (Optional) Schedule additional background tasks (e.g., Cursor tasks)
    event_loop_manager.start()


if __name__ == "__main__":
    main()
