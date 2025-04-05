#!/usr/bin/env python3
"""
Task Management Tab Factory

Creates a consolidated task management tab that combines functionality from:
- Task Status Tab
- Task History Modal
- Draggable Prompt Board
"""

import logging
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel,
    QPushButton, QHBoxLayout, QSplitter, QFrame
)
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)

class TaskManagementTabFactory:
    """Factory for creating the consolidated task management tab."""
    
    @staticmethod
    def create(services: Dict[str, Any], parent: Optional[QWidget] = None) -> QWidget:
        """
        Create a consolidated task management tab.
        
        Args:
            services: Dictionary of application services
            parent: Parent widget
            
        Returns:
            A widget containing the task management UI
        """
        try:
            # Create the main widget
            main_widget = QWidget(parent)
            main_layout = QVBoxLayout(main_widget)
            
            # Header with controls
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            header_layout.setContentsMargins(0, 0, 0, 10)
            
            title = QLabel("Task Management Dashboard")
            title.setStyleSheet("font-size: 16pt; font-weight: bold;")
            header_layout.addWidget(title)
            
            refresh_button = QPushButton("Refresh All")
            refresh_button.setMaximumWidth(100)
            header_layout.addWidget(refresh_button)
            
            main_layout.addWidget(header_widget)
            
            # Create a splitter for resizable sections
            splitter = QSplitter(Qt.Horizontal)
            
            # Left section: Task board with drag and drop
            try:
                from interfaces.pyqt.tabs.draggable_prompt_board_tab import DraggablePromptBoardTab
                # Using the tab class directly but not as a top-level tab
                board_widget = DraggablePromptBoardTab(services, is_subtab=True)
                board_container = QFrame()
                board_layout = QVBoxLayout(board_container)
                board_layout.addWidget(QLabel("Task Board"))
                board_layout.addWidget(board_widget)
                splitter.addWidget(board_container)
            except Exception as e:
                logger.error(f"Failed to load task board: {e}")
                error_widget = QWidget()
                error_layout = QVBoxLayout(error_widget)
                error_layout.addWidget(QLabel(f"Task Board unavailable: {str(e)}"))
                splitter.addWidget(error_widget)
            
            # Right section: Task status and history
            right_widget = QTabWidget()
            
            # Tab 1: Task Status
            try:
                from interfaces.pyqt.tabs.task_status_tab import TaskStatusTab
                status_tab = TaskStatusTab(services, is_subtab=True)
                right_widget.addTab(status_tab, "Task Status")
            except Exception as e:
                logger.error(f"Failed to load task status tab: {e}")
                error_widget = QWidget()
                error_layout = QVBoxLayout(error_widget)
                error_layout.addWidget(QLabel(f"Task Status unavailable: {str(e)}"))
                right_widget.addTab(error_widget, "Task Status (Error)")
            
            # Tab 2: Task History
            try:
                from interfaces.pyqt.tabs.task_history_modal import TaskHistoryWidget
                history_tab = TaskHistoryWidget(services)
                right_widget.addTab(history_tab, "Task History")
            except Exception as e:
                logger.error(f"Failed to load task history tab: {e}")
                error_widget = QWidget()
                error_layout = QVBoxLayout(error_widget)
                error_layout.addWidget(QLabel(f"Task History unavailable: {str(e)}"))
                right_widget.addTab(error_widget, "Task History (Error)")
            
            # Add Success Dashboard if available
            try:
                from interfaces.pyqt.tabs.success_dashboard_tab import SuccessDashboardTab
                success_tab = SuccessDashboardTab(services, is_subtab=True)
                right_widget.addTab(success_tab, "Success Metrics")
            except Exception as e:
                logger.error(f"Failed to load success dashboard: {e}")
                # Don't add an error tab for this since it's optional
            
            splitter.addWidget(right_widget)
            
            # Set initial sizes (40% left, 60% right)
            splitter.setSizes([400, 600])
            
            main_layout.addWidget(splitter)
            
            # Connect refresh button
            refresh_button.clicked.connect(lambda: TaskManagementTabFactory._refresh_all(board_widget, right_widget))
            
            return main_widget
        except Exception as e:
            logger.error(f"Failed to create task management tab: {e}")
            error_widget = QWidget(parent)
            error_layout = QVBoxLayout(error_widget)
            error_layout.addWidget(QLabel(f"Failed to create task management tab: {str(e)}"))
            
            retry_button = QPushButton("Retry")
            retry_button.clicked.connect(lambda: TaskManagementTabFactory._retry_load(error_widget, services, parent))
            error_layout.addWidget(retry_button)
            
            return error_widget
    
    @staticmethod
    def _refresh_all(board_widget, right_widget):
        """Refresh all components in the task management tab."""
        try:
            # Refresh task board
            if hasattr(board_widget, 'refresh_board'):
                board_widget.refresh_board()
            
            # Refresh active tab in right section
            current_tab = right_widget.currentWidget()
            if hasattr(current_tab, 'refresh_data'):
                current_tab.refresh_data()
            elif hasattr(current_tab, 'refresh'):
                current_tab.refresh()
            elif hasattr(current_tab, 'update_data'):
                current_tab.update_data()
        except Exception as e:
            logger.error(f"Error refreshing task management tab: {e}")
    
    @staticmethod
    def _retry_load(error_widget, services, parent):
        """Retry loading the task management tab."""
        try:
            new_widget = TaskManagementTabFactory.create(services, parent)
            if error_widget.parent():
                parent_layout = error_widget.parent().layout()
                if parent_layout:
                    # Find and replace the error widget
                    for i in range(parent_layout.count()):
                        if parent_layout.itemAt(i).widget() == error_widget:
                            parent_layout.replaceWidget(error_widget, new_widget)
                            error_widget.deleteLater()
                            break
        except Exception as e:
            logger.error(f"Failed to retry loading task management tab: {e}") 