"""
Task Queue Handler for AIDE

This module contains the TaskQueueHandler class that manages task queue operations
including adding, processing, and displaying tasks.
"""

import json
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QGroupBox, QFormLayout, QLineEdit, QComboBox,
                            QPlainTextEdit, QListWidget, QListWidgetItem,
                            QMenu, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication
from typing import Dict, Any, List, Optional

# Import operations from the separate file
from interfaces.pyqt.tabs.aide.task_queue_operations import (
    handle_cursor_manager_update,
    get_status_prefix,
    update_task_queue_display,
    _update_task_item_status,
    on_task_double_clicked,
    _show_task_details,
    show_task_context_menu,
    _handle_context_menu,
    _add_task_to_queue,
    _requeue_task,
    _cancel_task,
    _boost_task_priority,
    _improve_test_coverage,
    _get_task_data,
    append_output
)

class TaskQueueHandler:
    def __init__(self, parent, helpers, dispatcher=None, logger=None, cursor_manager=None):
        """
        Initialize the TaskQueueHandler.
        
        Args:
            parent: Parent widget
            helpers: GuiHelpers instance
            dispatcher: Signal dispatcher
            logger: Logger instance
            cursor_manager: Cursor manager service
        """
        self.parent = parent
        self.helpers = helpers
        self.dispatcher = dispatcher
        self.logger = logger
        self.cursor_manager = cursor_manager
        
        # Storage for task data
        self.tasks = {}  # Dictionary to store task data by task_id
        
        # UI Components
        self.task_prompt_edit = None
        self.task_source_combo = None
        self.task_priority_combo = None
        self.task_filepath_edit = None
        self.task_mode_edit = None
        self.task_context_edit = None
        self.task_queue_list = None
        self.add_task_btn = None
        self.clear_task_form_btn = None
        self.accept_next_btn = None
        self.toggle_auto_accept_btn = None
        
        # Attach methods from task_queue_operations.py
        self.handle_cursor_manager_update = handle_cursor_manager_update.__get__(self)
        self.get_status_prefix = get_status_prefix.__get__(self)
        self.update_task_queue_display = update_task_queue_display.__get__(self)
        self._update_task_item_status = _update_task_item_status.__get__(self)
        self.on_task_double_clicked = on_task_double_clicked.__get__(self)
        self._show_task_details = _show_task_details.__get__(self)
        self.show_task_context_menu = show_task_context_menu.__get__(self)
        self._handle_context_menu = _handle_context_menu.__get__(self)
        self._add_task_to_queue = _add_task_to_queue.__get__(self)
        self._requeue_task = _requeue_task.__get__(self)
        self._cancel_task = _cancel_task.__get__(self)
        self._boost_task_priority = _boost_task_priority.__get__(self)
        self._improve_test_coverage = _improve_test_coverage.__get__(self)
        self._get_task_data = _get_task_data.__get__(self)
        self.append_output = append_output.__get__(self)
        
    def create_task_queue_widget(self):
        """Create and return the task queue widget."""
        task_queue_widget = QWidget()
        task_queue_layout = QVBoxLayout(task_queue_widget)

        # --- Task Input Area ---
        task_input_group = QGroupBox("Compose New Task")
        task_input_layout = QFormLayout(task_input_group)

        self.task_prompt_edit = QPlainTextEdit()
        self.task_prompt_edit.setPlaceholderText("Enter the core prompt/instruction for the task...")
        task_input_layout.addRow("Prompt:", self.task_prompt_edit)

        self.task_source_combo = QComboBox()
        self.task_source_combo.addItems(["Victor", "Thea", "Auto"]) # Example sources
        task_input_layout.addRow("Source:", self.task_source_combo)

        self.task_priority_combo = QComboBox()
        self.task_priority_combo.addItems(["low", "medium", "high", "critical"]) # Example priorities
        self.task_priority_combo.setCurrentText("medium")
        task_input_layout.addRow("Priority:", self.task_priority_combo)

        self.task_filepath_edit = QLineEdit()
        self.task_filepath_edit.setPlaceholderText("Optional: target file path...")
        task_input_layout.addRow("File Path:", self.task_filepath_edit)
        
        # Mode could also be a dropdown
        self.task_mode_edit = QLineEdit()
        self.task_mode_edit.setPlaceholderText("Optional: execution mode (e.g., full_sync, tdd)...")
        task_input_layout.addRow("Mode:", self.task_mode_edit)
        
        # Context might need a more complex input, maybe a JSON editor or button
        self.task_context_edit = QPlainTextEdit()
        self.task_context_edit.setPlaceholderText("Optional: context as JSON...")
        self.task_context_edit.setFixedHeight(60) # Smaller box for context
        task_input_layout.addRow("Context (JSON):", self.task_context_edit)

        task_queue_layout.addWidget(task_input_group)

        # Buttons for task management
        task_button_layout = QHBoxLayout()
        self.add_task_btn = QPushButton("Add Task to Queue")
        self.add_task_btn.clicked.connect(self.on_add_task)
        task_button_layout.addWidget(self.add_task_btn)
        
        self.clear_task_form_btn = QPushButton("Clear Form")
        self.clear_task_form_btn.clicked.connect(self.clear_task_form)
        task_button_layout.addWidget(self.clear_task_form_btn)
        task_queue_layout.addLayout(task_button_layout)

        # --- Task Queue Display Area ---
        task_display_group = QGroupBox("Task Queue (via CursorSessionManager)")
        task_display_layout = QVBoxLayout(task_display_group)
        self.task_queue_list = QListWidget()
        # Enable context menu
        self.task_queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_queue_list.customContextMenuRequested.connect(self.show_task_context_menu)
        # Connect double-click for preview
        self.task_queue_list.itemDoubleClicked.connect(self.on_task_double_clicked)
        task_display_layout.addWidget(self.task_queue_list)
        task_queue_layout.addWidget(task_display_group)

        # Queue Control Buttons
        queue_control_layout = QHBoxLayout()
        self.accept_next_btn = QPushButton("Accept Next Task")
        self.accept_next_btn.clicked.connect(self.on_accept_next_task)
        queue_control_layout.addWidget(self.accept_next_btn)

        self.toggle_auto_accept_btn = QPushButton("Enable Auto-Accept")
        self.toggle_auto_accept_btn.setCheckable(True)
        self.toggle_auto_accept_btn.toggled.connect(self.on_toggle_auto_accept)
        queue_control_layout.addWidget(self.toggle_auto_accept_btn)
        task_queue_layout.addLayout(queue_control_layout)
        
        return task_queue_widget
        
    @pyqtSlot()
    def on_add_task(self):
        """Construct task dictionary from UI fields and queue it."""
        prompt_text = self.task_prompt_edit.toPlainText().strip()
        if not prompt_text:
            self.append_output("⚠️ Please enter a task prompt.")
            return
        
        # Attempt to parse context JSON
        context_text = self.task_context_edit.toPlainText().strip()
        task_context = {}
        if context_text:
            try:
                task_context = json.loads(context_text)
                if not isinstance(task_context, dict):
                    raise ValueError("Context must be a JSON object (dictionary).")
            except Exception as e:
                self.append_output(f"⚠️ Invalid Context JSON: {e}. Context will be ignored.")
                task_context = {} # Reset context on error

        # Build the task dictionary
        task_data = {
            "prompt": prompt_text,
            "source": self.task_source_combo.currentText(),
            "priority": self.task_priority_combo.currentText(),
            "file_path": self.task_filepath_edit.text().strip() or None,
            "mode": self.task_mode_edit.text().strip() or None,
            "context": task_context
        }

        if self.cursor_manager and hasattr(self.cursor_manager, 'queue_task'):
            try:
                self.cursor_manager.queue_task(task_data)
                self.append_output(f"✅ Task queued: {prompt_text[:50]}...")
                self.clear_task_form() # Clear form after successful queuing
            except Exception as e:
                error_msg = f"❌ Error queueing task: {e}"
                self.append_output(error_msg)
                if self.logger:
                    self.logger.error(error_msg, exc_info=True)
        else:
            self.append_output("❌ Cursor manager not available or doesn't support queue_task.")

    @pyqtSlot()
    def clear_task_form(self):
        """Clear all input fields in the task composition form."""
        self.task_prompt_edit.clear()
        self.task_source_combo.setCurrentIndex(0) # Reset to first item
        self.task_priority_combo.setCurrentText("medium") # Reset priority
        self.task_filepath_edit.clear()
        self.task_mode_edit.clear()
        self.task_context_edit.clear()

    @pyqtSlot()
    def on_accept_next_task(self):
        """Tell the CursorSessionManager to accept and run the next task in its queue."""
        if self.cursor_manager and hasattr(self.cursor_manager, 'accept_next_task'):
            try:
                self.append_output("Attempting to accept next task...")
                self.cursor_manager.accept_next_task() 
            except Exception as e:
                error_msg = f"❌ Error accepting next task: {e}"
                self.append_output(error_msg)
                if self.logger:
                    self.logger.error(error_msg, exc_info=True)
        else:
            self.append_output("❌ Cursor manager not available or doesn't support accept_next_task.")

    @pyqtSlot(bool)
    def on_toggle_auto_accept(self, checked):
        """Toggle the auto-accept mode in the CursorSessionManager."""
        if self.cursor_manager and hasattr(self.cursor_manager, 'toggle_auto_accept'):
            try:
                self.cursor_manager.toggle_auto_accept(checked)
                status = "enabled" if checked else "disabled"
                button_text = "Disable Auto-Accept" if checked else "Enable Auto-Accept"
                self.toggle_auto_accept_btn.setText(button_text)
                self.append_output(f"✅ Auto-accept mode {status}.")
            except Exception as e:
                error_msg = f"❌ Error toggling auto-accept: {e}"
                self.append_output(error_msg)
                if self.logger:
                    self.logger.error(error_msg, exc_info=True)
                self.toggle_auto_accept_btn.setChecked(not checked) # Revert button state on error
        else:
            self.append_output("❌ Cursor manager not available or doesn't support toggle_auto_accept.")
            self.toggle_auto_accept_btn.setChecked(not checked) # Revert button state 