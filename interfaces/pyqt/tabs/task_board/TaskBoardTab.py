"""
Task Board Tab Module

This module provides a UI for managing autonomous development tasks.
It allows uploading project context, managing a task queue, and
interfacing with the autonomous development system.
"""

from typing import Dict, Any, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QSplitter, QListWidget, QListWidgetItem, QPushButton, 
    QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
import logging

class TaskBoardTab(QWidget):
    """
    A tab widget for managing autonomous development tasks.
    
    This tab provides functionality to:
    - Upload and display project context
    - Manage a sortable list of development tasks
    - Queue tasks for autonomous execution
    """
    
    task_queued = pyqtSignal(dict)  # Emitted when a task is queued for execution
    
    def __init__(self, services: Dict[str, Any], parent: Optional[QWidget] = None):
        """
        Initialize the TaskBoardTab.
        
        Args:
            services: Dictionary of application services
            parent: Parent widget
        """
        super().__init__(parent)
        self.services = services
        self.logger = logging.getLogger(__name__)
        self.tasks = []
        self.context = ""
        
        # Get required services
        self.cursor_session = self.services.get('cursor_session_manager')
        self.project_scanner = self.services.get('project_scanner')
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the user interface components."""
        main_layout = QVBoxLayout(self)

        # Splitter: Left = Task List, Right = Project Context Display
        splitter = QSplitter(Qt.Horizontal)

        # Left Panel: Task List with sortable functionality
        task_list_group = QGroupBox("Task List")
        task_list_layout = QVBoxLayout()
        self.task_list_widget = QListWidget()
        self.task_list_widget.setDragDropMode(QListWidget.InternalMove)
        task_list_layout.addWidget(self.task_list_widget)
        task_list_group.setLayout(task_list_layout)
        splitter.addWidget(task_list_group)

        # Right Panel: Project Context
        context_group = QGroupBox("Project Context")
        context_layout = QVBoxLayout()
        self.context_label = QLabel("No context uploaded.")
        self.context_label.setWordWrap(True)
        context_layout.addWidget(self.context_label)
        context_group.setLayout(context_layout)
        splitter.addWidget(context_group)

        splitter.setSizes([300, 500])
        main_layout.addWidget(splitter)

        # Bottom Controls
        control_group = QGroupBox("Controls")
        control_layout = QHBoxLayout()

        self.upload_button = QPushButton("Upload Context")
        self.upload_button.clicked.connect(self.upload_context)
        control_layout.addWidget(self.upload_button)

        self.scan_button = QPushButton("Scan Project")
        self.scan_button.clicked.connect(self.scan_project)
        control_layout.addWidget(self.scan_button)

        self.add_task_button = QPushButton("Add Sample Task")
        self.add_task_button.clicked.connect(self.add_sample_task)
        control_layout.addWidget(self.add_task_button)

        self.queue_button = QPushButton("Queue Tasks")
        self.queue_button.clicked.connect(self.queue_tasks)
        control_layout.addWidget(self.queue_button)

        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)

        self.setLayout(main_layout)

    def upload_context(self):
        """Open a file dialog to upload a project context file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, 
            "Upload Project Context",
            "",
            "Text Files (*.txt);;Markdown Files (*.md);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    self.context = f.read()
                self.context_label.setText(
                    f"Context loaded from:\n{filename}\n\n{self.context[:200]}..."
                )
                self.logger.info(f"Successfully loaded context from {filename}")
            except Exception as e:
                self.logger.error(f"Error loading context: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load context file: {str(e)}"
                )

    def scan_project(self):
        """Scan the current project using ProjectScanner."""
        if not self.project_scanner:
            self.logger.warning("ProjectScanner service not available")
            QMessageBox.warning(
                self,
                "Service Unavailable",
                "Project scanning service is not available."
            )
            return

        try:
            # Scan project and update context
            scan_result = self.project_scanner.scan_project(max_files=100)
            self.context = str(scan_result)
            self.context_label.setText(
                f"Project scan completed.\n\nSummary:\n{self.context[:200]}..."
            )
            self.logger.info("Project scan completed successfully")
        except Exception as e:
            self.logger.error(f"Error scanning project: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to scan project: {str(e)}"
            )

    def add_sample_task(self):
        """Add a sample task to the task list."""
        task_id = f"task_{len(self.tasks)+1}"
        sample_task = {
            "id": task_id,
            "title": f"Sample Task {len(self.tasks)+1}",
            "prompt": "Implement feature X under conditions Y.",
            "priority": "High",
            "status": "To Do"
        }
        self.tasks.append(sample_task)
        item = QListWidgetItem(sample_task["title"])
        item.setData(Qt.UserRole, sample_task)
        self.task_list_widget.addItem(item)
        self.logger.debug(f"Added sample task: {task_id}")

    def queue_tasks(self):
        """Queue tasks for execution by the autonomous system."""
        if not self.tasks:
            self.logger.warning("No tasks to queue")
            QMessageBox.warning(
                self,
                "No Tasks",
                "There are no tasks to queue."
            )
            return

        if not self.cursor_session:
            self.logger.warning("CursorSessionManager service not available")
            QMessageBox.warning(
                self,
                "Service Unavailable",
                "Task execution service is not available."
            )
            return

        try:
            for task in self.tasks:
                # Emit signal for each task
                self.task_queued.emit({
                    **task,
                    "context": self.context
                })
                self.logger.info(f"Queued task: {task['id']}")

            QMessageBox.information(
                self,
                "Success",
                f"Successfully queued {len(self.tasks)} tasks for execution."
            )
        except Exception as e:
            self.logger.error(f"Error queueing tasks: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to queue tasks: {str(e)}"
            ) 