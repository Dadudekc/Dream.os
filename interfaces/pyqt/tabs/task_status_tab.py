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
    """Tab for displaying task statuses and management."""
    
    def __init__(self, services, parent=None, is_subtab=False):
        """
        Initialize the task status tab.
        
        Args:
            services: Dictionary of application services
            parent: Parent widget
            is_subtab: Whether this tab is being used as a subtab in another component
        """
        super().__init__(parent)
        self.services = services
        self.is_subtab = is_subtab
        self.task_manager = services.get('task_manager')
        
        # Initialize UI elements
        if not self.is_subtab:
            self._init_ui()
        else:
            self._init_subtab_ui()
            
    def _init_ui(self):
        """Initialize the full UI for standalone tab mode."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Header with title and controls
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Task Status Dashboard")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        # Add the refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_button)
        
        # Add filter controls
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Tasks", "Pending", "In Progress", "Completed", "Failed"])
        self.filter_combo.currentIndexChanged.connect(self.filter_tasks)
        header_layout.addWidget(self.filter_combo)
        
        main_layout.addLayout(header_layout)
        
        # Create and add the task status UI
        self.status_widget = self._create_status_ui()
        main_layout.addWidget(self.status_widget)
        
        # Initialize the task data
        self.refresh_data()
        
    def _init_subtab_ui(self):
        """Initialize minimal UI for use as a subtab."""
        # Simplified layout without header
        main_layout = QVBoxLayout(self)
        
        # Create a toolbar with essential controls
        toolbar_layout = QHBoxLayout()
        
        # Add the refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        toolbar_layout.addWidget(self.refresh_button)
        
        # Add filter controls
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Tasks", "Pending", "In Progress", "Completed", "Failed"])
        self.filter_combo.currentIndexChanged.connect(self.filter_tasks)
        toolbar_layout.addWidget(self.filter_combo)
        
        main_layout.addLayout(toolbar_layout)
        
        # Create and add the task status UI
        self.status_widget = self._create_status_ui()
        main_layout.addWidget(self.status_widget)
        
        # Initialize the task data
        self.refresh_data()
        
    def _create_status_ui(self):
        """Create the task status UI components common to both full tab and subtab modes."""
        # Implementation continues as before...


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