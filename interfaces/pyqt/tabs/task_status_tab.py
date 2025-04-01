#!/usr/bin/env python3
"""
Task Status Tab

This module provides a PyQt5 UI tab for displaying task status, screenshots, and
validation results from the CursorUIService. It integrates with the prompt
orchestration system to provide real-time feedback on task execution.
"""

import os
import sys
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QTabWidget, QSplitter,
    QHeaderView, QTextEdit, QComboBox, QFileDialog, QMessageBox,
    QScrollArea, QGridLayout, QFrame
)
from PyQt5.QtGui import QPixmap, QIcon, QColor, QFont
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer

# Add parent directory to path to allow importing from modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core.services.cursor_ui_service import ExecutionStatus
from interfaces.pyqt.orchestrator_bridge import OrchestratorBridge


class TaskStatusWidget(QWidget):
    """
    Widget for displaying a single task's status and details.
    """
    
    # Signal emitted when a requeue is requested
    requeue_requested = pyqtSignal(str)
    
    def __init__(self, task_data: Dict[str, Any], parent=None):
        """
        Initialize the TaskStatusWidget.
        
        Args:
            task_data: Dictionary containing task data
            parent: Parent widget
        """
        super().__init__(parent)
        self.task_data = task_data
        self.setup_ui()
        self.update_task_data(task_data)
    
    def setup_ui(self):
        """Set up the widget UI."""
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create header
        header_layout = QHBoxLayout()
        
        # Task ID and status
        self.id_label = QLabel()
        self.id_label.setFont(QFont("Arial", 10, QFont.Bold))
        header_layout.addWidget(self.id_label)
        
        self.status_label = QLabel()
        self.status_label.setFont(QFont("Arial", 10))
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        # Timestamp
        self.timestamp_label = QLabel()
        self.timestamp_label.setFont(QFont("Arial", 8))
        header_layout.addWidget(self.timestamp_label)
        
        layout.addLayout(header_layout)
        
        # Create separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Create content area with tabs
        self.tabs = QTabWidget()
        
        # Details tab
        self.details_widget = QWidget()
        details_layout = QGridLayout(self.details_widget)
        
        # Template
        details_layout.addWidget(QLabel("Template:"), 0, 0)
        self.template_label = QLabel()
        details_layout.addWidget(self.template_label, 0, 1)
        
        # Target output
        details_layout.addWidget(QLabel("Target Output:"), 1, 0)
        self.target_output_label = QLabel()
        details_layout.addWidget(self.target_output_label, 1, 1)
        
        # Duration
        details_layout.addWidget(QLabel("Duration:"), 2, 0)
        self.duration_label = QLabel()
        details_layout.addWidget(self.duration_label, 2, 1)
        
        # Attempts
        details_layout.addWidget(QLabel("Attempts:"), 3, 0)
        self.attempts_label = QLabel()
        details_layout.addWidget(self.attempts_label, 3, 1)
        
        self.tabs.addTab(self.details_widget, "Details")
        
        # Screenshot tab
        self.screenshot_widget = QWidget()
        screenshot_layout = QVBoxLayout(self.screenshot_widget)
        
        self.screenshot_label = QLabel("No screenshot available")
        self.screenshot_label.setAlignment(Qt.AlignCenter)
        
        screenshot_scroll = QScrollArea()
        screenshot_scroll.setWidget(self.screenshot_label)
        screenshot_scroll.setWidgetResizable(True)
        
        screenshot_layout.addWidget(screenshot_scroll)
        
        self.tabs.addTab(self.screenshot_widget, "Screenshot")
        
        # Validation tab
        self.validation_widget = QWidget()
        validation_layout = QVBoxLayout(self.validation_widget)
        
        self.validation_table = QTableWidget(0, 3)  # Columns: Type, Expected, Result
        self.validation_table.setHorizontalHeaderLabels(["Check Type", "Expected", "Result"])
        self.validation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        validation_layout.addWidget(self.validation_table)
        
        self.validation_summary = QLabel()
        validation_layout.addWidget(self.validation_summary)
        
        self.tabs.addTab(self.validation_widget, "Validation")
        
        # Output tab
        self.output_widget = QWidget()
        output_layout = QVBoxLayout(self.output_widget)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        
        self.tabs.addTab(self.output_widget, "Output")
        
        layout.addWidget(self.tabs)
        
        # Create buttons
        button_layout = QHBoxLayout()
        
        self.view_button = QPushButton("View Output File")
        self.view_button.clicked.connect(self.view_output_file)
        button_layout.addWidget(self.view_button)
        
        self.requeue_button = QPushButton("Requeue Task")
        self.requeue_button.clicked.connect(self.requeue_task)
        button_layout.addWidget(self.requeue_button)
        
        layout.addLayout(button_layout)
    
    def update_task_data(self, task_data: Dict[str, Any]):
        """
        Update the widget with task data.
        
        Args:
            task_data: Dictionary containing task data
        """
        self.task_data = task_data
        
        # Update header
        task_id = task_data.get("id", "Unknown ID")
        self.id_label.setText(f"Task: {task_id}")
        
        status = task_data.get("status", "unknown")
        self.status_label.setText(f"Status: {status}")
        
        # Set status color
        if status == ExecutionStatus.COMPLETED.value:
            color = QColor(0, 128, 0)  # Green
        elif status == ExecutionStatus.RUNNING.value:
            color = QColor(0, 0, 255)  # Blue
        elif status == ExecutionStatus.ERROR.value or status == ExecutionStatus.FAILED.value:
            color = QColor(255, 0, 0)  # Red
        else:
            color = QColor(128, 128, 128)  # Gray
            
        self.status_label.setStyleSheet(f"color: {color.name()}")
        
        # Update timestamp
        timestamp = task_data.get("end_time") or task_data.get("start_time")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                self.timestamp_label.setText(formatted_time)
            except ValueError:
                self.timestamp_label.setText(timestamp)
        else:
            self.timestamp_label.setText("")
        
        # Update details tab
        self.template_label.setText(task_data.get("template_name", ""))
        self.target_output_label.setText(task_data.get("target_output", ""))
        
        duration = task_data.get("duration_seconds")
        if duration is not None:
            self.duration_label.setText(f"{duration:.2f} seconds")
        else:
            self.duration_label.setText("N/A")
            
        self.attempts_label.setText(str(task_data.get("attempts", 1)))
        
        # Update screenshot tab
        screenshot_path = task_data.get("screenshot")
        if screenshot_path and os.path.exists(screenshot_path):
            pixmap = QPixmap(screenshot_path)
            if not pixmap.isNull():
                self.screenshot_label.setPixmap(pixmap)
                self.screenshot_label.setMinimumSize(1, 1)
                self.screenshot_label.setScaledContents(True)
            else:
                self.screenshot_label.setText("Could not load screenshot")
        else:
            self.screenshot_label.setText("No screenshot available")
            self.screenshot_label.setPixmap(QPixmap())  # Clear pixmap
        
        # Update validation tab
        validation = task_data.get("validation", {})
        checks = validation.get("checks", [])
        
        self.validation_table.setRowCount(len(checks))
        
        for i, check in enumerate(checks):
            check_type = check.get("type", "")
            
            # Create items
            type_item = QTableWidgetItem(check_type.replace("_", " ").title())
            
            # Get expected value based on check type
            expected = ""
            if "expected" in check:
                expected = str(check["expected"])
            elif "excluded" in check:
                expected = f"Not contain: {check['excluded']}"
                
            expected_item = QTableWidgetItem(expected)
            
            # Result with color
            passed = check.get("passed", False)
            result_item = QTableWidgetItem("✓ Passed" if passed else "✗ Failed")
            result_item.setForeground(QColor(0, 128, 0) if passed else QColor(255, 0, 0))
            
            # Set items in table
            self.validation_table.setItem(i, 0, type_item)
            self.validation_table.setItem(i, 1, expected_item)
            self.validation_table.setItem(i, 2, result_item)
        
        # Update validation summary
        passed = validation.get("passed", False)
        requeue = validation.get("requeue", False)
        
        if passed:
            self.validation_summary.setText("✓ All validation checks passed")
            self.validation_summary.setStyleSheet("color: green")
        else:
            message = "✗ Validation failed"
            if requeue:
                message += " (task will be requeued)"
            self.validation_summary.setText(message)
            self.validation_summary.setStyleSheet("color: red")
        
        # Update output tab
        output = task_data.get("output", "")
        self.output_text.setPlainText(output)
        
        # Update button states
        target_output = task_data.get("target_output", "")
        self.view_button.setEnabled(bool(target_output) and os.path.exists(target_output))
        self.requeue_button.setEnabled(status != ExecutionStatus.RUNNING.value)
    
    def view_output_file(self):
        """Open the output file."""
        target_output = self.task_data.get("target_output", "")
        if target_output and os.path.exists(target_output):
            # Use system default application to open the file
            # This approach varies by platform, so might need refinement
            import subprocess
            try:
                if sys.platform == 'win32':
                    os.startfile(target_output)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.call(['open', target_output])
                else:  # Linux
                    subprocess.call(['xdg-open', target_output])
            except Exception as e:
                QMessageBox.warning(self, "Error Opening File", f"Could not open file: {str(e)}")
        else:
            QMessageBox.warning(self, "File Not Found", "Output file does not exist.")
    
    def requeue_task(self):
        """Emit signal to requeue this task."""
        task_id = self.task_data.get("id")
        if task_id:
            self.requeue_requested.emit(task_id)


