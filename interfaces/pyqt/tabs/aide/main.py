#!/usr/bin/env python3
"""
AIDE.py (AI Development Environment)

A unified development environment that combines chat automation and debugging functionality.
This tab provides:
- File browsing and editing
- Prompt execution
- Debug session management
- Code generation and testing
- Self-healing capabilities
- Project scanning functionality
"""

import sys
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QSplitter, QTabWidget, QProgressBar, QPlainTextEdit, 
                             QGroupBox, QFormLayout, QLineEdit, QComboBox)
from PyQt5.QtCore import Qt, pyqtSlot
from typing import Dict, Any, Optional

# Import internal modules
from interfaces.pyqt.widgets.file_browser_widget import FileBrowserWidget
from interfaces.pyqt.GuiHelpers import GuiHelpers
from core.chatgpt_automation.automation_engine import AutomationEngine

# Import modular components
from interfaces.pyqt.tabs.aide.file_operations import FileOperationsHandler
from interfaces.pyqt.tabs.aide.prompt_operations import PromptOperationsHandler
from interfaces.pyqt.tabs.aide.debug_operations import DebugOperationsHandler
from interfaces.pyqt.tabs.aide.task_queue import TaskQueueHandler

# Define the folder for updated files
UPDATED_FOLDER = Path("updated")
UPDATED_FOLDER.mkdir(exist_ok=True)


class AIDE(QWidget):
    def __init__(self, dispatcher=None, logger=None, **services):
        """
        Initializes the AIDE (AI Development Environment).
        
        Args:
            dispatcher: Centralized signal dispatcher.
            logger: Logger instance.
            services: Additional services including debug_service, fix_service, rollback_service, 
                      cursor_manager, project_scanner.
        """
        super().__init__()
        self.dispatcher = dispatcher
        self.logger = logger
        self.services = services
        self.current_file_path = None
        
        # Initialize helpers and engine
        self.helpers = GuiHelpers()
        self.engine = AutomationEngine(use_local_llm=False, model_name='mistral')
        
        # Get debug-related services
        self.debug_service = services.get("debug_service")
        self.fix_service = services.get("fix_service")
        self.rollback_service = services.get("rollback_service")
        self.cursor_manager = services.get("cursor_manager")
        self.project_scanner = services.get("project_scanner")
        
        # Initialize handlers
        self.file_operations = FileOperationsHandler(
            parent=self,
            helpers=self.helpers,
            engine=self.engine,
            dispatcher=self.dispatcher,
            logger=self.logger,
            project_scanner=self.project_scanner
        )
        
        self.prompt_operations = PromptOperationsHandler(
            parent=self,
            helpers=self.helpers,
            engine=self.engine,
            dispatcher=self.dispatcher,
            logger=self.logger
        )
        
        self.debug_operations = DebugOperationsHandler(
            parent=self,
            helpers=self.helpers,
            dispatcher=self.dispatcher,
            logger=self.logger,
            debug_service=self.debug_service,
            fix_service=self.fix_service,
            rollback_service=self.rollback_service,
            cursor_manager=self.cursor_manager
        )
        
        self.task_queue = TaskQueueHandler(
            parent=self,
            helpers=self.helpers,
            dispatcher=self.dispatcher,
            logger=self.logger,
            cursor_manager=self.cursor_manager
        )
        
        self._init_ui()
        self._connect_signals()

        # Register callback with CursorSessionManager if available
        if self.cursor_manager and hasattr(self.cursor_manager, 'set_on_update_callback'):
            self.cursor_manager.set_on_update_callback(self.task_queue.handle_cursor_manager_update)
            # Optionally, trigger an initial update
            if hasattr(self.cursor_manager, '_get_queue_snapshot'):
                initial_snapshot = self.cursor_manager._get_queue_snapshot()
                self.task_queue.update_task_queue_display(initial_snapshot)

        if self.logger:
            self.logger.info("AIDE initialized")
        else:
            print("AIDE initialized")

    def _init_ui(self):
        """
        Set up the user interface.
        """
        self.setMinimumSize(800, 600)
        main_layout = QVBoxLayout(self)
        
        # Title label
        title_label = QLabel("AIDE - AI Development Environment")
        main_layout.addWidget(title_label)
        
        # Horizontal splitter for left/right panels
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # LEFT PANEL: File Browser 
        self.file_browser = FileBrowserWidget(helpers=self.helpers)
        main_splitter.addWidget(self.file_browser)
        main_splitter.setStretchFactor(0, 1)
        
        # RIGHT PANEL: QTabWidget with multiple tabs
        right_tab = QTabWidget()
        
        # --- Tab 1: Preview with Action Buttons ---
        preview_widget = self.file_operations.create_preview_widget()
        right_tab.addTab(preview_widget, "Preview")
        
        # --- Tab 2: Prompt Tab for OpenAIClient ---
        prompt_widget = self.prompt_operations.create_prompt_widget()
        right_tab.addTab(prompt_widget, "Prompt")
        
        # --- Tab 3: Task Queue / Full Sync Control ---
        task_queue_widget = self.task_queue.create_task_queue_widget()
        right_tab.addTab(task_queue_widget, "Task Queue")
        
        main_splitter.addWidget(right_tab)
        main_splitter.setStretchFactor(1, 3)
        
        # Connect file browser signal
        self.file_browser.fileDoubleClicked.connect(self.file_operations.load_file_into_preview)

    def _connect_signals(self):
        """
        Connect signals between components.
        """
        if self.dispatcher:
            if hasattr(self.dispatcher, "automation_result"):
                self.dispatcher.automation_result.connect(self.on_automation_result)
            if hasattr(self.dispatcher, "debug_output"):
                self.dispatcher.debug_output.connect(self.append_output)
            if hasattr(self.dispatcher, "cursor_code_generated"):
                self.dispatcher.cursor_code_generated.connect(self.on_cursor_code_generated)

    # Signal Handlers
    def on_automation_result(self, result):
        """Handle automation result from the dispatcher."""
        self.append_output(result)

    def on_cursor_code_generated(self, code):
        """Handle generated code from Cursor."""
        self.append_output("Cursor generated code:")
        self.append_output(code)

    def append_output(self, message: str):
        """Append a message to the output and log it."""
        if self.dispatcher and hasattr(self.dispatcher, "emit_append_output"):
            self.dispatcher.emit_append_output(message)
            
        # Delegate to prompt operations for display
        self.prompt_operations.append_output(message)
        
        if self.logger:
            self.logger.info(f"[AIDE] {message}") 