"""
Signal handlers for Dream.OS main window.
"""

import logging
from typing import Optional

from PyQt5.QtCore import pyqtSlot


class SignalHandlers:
    """Manages signal handling for the Dream.OS main window."""
    
    def __init__(self, window_ui, logger: logging.Logger):
        """
        Initialize signal handlers.
        
        Args:
            window_ui: Window UI instance
            logger: Logger instance for signal-related messages
        """
        self.ui = window_ui
        self.logger = logger
        
    def setup_signals(self, dispatcher, ui_logic) -> None:
        """
        Connect signals between components.
        
        Args:
            dispatcher: Signal dispatcher instance
            ui_logic: UI logic instance
        """
        try:
            dispatcher.append_output.connect(self.on_append_output)
            dispatcher.status_update.connect(self.on_status_update)
            dispatcher.discord_log.connect(self.on_discord_log)
            dispatcher.task_started.connect(self.on_task_started)
            dispatcher.task_progress.connect(self.on_task_progress)
            dispatcher.task_completed.connect(self.on_task_completed)
            dispatcher.task_failed.connect(self.on_task_failed)
            
            if ui_logic:
                ui_logic.set_output_signal(dispatcher.emit_append_output)
                ui_logic.set_status_update_signal(dispatcher.emit_status_update)
                ui_logic.set_discord_log_signal(dispatcher.emit_discord_log)
        except Exception as e:
            self.logger.error(f"Failed to set up signals: {str(e)}")
            
    @pyqtSlot(str)
    def on_append_output(self, message: str) -> None:
        """
        Handle append output signal.
        
        Args:
            message: Message to append
        """
        if self.ui.tabs:
            self.ui.tabs.append_output(message)
        else:
            self.ui.chat_display.append(message)
        self.ui.parent.statusBar().showMessage(message.split('\n')[0])
        
    @pyqtSlot(str)
    def on_status_update(self, message: str) -> None:
        """
        Handle status update signal.
        
        Args:
            message: Status message to display
        """
        if self.ui.tabs:
            self.ui.tabs.append_output(f"[Status] {message}")
        else:
            self.ui.parent.statusBar().showMessage(message)
        self.ui.parent.statusBar().showMessage(message)
        
    @pyqtSlot(str)
    def on_discord_log(self, message: str) -> None:
        """
        Handle Discord log signal.
        
        Args:
            message: Discord-related message to log
        """
        output_text = f"[Discord] {message}"
        if self.ui.tabs:
            self.ui.tabs.append_output(output_text)
        elif hasattr(self.ui, 'fallback_output'):
            self.ui.fallback_output.append(output_text)
        else:
            self.ui.chat_display.append(output_text)
        self.logger.info(output_text)
        
    @pyqtSlot(str)
    def on_task_started(self, task_id: str) -> None:
        """
        Handle task started signal.
        
        Args:
            task_id: ID of the started task
        """
        status_message = f"Task {task_id} started"
        self.ui.parent.statusBar().showMessage(status_message)
        output_text = f"[Task] {task_id} started"
        self._append_task_output(output_text)
        self.logger.info(output_text)
        
    @pyqtSlot(str, int, str)
    def on_task_progress(self, task_id: str, progress: int, message: str) -> None:
        """
        Handle task progress signal.
        
        Args:
            task_id: ID of the task
            progress: Progress percentage
            message: Progress message
        """
        status_message = f"Task {task_id}: {progress}% - {message}"
        self.ui.parent.statusBar().showMessage(status_message)
        output_text = f"[Task] {task_id}: {progress}% - {message}"
        self._append_task_output(output_text)
        self.logger.info(output_text)
        
    @pyqtSlot(str, dict)
    def on_task_completed(self, task_id: str, result: dict) -> None:
        """
        Handle task completed signal.
        
        Args:
            task_id: ID of the completed task
            result: Task result data
        """
        status_message = f"Task {task_id} completed"
        self.ui.parent.statusBar().showMessage(status_message)
        output_text = f"[Task] {task_id} completed successfully"
        self._append_task_output(output_text)
        self.logger.info(output_text)
        
    @pyqtSlot(str, str)
    def on_task_failed(self, task_id: str, error: str) -> None:
        """
        Handle task failed signal.
        
        Args:
            task_id: ID of the failed task
            error: Error message
        """
        error_msg = f"Task {task_id} failed: {error}"
        self.ui.parent.statusBar().showMessage(error_msg)
        output_text = f"[Error] {error_msg}"
        self._append_task_output(output_text)
        self.logger.error(output_text)
        
    def _append_task_output(self, message: str) -> None:
        """
        Append task-related output to the appropriate widget.
        
        Args:
            message: Message to append
        """
        if self.ui.tabs:
            self.ui.tabs.append_output(message)
        elif hasattr(self.ui, 'fallback_output'):
            self.ui.fallback_output.append(message)
        else:
            self.ui.chat_display.append(message) 