class TaskStatusTab(QWidget):
    """
    Tab for displaying task status, screenshots, and validation results.
    """
    
    refresh_signal = pyqtSignal()
    
    def __init__(self, parent=None, orchestrator_bridge=None):
        """
        Initialize the TaskStatusTab.
        
        Args:
            parent: Parent widget
            orchestrator_bridge: Optional OrchestratorBridge instance
        """
        super().__init__(parent)
        self.tasks = {}
        self.task_widgets = {}
        self.orchestrator_bridge = orchestrator_bridge
        self.setup_ui()
        
        # Connect to bridge signals if provided
        if self.orchestrator_bridge:
            self.connect_to_bridge()
        
        # Set up auto-refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_tasks)
        
        # Start with a refresh to load initial tasks
        self.refresh_tasks()
    
    def setup_ui(self):
        """Set up the tab UI."""
        # Create layout
        main_layout = QVBoxLayout(self)
        
        # Create header
        header_layout = QHBoxLayout()
        
        header_label = QLabel("Task Status and Results")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        # Create filter dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Tasks",
            "Completed Tasks",
            "Running Tasks",
            "Failed Tasks"
        ])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        header_layout.addWidget(QLabel("Filter:"))
        header_layout.addWidget(self.filter_combo)
        
        # Create refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_tasks)
        header_layout.addWidget(self.refresh_button)
        
        # Create auto-refresh checkbox
        self.auto_refresh_combo = QComboBox()
        self.auto_refresh_combo.addItems([
            "Auto-refresh: Off",
            "Auto-refresh: 5s",
            "Auto-refresh: 15s",
            "Auto-refresh: 30s"
        ])
        self.auto_refresh_combo.currentTextChanged.connect(self.set_auto_refresh)
        header_layout.addWidget(self.auto_refresh_combo)
        
        main_layout.addLayout(header_layout)
        
        # Create scroll area for task widgets
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)
        
        # Create bottom controls
        bottom_layout = QHBoxLayout()
        
        # Memory file selection
        bottom_layout.addWidget(QLabel("Task Memory File:"))
        
        self.memory_path_edit = QTextEdit("memory/task_history.json")
        self.memory_path_edit.setMaximumHeight(28)
        bottom_layout.addWidget(self.memory_path_edit)
        
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_memory_file)
        bottom_layout.addWidget(self.browse_button)
        
        # Load button
        self.load_button = QPushButton("Load Tasks")
        self.load_button.clicked.connect(self.load_tasks_from_file)
        bottom_layout.addWidget(self.load_button)
        
        main_layout.addLayout(bottom_layout)
        
        # Status bar
        self.status_bar = QLabel()
        self.status_bar.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.status_bar)
    
    def connect_to_bridge(self):
        """Connect to the orchestrator bridge signals."""
        if not self.orchestrator_bridge:
            return
            
        # Connect to relevant signals
        self.orchestrator_bridge.task_execution_completed.connect(self.on_task_execution_completed)
        self.orchestrator_bridge.task_requeued.connect(self.on_task_requeued)
        self.orchestrator_bridge.tasks_requeued.connect(self.on_tasks_requeued)
    
    def on_task_execution_completed(self, data: Dict[str, Any]):
        """
        Handle task execution completed event.
        
        Args:
            data: Event data
        """
        # Get task data and update
        task_id = data.get("task_id")
        result = data.get("result", {})
        
        if task_id and task_id in self.tasks:
            # Update task data
            task = self.tasks[task_id]
            task.update(result)
            
            # Update widget if exists
            if task_id in self.task_widgets:
                self.task_widgets[task_id].update_task_data(task)
            
            # Show status message
            status = result.get("status", "completed")
            self.status_bar.setText(f"Task {task_id} {status} at {datetime.now().strftime('%H:%M:%S')}")
        else:
            # If task not loaded yet, refresh tasks
            self.refresh_tasks()
    
    def on_task_requeued(self, data: Dict[str, Any]):
        """
        Handle task requeued event.
        
        Args:
            data: Event data
        """
        task_id = data.get("task_id")
        success = data.get("success", False)
        
        if success:
            self.status_bar.setText(f"Task {task_id} requeued successfully at {datetime.now().strftime('%H:%M:%S')}")
            # Refresh tasks to update status
            self.refresh_tasks()
        else:
            error = data.get("error", "Unknown error")
            self.status_bar.setText(f"Failed to requeue task {task_id}: {error}")
            QMessageBox.warning(self, "Requeue Failed", f"Failed to requeue task {task_id}: {error}")
    
    def on_tasks_requeued(self, data: Dict[str, Any]):
        """
        Handle tasks requeued event.
        
        Args:
            data: Event data
        """
        count = data.get("count", 0)
        self.status_bar.setText(f"Requeued {count} tasks at {datetime.now().strftime('%H:%M:%S')}")
        # Refresh tasks to update status
        self.refresh_tasks()
    
    def refresh_tasks(self):
        """Refresh task display from execution service."""
        # If connected to orchestrator bridge, use it to refresh tasks
        if self.orchestrator_bridge:
            task_data = self.orchestrator_bridge.refresh_tasks()
            
            # Update tasks dictionary with both queued and executed tasks
            for task in task_data.get("queued", []) + task_data.get("executed", []):
                task_id = task.get("id")
                if task_id:
                    self.tasks[task_id] = task
            
            # Update UI
            self.update_task_widgets()
            self.status_bar.setText(f"Tasks refreshed at {datetime.now().strftime('%H:%M:%S')}")
        else:
            # Fall back to loading from file
            self.load_tasks_from_file()
    
    def apply_filter(self, filter_text: str):
        """
        Apply a filter to the displayed tasks.
        
        Args:
            filter_text: Filter text
        """
        for task_id, widget in self.task_widgets.items():
            status = self.tasks.get(task_id, {}).get("status", "unknown")
            
            if filter_text == "All Tasks":
                widget.setVisible(True)
            elif filter_text == "Completed Tasks" and status == ExecutionStatus.COMPLETED.value:
                widget.setVisible(True)
            elif filter_text == "Running Tasks" and status == ExecutionStatus.RUNNING.value:
                widget.setVisible(True)
            elif filter_text == "Failed Tasks" and (status == ExecutionStatus.FAILED.value or status == ExecutionStatus.ERROR.value):
                widget.setVisible(True)
            else:
                widget.setVisible(False)
    
    def set_auto_refresh(self, setting: str):
        """
        Set auto-refresh interval.
        
        Args:
            setting: Auto-refresh setting
        """
        self.refresh_timer.stop()
        
        if "5s" in setting:
            self.refresh_timer.start(5000)
        elif "15s" in setting:
            self.refresh_timer.start(15000)
        elif "30s" in setting:
            self.refresh_timer.start(30000)
    
    def browse_memory_file(self):
        """Browse for memory file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Task Memory File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            self.memory_path_edit.setPlainText(filename)
    
    def load_tasks_from_file(self):
        """Load tasks from the specified memory file."""
        memory_file = self.memory_path_edit.toPlainText().strip()
        if not memory_file or not os.path.exists(memory_file):
            QMessageBox.warning(self, "File Not Found", f"Task memory file not found: {memory_file}")
            return
        
        try:
            with open(memory_file, 'r') as f:
                memory_data = json.load(f)
            
            # Extract tasks from memory data
            memory_tasks = memory_data.get("tasks", [])
            
            # Update our task dictionary
            for task in memory_tasks:
                task_id = task.get("id")
                if task_id:
                    self.tasks[task_id] = task
            
            # Update UI with tasks
            self.update_task_widgets()
            
            self.status_bar.setText(f"Loaded {len(memory_tasks)} tasks from file at {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error Loading Tasks", f"Could not load tasks: {str(e)}")
    
    def update_task_widgets(self):
        """Update the task widgets based on the tasks dictionary."""
        # Clear existing widgets from layout
        for i in reversed(range(self.scroll_layout.count() - 1)):  # -1 to preserve stretch at end
            item = self.scroll_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        # Create widgets for all tasks
        self.task_widgets = {}
        for task_id, task_data in sorted(self.tasks.items(), key=lambda x: x[1].get("start_time", ""), reverse=True):
            widget = TaskStatusWidget(task_data)
            # Connect requeue signal to handler
            widget.requeue_requested.connect(self.handle_requeue_request)
            self.task_widgets[task_id] = widget
            self.scroll_layout.insertWidget(0, widget)
        
        # Apply current filter
        self.apply_filter(self.filter_combo.currentText())
    
    def handle_requeue_request(self, task_id: str):
        """
        Handle a requeue request from a task widget.
        
        Args:
            task_id: ID of the task to requeue
        """
        if self.orchestrator_bridge:
            # Use the bridge to requeue the task
            success = self.orchestrator_bridge.requeue_task(task_id)
            if not success:
                QMessageBox.warning(self, "Requeue Failed", f"Failed to requeue task {task_id}")
        else:
            QMessageBox.information(self, "Not Connected", 
                                  "Not connected to orchestrator. Requeue is not possible without a connection.")


class TaskStatusTabFactory:
    """Factory for creating TaskStatusTab instances."""
    
    @staticmethod
    def create(orchestrator_bridge=None, parent=None) -> TaskStatusTab:
        """
        Create a TaskStatusTab instance.
        
        Args:
            orchestrator_bridge: Optional OrchestratorBridge instance to connect to
            parent: Parent widget
            
        Returns:
            TaskStatusTab instance
        """
        tab = TaskStatusTab(parent, orchestrator_bridge)
        return tab


if __name__ == "__main__":
    # For testing as standalone
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = TaskStatusTabFactory.create()
    window.show()
    sys.exit(app.exec_()) 