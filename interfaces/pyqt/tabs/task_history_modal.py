#!/usr/bin/env python3
"""
task_history_modal.py

This module provides a modal dialog for viewing task details in the task history view.
"""

import json
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QDialogButtonBox, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt


class TaskDetailsModal(QDialog):
    """
    Modal dialog for viewing task details from the task history.
    """
    
    def __init__(self, task_data: Dict[str, Any], parent=None):
        """
        Initialize the task details modal.
        
        Args:
            task_data: Dictionary containing task information
            parent: Parent widget
        """
        super().__init__(parent)
        self.task_data = task_data
        self.setWindowTitle(f"Task Details: {task_data.get('id', 'Unknown')[:8]}...")
        self.resize(800, 600)
        self.setModal(True)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface for the modal."""
        layout = QVBoxLayout(self)
        
        # Header with key information
        header_layout = QVBoxLayout()
        
        # Task ID and status
        task_info = QHBoxLayout()
        task_info.addWidget(QLabel(f"<b>Task ID:</b> {self.task_data.get('id', 'Unknown')}"))
        status = self.task_data.get('status', 'unknown')
        status_color = {
            'queued': 'blue',
            'running': 'orange',
            'completed': 'green',
            'failed': 'red'
        }.get(status.lower(), 'gray')
        task_info.addWidget(QLabel(f"<b>Status:</b> <span style='color:{status_color};'>{status}</span>"))
        task_info.addStretch()
        header_layout.addLayout(task_info)
        
        # Template and target
        template_target = QHBoxLayout()
        template_target.addWidget(QLabel(f"<b>Template:</b> {self.task_data.get('template_name', 'Unknown')}"))
        template_target.addWidget(QLabel(f"<b>Target Output:</b> {self.task_data.get('target_output', 'Unknown')}"))
        template_target.addStretch()
        header_layout.addLayout(template_target)
        
        # Timestamp
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel(f"<b>Created:</b> {self.task_data.get('timestamp', 'Unknown')}"))
        time_layout.addStretch()
        header_layout.addLayout(time_layout)
        
        layout.addLayout(header_layout)
        
        # Create tabs for different views of the task
        tabs = QTabWidget()
        
        # Tab for the rendered prompt
        prompt_tab = QWidget()
        prompt_layout = QVBoxLayout(prompt_tab)
        prompt_edit = QTextEdit()
        prompt_edit.setReadOnly(True)
        prompt_edit.setPlainText(self.task_data.get('rendered_prompt', 'No prompt available'))
        prompt_layout.addWidget(prompt_edit)
        tabs.addTab(prompt_tab, "Rendered Prompt")
        
        # Tab for the context data
        context_tab = QWidget()
        context_layout = QVBoxLayout(context_tab)
        context_edit = QTextEdit()
        context_edit.setReadOnly(True)
        context_json = json.dumps(self.task_data.get('context', {}), indent=2)
        context_edit.setPlainText(context_json)
        context_layout.addWidget(context_edit)
        tabs.addTab(context_tab, "Context Data")
        
        # Tab for the raw task data
        raw_tab = QWidget()
        raw_layout = QVBoxLayout(raw_tab)
        raw_edit = QTextEdit()
        raw_edit.setReadOnly(True)
        # Filter out potentially large fields
        display_data = self.task_data.copy()
        if 'rendered_prompt' in display_data and len(display_data['rendered_prompt']) > 1000:
            display_data['rendered_prompt'] = display_data['rendered_prompt'][:1000] + "... (truncated)"
        raw_edit.setPlainText(json.dumps(display_data, indent=2))
        raw_layout.addWidget(raw_edit)
        tabs.addTab(raw_tab, "Raw Task Data")
        
        layout.addWidget(tabs)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box) 