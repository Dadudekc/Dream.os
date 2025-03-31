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

# Import the modular implementation
from interfaces.pyqt.tabs.aide import AIDE

import sys
import random
import json
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
                             QLabel, QSplitter, QTabWidget, QProgressBar, QPlainTextEdit, 
                             QFileDialog, QListWidget, QListWidgetItem, QInputDialog, QComboBox, QGroupBox, QFormLayout, QLineEdit, QMessageBox, QMenu)
from PyQt5.QtCore import Qt, pyqtSlot, QPoint
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

from interfaces.pyqt.widgets.file_browser_widget import FileBrowserWidget
from interfaces.pyqt.GuiHelpers import GuiHelpers
from core.chatgpt_automation.automation_engine import AutomationEngine

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
        self.tasks = {}  # Dictionary to store task data by task_id
        
        # Initialize helpers and engine
        self.helpers = GuiHelpers()
        self.engine = AutomationEngine(use_local_llm=False, model_name='mistral')
        
        # Get debug-related services
        self.debug_service = services.get("debug_service")
        self.fix_service = services.get("fix_service")
        self.rollback_service = services.get("rollback_service")
        self.cursor_manager = services.get("cursor_manager")
        self.project_scanner = services.get("project_scanner")
        
        self._init_ui()
        self._connect_signals()

        # Register callback with CursorSessionManager if available
        if self.cursor_manager and hasattr(self.cursor_manager, 'set_on_update_callback'):
            self.cursor_manager.set_on_update_callback(self._handle_cursor_manager_update)
            # Optionally, trigger an initial update
            if hasattr(self.cursor_manager, '_get_queue_snapshot'):
                initial_snapshot = self.cursor_manager._get_queue_snapshot()
                self._update_task_queue_display(initial_snapshot)

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
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        self.file_preview = QPlainTextEdit()
        self.file_preview.setPlaceholderText(
            "File preview will appear here.\nDouble-click a file in the browser to load it for editing."
        )
        preview_layout.addWidget(self.file_preview)
        
        # Action buttons layout
        button_layout = QHBoxLayout()
        
        # Add Scan Project button
        self.scan_project_btn = QPushButton("Scan Project")
        self.scan_project_btn.clicked.connect(self.on_scan_project)
        button_layout.addWidget(self.scan_project_btn)
        
        # File processing buttons
        self.process_button = QPushButton("Process File")
        self.process_button.clicked.connect(self.process_file)
        button_layout.addWidget(self.process_button)
        
        self.self_heal_button = QPushButton("Self-Heal")
        self.self_heal_button.clicked.connect(self.self_heal)
        button_layout.addWidget(self.self_heal_button)
        
        self.run_tests_button = QPushButton("Run Tests")
        self.run_tests_button.clicked.connect(self.run_tests)
        button_layout.addWidget(self.run_tests_button)
        
        # Debug buttons
        self.run_debug_btn = QPushButton("Run Debug")
        self.run_debug_btn.clicked.connect(self.on_run_debug)
        button_layout.addWidget(self.run_debug_btn)
        
        self.apply_fix_btn = QPushButton("Apply Fix")
        self.apply_fix_btn.clicked.connect(self.on_apply_fix)
        button_layout.addWidget(self.apply_fix_btn)
        
        self.rollback_btn = QPushButton("Rollback Fix")
        self.rollback_btn.clicked.connect(self.on_rollback_fix)
        button_layout.addWidget(self.rollback_btn)
        
        self.cursor_exec_btn = QPushButton("Execute via Cursor")
        self.cursor_exec_btn.clicked.connect(self.on_cursor_execute)
        button_layout.addWidget(self.cursor_exec_btn)
        
        preview_layout.addLayout(button_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        preview_layout.addWidget(self.progress_bar)
        
        right_tab.addTab(preview_widget, "Preview")
        
        # --- Tab 2: Prompt Tab for OpenAIClient ---
        prompt_widget = QWidget()
        prompt_layout = QVBoxLayout(prompt_widget)
        
        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setPlaceholderText("Enter your prompt here...")
        prompt_layout.addWidget(self.prompt_input)
        
        send_button = QPushButton("Send Prompt to ChatGPT")
        send_button.clicked.connect(self.send_prompt)
        prompt_layout.addWidget(send_button)
        
        batch_button = QPushButton("Process Batch with Prompt")
        batch_button.clicked.connect(self.process_batch_files)
        prompt_layout.addWidget(batch_button)
        
        self.prompt_response = QPlainTextEdit()
        self.prompt_response.setReadOnly(True)
        self.prompt_response.setPlaceholderText("Response will appear here...")
        prompt_layout.addWidget(self.prompt_response)
        
        right_tab.addTab(prompt_widget, "Prompt")
        
        # --- Tab 3: Task Queue / Full Sync Control ---
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
        task_button_layout.addWidget(self.add_task_btn)
        
        self.clear_task_form_btn = QPushButton("Clear Form") # Renamed
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
        queue_control_layout.addWidget(self.accept_next_btn)

        self.toggle_auto_accept_btn = QPushButton("Enable Auto-Accept")
        self.toggle_auto_accept_btn.setCheckable(True)
        queue_control_layout.addWidget(self.toggle_auto_accept_btn)
        task_queue_layout.addLayout(queue_control_layout)

        right_tab.addTab(task_queue_widget, "Task Queue")
        # --- End Tab 3 ---

        main_splitter.addWidget(right_tab)
        main_splitter.setStretchFactor(1, 3)
        
        self.file_browser.fileDoubleClicked.connect(self.load_file_into_preview)

        # Connect Task Queue buttons
        self.add_task_btn.clicked.connect(self.on_add_task)
        self.clear_task_form_btn.clicked.connect(self.clear_task_form) # New slot
        self.accept_next_btn.clicked.connect(self.on_accept_next_task)
        self.toggle_auto_accept_btn.toggled.connect(self.on_toggle_auto_accept)

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

    # --- File Operations ---
    
    def load_file_into_preview(self, file_path):
        """Load a file into the preview pane."""
        content = self.helpers.read_file(file_path)
        if content:
            self.file_preview.setPlainText(content)
            self.current_file_path = file_path
            self.append_output(f"Loaded: {file_path}")
        else:
            self.helpers.show_error("Could not load file.", "Error")

    def process_file(self):
        """Process the current file using the automation engine."""
        if not self.current_file_path:
            self.helpers.show_warning("No file loaded.", "Warning")
            return
        
        prompt_text = "Update this file and show me the complete updated version."
        file_content = self.file_preview.toPlainText()
        combined_prompt = f"{prompt_text}\n\n---\n\n{file_content}"
        self.append_output("Processing file...")
        
        response = self.engine.get_chatgpt_response(combined_prompt)
        if response:
            updated_file = UPDATED_FOLDER / Path(self.current_file_path).name
            saved = self.helpers.save_file(str(updated_file), response)
            if saved:
                self.append_output(f"✅ Updated file saved: {updated_file}")
            else:
                self.append_output(f"❌ Failed to save: {updated_file}")
        else:
            self.append_output("❌ No response from ChatGPT.")

    def self_heal(self):
        """Run self-healing on the current file."""
        if not self.current_file_path:
            self.helpers.show_warning("No file loaded.", "Warning")
            return
        
        self.append_output("Self-healing in progress...")
        response = self.engine.self_heal_file(self.current_file_path)
        if response:
            updated_file = UPDATED_FOLDER / Path(self.current_file_path).name
            saved = self.helpers.save_file(str(updated_file), response)
            if saved:
                self.append_output(f"✅ Self-healed file saved: {updated_file}")
            else:
                self.append_output(f"❌ Failed to save self-healed file: {updated_file}")
        else:
            self.append_output("❌ Self-Heal did not produce a response.")

    def run_tests(self):
        """Run tests on the current file."""
        if not self.current_file_path:
            self.helpers.show_warning("No file loaded.", "Warning")
            return
        
        self.append_output("Running tests...")
        results = self.engine.run_tests(self.current_file_path)
        self.append_output("Test run complete.")

    # --- New: Project Scan Operation ---
        
    def on_scan_project(self):
        """Trigger a project scan with live progress reporting."""
        self.append_output("Scanning project...")
        if self.project_scanner:
            try:
                # Define a callback that updates the progress bar.
                def progress_callback(percent):
                    self.progress_bar.setValue(percent)
                    self.append_output(f"Scan progress: {percent}%")
                
                # Trigger scan_project with the progress callback.
                self.project_scanner.scan_project(progress_callback=progress_callback)
                self.append_output("✅ Project scan completed.")
            except Exception as e:
                self.append_output(f"❌ Project scan error: {e}")
        else:
            self.append_output("Project scanner service not available.")

    # --- Prompt Operations ---

    def send_prompt(self):
        """Send a prompt to ChatGPT."""
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self.append_output("Please enter a prompt.")
            return
        
        self.append_output("Sending prompt to ChatGPT...")
        response = self.engine.get_chatgpt_response(prompt)
        if response:
            self.prompt_response.setPlainText(response)
            self.append_output("✅ Response received.")
        else:
            self.prompt_response.setPlainText("❌ No response received.")
            self.append_output("❌ No response received.")

    def process_batch_files(self):
        """Process multiple files with the same prompt."""
        file_list = self.engine.prioritize_files()
        if not file_list:
            self.append_output("No files found for batch processing.")
            return
        
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self.append_output("Please enter a prompt for batch processing.")
            return
        
        total_files = len(file_list)
        self.append_output(f"Processing {total_files} files with the shared prompt...")
        
        batch_results = []
        for index, file_path in enumerate(file_list, start=1):
            progress_percent = int((index / total_files) * 100)
            self.progress_bar.setValue(progress_percent)
            
            file_content = self.helpers.read_file(file_path)
            if not file_content:
                batch_results.append(f"[WARNING] Failed to read {file_path}")
                continue
            
            composite_prompt = f"{prompt}\n\n---\n\n{file_content}"
            self.append_output(f"Processing {file_path}...")
            response = self.engine.get_chatgpt_response(composite_prompt)
            
            if response:
                updated_file = UPDATED_FOLDER / Path(file_path).name
                if self.helpers.save_file(str(updated_file), response):
                    batch_results.append(f"[SUCCESS] {updated_file} saved.")
                else:
                    batch_results.append(f"[ERROR] Failed to save {updated_file}.")
            else:
                batch_results.append(f"[ERROR] No response for {file_path}.")
        
        self.prompt_response.setPlainText("\n".join(batch_results))
        self.append_output("Batch processing complete.")

    # --- Debug Operations ---

    def on_run_debug(self):
        """Run a debug session."""
        self.append_output("Starting debug session...")
        if self.debug_service:
            try:
                result = self.debug_service.run_debug_cycle()
                self.append_output(f"Debug session completed: {result}")
                if self.dispatcher:
                    self.dispatcher.emit_debug_completed(result)
            except Exception as e:
                error_msg = f"Error running debug session: {e}"
                self.append_output(error_msg)
                if self.dispatcher:
                    self.dispatcher.emit_debug_error(str(e))
        else:
            self.append_output("Debug service not available.")

    def on_apply_fix(self):
        """Apply a fix."""
        self.append_output("Applying fix...")
        if self.fix_service:
            try:
                result = self.fix_service.apply_fix()
                self.append_output(f"Fix applied: {result}")
                if self.dispatcher:
                    self.dispatcher.emit_fix_applied(result)
            except Exception as e:
                error_msg = f"Error applying fix: {e}"
                self.append_output(error_msg)
                if self.dispatcher:
                    self.dispatcher.emit_fix_error(str(e))
        else:
            self.append_output("Fix service not available.")

    def on_rollback_fix(self):
        """Roll back a fix."""
        self.append_output("Rolling back fix...")
        if self.rollback_service:
            try:
                result = self.rollback_service.rollback_fix()
                self.append_output(f"Rollback successful: {result}")
                if self.dispatcher:
                    self.dispatcher.emit_rollback_completed(result)
            except Exception as e:
                error_msg = f"Error during rollback: {e}"
                self.append_output(error_msg)
                if self.dispatcher:
                    self.dispatcher.emit_rollback_error(str(e))
        else:
            self.append_output("Rollback service not available.")

    def on_cursor_execute(self):
        """Execute a prompt via the Cursor integration by adding it to the task queue."""
        self.append_output("Queueing debug prompt for execution via Cursor...")
        if self.cursor_manager and hasattr(self.cursor_manager, 'queue_task'):
            try:
                # Use the queue_task method instead of a direct execute_prompt
                prompt = "## DEBUG PROMPT\nPlease analyze the current error state and generate a suggested fix."
                self.cursor_manager.queue_task(prompt)
                self.append_output(f"✅ Debug task queued: {prompt[:50]}...")
                # TODO: Refresh queue display
                # Consider automatically accepting this specific task if desired,
                # or rely on manual/auto-accept mechanism.

                # Original code (kept for reference):
                # generated_code = self.cursor_manager.execute_prompt(prompt)
                # if generated_code:
                #     self.append_output("Cursor generated code:")
                #     self.append_output(generated_code)
                #     if self.dispatcher:
                #         self.dispatcher.emit_cursor_code_generated(generated_code)
                # else:
                #     self.append_output("Cursor did not generate any code.")
            except Exception as e:
                error_msg = f"Error queueing prompt via Cursor: {e}"
                self.append_output(error_msg)
                if self.dispatcher and hasattr(self.dispatcher, "emit_cursor_error"):
                    self.dispatcher.emit_cursor_error(str(e))
                if self.logger:
                    self.logger.error(error_msg, exc_info=True)
        else:
            self.append_output("❌ Cursor manager not available or doesn't support queue_task.")

    # --- Task Queue Operations (New & Updated) ---

    @pyqtSlot()
    def on_add_task(self):
        """Construct task dictionary from UI fields and queue it."""
        prompt_text = self.task_prompt_edit.toPlainText().strip()
        if not prompt_text:
            self.append_output("⚠️ Please enter a task prompt.")
            # Maybe show a warning popup instead/as well
            # self.helpers.show_warning("Task prompt cannot be empty.", "Input Error")
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
                # self.helpers.show_warning(f"Invalid Context JSON: {e}. Please provide a valid JSON object.", "Input Error")
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
                # The queue list will update via the callback
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
                # Note: The actual execution happens in the manager.
                # We might need a signal back from the manager upon completion/error.
                # TODO: Add logic to refresh self.task_queue_list display
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

    def _handle_cursor_manager_update(self, update_data: Dict[str, Any]):
        """Handle updates pushed from the CursorSessionManager via callback."""
        event_type = update_data.get("event_type")
        task_id = update_data.get("task_id")
        
        if event_type == "queue_changed":
            queue_snapshot = update_data.get("queue_snapshot", []) 
            self._update_task_queue_display(queue_snapshot)
            self.append_output("Task queue display updated.")
        elif event_type == "task_started":
            self.append_output(f"▶️ Task [{task_id[:6]}...] started.")
            # Update task data in our dictionary
            if task_id not in self.tasks:
                self.tasks[task_id] = {}
            self.tasks[task_id]["status"] = "running"
            self.tasks[task_id]["task_prompt"] = update_data.get("task_prompt", "")
            self._update_task_item_status(task_id, "running")
        elif event_type == "task_completed":
            self.append_output(f"✅ Task [{task_id[:6]}...] completed.")
            # Update task data in our dictionary
            if task_id not in self.tasks:
                self.tasks[task_id] = {}
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["task_prompt"] = update_data.get("task_prompt", "")
            self.tasks[task_id]["response"] = update_data.get("response", "")
            self.tasks[task_id]["timestamp"] = datetime.now().isoformat()
            
            # Add any test generation data
            if "generated_test_path" in update_data:
                self.tasks[task_id]["generated_test_path"] = update_data.get("generated_test_path")
                
            # Add any coverage analysis
            if "coverage_analysis" in update_data:
                self.tasks[task_id]["coverage_analysis"] = update_data.get("coverage_analysis")
                
            # Include file path if provided
            if "file_path" in update_data:
                self.tasks[task_id]["file_path"] = update_data.get("file_path")
                
            # Include mode if available
            if "mode" in update_data:
                self.tasks[task_id]["mode"] = update_data.get("mode")
                
            self._update_task_item_status(task_id, "completed")
        elif event_type == "task_failed":
            error_msg = update_data.get("error", "Unknown error")
            self.append_output(f"❌ Task [{task_id[:6]}...] failed. Error: {error_msg}")
            # Update task data in our dictionary
            if task_id not in self.tasks:
                self.tasks[task_id] = {}
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["task_prompt"] = update_data.get("task_prompt", "")
            self.tasks[task_id]["error"] = error_msg
            self.tasks[task_id]["timestamp"] = datetime.now().isoformat()
            self._update_task_item_status(task_id, "failed")
        elif event_type == "queue_empty":
            self.append_output("Task queue is empty.")
            self._update_task_queue_display([])
        elif event_type == "task_rejected":
            reason = update_data.get("reason", "Unknown reason")
            self.append_output(f"⚠️ Task [{task_id[:6]}...] rejected: {reason}")
            # Update task data in our dictionary
            if task_id not in self.tasks:
                self.tasks[task_id] = {}
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["error"] = f"Rejected: {reason}"
            self.tasks[task_id]["timestamp"] = datetime.now().isoformat()
            self._update_task_item_status(task_id, "failed", f"Rejected: {reason}")
        # Add handlers for lifecycle stages
        elif event_type == "lifecycle_stage_change":
            stage = update_data.get("stage")
            self.append_output(f"🔄 Task [{task_id[:6]}...] in {stage} stage.")
            # Update task data in our dictionary
            if task_id not in self.tasks:
                self.tasks[task_id] = {}
            self.tasks[task_id]["status"] = stage
            self.tasks[task_id]["task_prompt"] = update_data.get("task_prompt", "")
            self._update_task_item_status(task_id, stage)

    def _get_status_prefix(self, status: Optional[str]) -> str:
        """Return a prefix string based on task status."""
        status_map = {
            "queued": "[Q]",
            "running": "[R]", # Or ▶️ if unicode preferred
            "processing": "[R]",
            "completed": "[✓]",
            "failed": "[X]",
            # Add lifecycle stages
            "validating": "[V]",
            "injecting": "[I]",
            "approving": "[A]",
            "dispatching": "[D]"
        }
        return status_map.get(status, "[?]") # Default for unknown status

    def _update_task_queue_display(self, queue_snapshot: List[Dict[str, Any]]):
        """Clear and repopulate the task queue list widget using task dictionaries."""
        # Preserve selection/scroll state if possible (more advanced)
        # current_selection = self.task_queue_list.currentItem()

        self.task_queue_list.clear()
        if not queue_snapshot:
            self.task_queue_list.addItem("(Queue Empty)")
            self.task_queue_list.setEnabled(False)
        else:
            for task in queue_snapshot:
                task_id = task.get("task_id", "NO_ID")
                priority = task.get("priority", "med")
                source = task.get("source", "?")
                prompt = task.get("prompt", "<No Prompt>")
                status = task.get("status", "queued") # Status from manager
                
                # Check for lifecycle stage - show the most recent stage
                lifecycle = task.get("lifecycle", {})
                if lifecycle:
                    # Determine the most recent stage based on timestamps
                    if "dispatched_at" in lifecycle:
                        status = "dispatching"
                    elif "approved_at" in lifecycle:
                        status = "approving"
                    elif "validated_at" in lifecycle:
                        status = "validating"
                    elif "injected_at" in lifecycle:
                        status = "injecting"
                
                status_prefix = self._get_status_prefix(status)
                display_text = f"{status_prefix} [{priority[:1].upper()}] {source[:3]} | {prompt[:40]}..."
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, task) # Store the full task dict 
                
                # Extended tooltip with lifecycle information
                tooltip = f"ID: {task_id}\nStatus: {status}\nPrompt: {prompt}"
                if lifecycle:
                    tooltip += "\n--- Lifecycle ---"
                    if "queued_at" in lifecycle:
                        tooltip += f"\nQueued: {lifecycle['queued_at']}"
                    if "injected_at" in lifecycle:
                        tooltip += f"\nContext Injected: {lifecycle['injected_at']}"
                    if "validated_at" in lifecycle:
                        tooltip += f"\nValidated: {lifecycle['validated_at']}"
                    if "approved_at" in lifecycle:
                        tooltip += f"\nApproved: {lifecycle['approved_at']}"
                    if "dispatched_at" in lifecycle:
                        tooltip += f"\nDispatched: {lifecycle['dispatched_at']}"
                    if "completed_at" in lifecycle:
                        tooltip += f"\nCompleted: {lifecycle['completed_at']}"
                
                # Add coverage information if available in the task
                if 'coverage_analysis' in task:
                    coverage = task.get('coverage_analysis', {})
                    tooltip += f"\n\nCoverage: {coverage.get('percentage', 0)}%"
                    
                    if 'trend' in coverage:
                        tooltip += f"\nTrend: {coverage.get('trend')}"
                        
                    if coverage.get('needs_improvement', False):
                        tooltip += "\nRecommendation: Improve test coverage"
                
                # Add file path if available
                if 'file_path' in task:
                    tooltip += f"\nFile: {task.get('file_path')}"
                    
                # Add generated test path if available
                if 'generated_test_path' in task:
                    tooltip += f"\nGenerated Test: {task.get('generated_test_path')}"
                
                item.setToolTip(tooltip)
                
                # Apply background color based on status
                if status == 'running' or status == 'processing':
                    item.setBackground(QColor(230, 255, 230))  # Light green
                elif status == 'completed':
                    item.setBackground(QColor(220, 240, 255))  # Light blue
                elif status == 'failed':
                    item.setBackground(QColor(255, 230, 230))  # Light red
                
                self.task_queue_list.addItem(item)
            self.task_queue_list.setEnabled(True)
            # Restore selection if needed

    def _update_task_item_status(self, task_id: str, new_status: str, message: str = None):
        """Finds a task item by ID and updates its display text/status."""
        for i in range(self.task_queue_list.count()):
            item = self.task_queue_list.item(i)
            task_data = item.data(Qt.UserRole)
            if task_data and task_data.get("task_id") == task_id:
                # Update the stored status first (optional but good practice)
                task_data["status"] = new_status 
                item.setData(Qt.UserRole, task_data) 
                
                # Update display text
                priority = task_data.get("priority", "med")
                source = task_data.get("source", "?")
                prompt = task_data.get("prompt", "<No Prompt>")
                status_prefix = self._get_status_prefix(new_status)
                display_text = f"{status_prefix} [{priority[:1].upper()}] {source[:3]} | {prompt[:40]}..."
                item.setText(display_text)
                
                # Update tooltip with optional message
                tooltip = f"ID: {task_id}\nStatus: {new_status}\nPrompt: {prompt}"
                if message:
                    tooltip += f"\nMessage: {message}"
                
                # Add lifecycle info if available
                lifecycle = task_data.get("lifecycle", {})
                if lifecycle:
                    tooltip += "\n--- Lifecycle ---"
                    stages = ["queued_at", "injected_at", "validated_at", "approved_at", "dispatched_at", "completed_at"]
                    for stage in stages:
                        if stage in lifecycle:
                            tooltip += f"\n{stage.replace('_at', '').capitalize()}: {lifecycle[stage]}"
                
                item.setToolTip(tooltip)
                break # Found and updated

    # --- Slot for Double-Click ---
    @pyqtSlot(QListWidgetItem)
    def on_task_double_clicked(self, item):
        """Show task details on double-click with enhanced lifecycle information."""
        self._show_task_details(item)

    def _show_task_details(self, item):
        """Show detailed information about a task when double-clicked."""
        task_data = item.data(Qt.UserRole)
        if not task_data:
            return
            
        task_id = task_data.get("task_id", "Unknown")
            
        # Create a detailed message with formatting
        details = f"<h3>Task Details: {task_id}</h3>"
        details += f"<p><b>Prompt:</b> {task_data.get('prompt', 'Unknown')}</p>"
        details += f"<p><b>Status:</b> {task_data.get('status', 'Unknown')}</p>"
        
        # Add file path if available
        if 'file_path' in task_data:
            details += f"<p><b>File:</b> {task_data.get('file_path')}</p>"
            
        # Add mode information if available
        if 'mode' in task_data:
            details += f"<p><b>Mode:</b> {task_data.get('mode')}</p>"
            
        # Add test generation information if available
        if 'generated_test_path' in task_data:
            details += f"<p><b>Generated Test:</b> {task_data.get('generated_test_path')}</p>"
            
        # Add coverage analysis if available
        if 'coverage_analysis' in task_data:
            coverage = task_data.get('coverage_analysis', {})
            percentage = coverage.get('percentage', 0)
            
            # Determine color based on coverage percentage
            color = "green" if percentage >= 80 else "orange" if percentage >= 50 else "red"
            
            details += f"<div style='margin-top: 10px;'>"
            details += f"<h4>Test Coverage Analysis</h4>"
            details += f"<p><b>Coverage:</b> <span style='color: {color};'>{percentage}%</span></p>"
            
            # Add trend information
            if 'trend' in coverage:
                trend = coverage.get('trend')
                trend_icon = "▲" if trend == "increasing" else "▼" if trend == "decreasing" else "◆"
                details += f"<p><b>Trend:</b> {trend_icon} {trend}</p>"
                
            # Add uncovered functions count
            if 'uncovered_functions_count' in coverage:
                details += f"<p><b>Uncovered Functions:</b> {coverage.get('uncovered_functions_count')}</p>"
                
            # Add recommendation
            if coverage.get('needs_improvement', False):
                details += f"<p style='color: orange;'><b>Recommendation:</b> Test coverage should be improved</p>"
                
            details += "</div>"
            
        # Add lifecycle information if available
        lifecycle = task_data.get('lifecycle', {})
        if lifecycle:
            details += f"<div style='margin-top: 10px;'>"
            details += f"<h4>Lifecycle</h4>"
            stages = [
                ("queued_at", "Queued"),
                ("injected_at", "Context Injected"), 
                ("validated_at", "Validated"),
                ("approved_at", "Approved"),
                ("dispatched_at", "Dispatched"),
                ("completed_at", "Completed")
            ]
            for key, label in stages:
                if key in lifecycle:
                    details += f"<p><b>{label}:</b> {lifecycle[key]}</p>"
            details += "</div>"
                
        # Display the details in a message box
        msg_box = QMessageBox()
        msg_box.setWindowTitle(f"Task Details - {task_id}")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(details)
        
        # Add buttons for actions
        if task_data.get('status') == 'failed':
            retry_button = msg_box.addButton("Retry Task", QMessageBox.ActionRole)
        
        if task_data.get('coverage_analysis', {}).get('needs_improvement', False):
            improve_button = msg_box.addButton("Improve Tests", QMessageBox.ActionRole)
            
        close_button = msg_box.addButton("Close", QMessageBox.RejectRole)
        
        # Show the dialog and process the result
        msg_box.exec_()
        
        # Handle button clicks
        clicked_button = msg_box.clickedButton()
        
        if clicked_button and clicked_button.text() == "Retry Task" and task_data.get('status') == 'failed':
            self._requeue_task(task_id)
        elif clicked_button and clicked_button.text() == "Improve Tests" and task_data.get('coverage_analysis', {}).get('needs_improvement', False):
            self._improve_test_coverage(task_id, task_data)

    def _handle_context_menu(self, position):
        """Handle right-click context menu on task list items."""
        item = self.task_queue_list.itemAt(position)
        if not item:
            return
            
        task_data = item.data(Qt.UserRole)
        if not task_data:
            return
            
        task_id = task_data.get("task_id", "Unknown")
            
        # Create context menu
        menu = QMenu()
        status = task_data.get('status', 'unknown')
        
        # Add actions based on task status
        if status == 'queued':
            cancel_action = menu.addAction("Cancel Task")
            boost_action = menu.addAction("Boost Priority")
        elif status == 'completed':
            view_action = menu.addAction("View Details")
            if task_data.get('coverage_analysis', {}).get('needs_improvement', False):
                improve_tests_action = menu.addAction("Improve Test Coverage")
        elif status == 'failed':
            retry_action = menu.addAction("Retry Task")
            view_action = menu.addAction("View Error Details")
            
        # Always add these options
        copy_action = menu.addAction("Copy Task ID")
        
        # Show the menu and get the selected action
        action = menu.exec_(self.task_queue_list.mapToGlobal(position))
        
        # Handle the selected action
        if not action:
            return
            
        if status == 'queued' and action.text() == "Cancel Task":
            self._cancel_task(task_id)
        elif status == 'queued' and action.text() == "Boost Priority":
            self._boost_task_priority(task_id)
        elif action.text() == "View Details" or action.text() == "View Error Details":
            self._show_task_details(item)
        elif status == 'failed' and action.text() == "Retry Task":
            self._requeue_task(task_id)
        elif action.text() == "Copy Task ID":
            QApplication.clipboard().setText(task_id)
        elif action.text() == "Improve Test Coverage":
            self._improve_test_coverage(task_id, task_data)

    # --- Signal Handlers ---

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
        current_text = self.prompt_response.toPlainText()
        if current_text:
            self.prompt_response.setPlainText(f"{current_text}\n{message}")
        else:
            self.prompt_response.setPlainText(message)
        if self.logger:
            self.logger.info(f"[AIDE] {message}")

    def show_task_context_menu(self, position):
        """Show context menu for tasks."""
        self._handle_context_menu(position)

    def _extract_task_id(self, display_text):
        """Extract task ID from display text."""
        # Expected format: "[Status] ID: Prompt"
        try:
            # Skip the status prefix and focus on the ID part
            parts = display_text.split(" ", 2)
            if len(parts) < 3:
                return None
            
            # Extract ID (remove the colon)
            task_id = parts[1].strip().rstrip(":")
            return task_id
        except:
            return None

    def _get_task_data(self, task_id):
        """Get task data from stored tasks dictionary."""
        return self.tasks.get(task_id, None)

    def _add_task_to_queue(self, task_data):
        """Add a task to the queue using cursor manager."""
        if self.cursor_manager and hasattr(self.cursor_manager, 'queue_task'):
            try:
                self.cursor_manager.queue_task(task_data)
                self.append_output(f"✅ Task queued: {task_data.get('prompt', '')[:50]}...")
                return True
            except Exception as e:
                error_msg = f"❌ Error queueing task: {e}"
                self.append_output(error_msg)
                if self.logger:
                    self.logger.error(error_msg, exc_info=True)
                return False
        else:
            self.append_output("❌ Cursor manager not available or doesn't support queue_task.")
            return False

    def _requeue_task(self, task_id):
        """Requeue a failed task."""
        task_data = self._get_task_data(task_id)
        if not task_data:
            self.append_output(f"❌ Cannot requeue task {task_id}: task data not found.")
            return
        
        # Create a new task with the same data
        new_task = {
            "prompt": task_data.get("task_prompt", ""),
            "priority": task_data.get("priority", "medium"),
            "source": task_data.get("source", "requeue"),
            "file_path": task_data.get("file_path"),
            "mode": task_data.get("mode"),
            "parent_task_id": task_id  # Link to the original task
        }
        
        # Add any additional data that might be useful
        if "context" in task_data:
            new_task["context"] = task_data["context"]
            
        success = self._add_task_to_queue(new_task)
        if success:
            QMessageBox.information(self, "Task Requeued", f"Task {task_id} has been requeued.")
        else:
            QMessageBox.warning(self, "Requeue Failed", f"Failed to requeue task {task_id}.")

    def _cancel_task(self, task_id):
        """Cancel a queued task."""
        if self.cursor_manager and hasattr(self.cursor_manager, 'cancel_task'):
            try:
                self.cursor_manager.cancel_task(task_id)
                self.append_output(f"✅ Task {task_id} cancelled.")
                
                # Update our local task data
                if task_id in self.tasks:
                    self.tasks[task_id]["status"] = "cancelled"
                    self._update_task_item_status(task_id, "cancelled")
                    
                return True
            except Exception as e:
                error_msg = f"❌ Error cancelling task {task_id}: {e}"
                self.append_output(error_msg)
                if self.logger:
                    self.logger.error(error_msg, exc_info=True)
                return False
        else:
            self.append_output("❌ Cursor manager not available or doesn't support cancel_task.")
            return False

    def _boost_task_priority(self, task_id):
        """Boost the priority of a queued task."""
        if self.cursor_manager and hasattr(self.cursor_manager, 'update_task_priority'):
            try:
                self.cursor_manager.update_task_priority(task_id, "high")
                self.append_output(f"✅ Task {task_id} priority boosted to high.")
                
                # Update our local task data
                if task_id in self.tasks:
                    self.tasks[task_id]["priority"] = "high"
                    
                return True
            except Exception as e:
                error_msg = f"❌ Error boosting priority for task {task_id}: {e}"
                self.append_output(error_msg)
                if self.logger:
                    self.logger.error(error_msg, exc_info=True)
                return False
        else:
            self.append_output("❌ Cursor manager not available or doesn't support update_task_priority.")
            return False

    def _improve_test_coverage(self, task_id, task_data):
        """Create a new task to improve test coverage for the given task."""
        file_path = task_data.get('file_path')
        if not file_path:
            QMessageBox.warning(self, "Error", "Cannot improve tests: No file path available")
            return
            
        # Get coverage information
        coverage = task_data.get('coverage_analysis', {})
        percentage = coverage.get('percentage', 0)
        uncovered_count = coverage.get('uncovered_functions_count', 0)
        
        # Create a new task with appropriate metadata
        new_task = {
            "prompt": f"Improve test coverage for {file_path}. Current coverage is {percentage}% with {uncovered_count} uncovered functions. Focus on generating tests for untested functionality.",
            "file_path": file_path,
            "mode": "coverage_driven",
            "analyze_coverage": True,
            "generate_tests": True,
            "priority": 10,  # High priority
            "parent_task_id": task_id  # Link to the original task
        }
        
        # Add the task to the queue
        self._add_task_to_queue(new_task)
        
        # Show confirmation
        QMessageBox.information(self, "Task Added", f"Added task to improve test coverage for {file_path}")
