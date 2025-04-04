#!/usr/bin/env python3
"""
CursorExecutionTab.py

A unified PyQt5 tab interface for executing and managing Cursor dispatching operations.
This version merges two iterations:
- It retains all UI elements for prompt, sequence, test, and Git operations.
- It cleanly calls backend logic via CursorDispatcher (which itself is built on a micro–factory architecture).
- It ensures signals and worker threads are used to keep the UI responsive.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QComboBox, QTextEdit, QTabWidget, QGroupBox, QCheckBox,
    QFileDialog, QSplitter, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox, QLineEdit, QApplication, QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot

from core.refactor.cursor_dispatcher import CursorDispatcher, logger
from core.PromptExecutionService import PromptExecutionService
from interfaces.pyqt.tabs.task_history_modal import TaskDetailsModal

# Setup logging for this UI module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CursorExecutionTab")


class WorkerThread(QThread):
    """Worker thread for executing tasks without blocking the UI."""
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(int)
    
    def __init__(self, task, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            result = self.task(*self.args, **self.kwargs)
            self.finished_signal.emit(True, str(result))
        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")
            self.finished_signal.emit(False, str(e))


class CursorExecutionTab(QWidget):
    """
    PyQt5 tab for executing and managing Cursor dispatching operations.
    
    Provides a GUI interface for:
    - Selecting and rendering templates (prompt execution)
    - Running prompt sequences
    - Generating and running tests
    - Performing Git operations (install hooks, commit changes)
    - *NEW* Direct Cursor Task Injection for automated processing
    """
    
    # Signals to report status back to the main window or logging agent
    prompt_executed = pyqtSignal(bool, str, str)     # success, result, error
    sequence_executed = pyqtSignal(bool, str, str)     # success, result, error
    tests_generated = pyqtSignal(bool, str, str)       # success, file_path, error
    tests_run = pyqtSignal(bool, str, str)             # success, output, error
    git_operation_completed = pyqtSignal(bool, str)    # success, message
    cursor_task_injected = pyqtSignal(bool, str)       # success, task_path
    
    def __init__(self, services: Dict[str, Any], parent: Optional[QWidget] = None):
        """
        Initialize the CursorExecutionTab.
        
        Args:
            services: Dictionary of application services
            parent: Optional parent widget
        """
        super().__init__(parent)
        self.services = services
        
        # Initialize the backend CursorDispatcher (which now encapsulates our micro-factory architecture)
        self.dispatcher = CursorDispatcher()
        
        # Initialize PromptExecutionService for direct task injection
        self.prompt_service = PromptExecutionService()
        
        # Setup UI components
        self.init_ui()
        
        # Load available templates and sequences
        self.load_templates()
        self.load_sequences()
        
    def init_ui(self):
        """Initialize the user interface components."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Create a tab widget for organizing operations
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Tab for executing a single prompt
        prompt_tab = self._create_prompt_tab()
        tabs.addTab(prompt_tab, "Execute Prompt")
        
        # Tab for executing sequences
        sequence_tab = self._create_sequence_tab()
        tabs.addTab(sequence_tab, "Run Sequence")
        
        # Tab for test management
        test_tab = self._create_test_tab()
        tabs.addTab(test_tab, "Test Management")
        
        # Tab for Git integration
        git_tab = self._create_git_tab()
        tabs.addTab(git_tab, "Git Integration")
        
        # New tab for Cursor Task Injection
        cursor_task_tab = self._create_cursor_task_tab()
        tabs.addTab(cursor_task_tab, "Cursor Task Injection")
        
        # New tab for Task History
        task_history_tab = self._create_task_history_tab()
        tabs.addTab(task_history_tab, "Task History")
        
    def _create_prompt_tab(self) -> QWidget:
        """Create the prompt execution tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Template selection group
        template_group = QGroupBox("Template Selection")
        template_layout = QVBoxLayout(template_group)
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(300)
        template_layout.addWidget(QLabel("Select Template:"))
        template_layout.addWidget(self.template_combo)
        
        # Context input group
        context_group = QGroupBox("Context Variables")
        context_layout = QVBoxLayout(context_group)
        self.context_edit = QTextEdit()
        self.context_edit.setPlaceholderText('{"STRATEGY_DESCRIPTION": "Create a modular PyQt5 tab..."}')
        context_layout.addWidget(QLabel("Context JSON:"))
        context_layout.addWidget(self.context_edit)
        
        # Initial code input group
        code_group = QGroupBox("Initial Code")
        code_layout = QVBoxLayout(code_group)
        self.code_edit = QTextEdit()
        self.code_edit.setPlaceholderText("# Initial code to send to Cursor")
        code_layout.addWidget(QLabel("Starting Code:"))
        code_layout.addWidget(self.code_edit)
        
        # Control buttons and options
        control_layout = QHBoxLayout()
        self.auto_checkbox = QCheckBox("Auto Mode (No User Input)")
        control_layout.addWidget(self.auto_checkbox)
        self.run_tests_checkbox = QCheckBox("Run Tests")
        self.run_tests_checkbox.setChecked(True)
        control_layout.addWidget(self.run_tests_checkbox)
        self.git_commit_checkbox = QCheckBox("Git Commit")
        control_layout.addWidget(self.git_commit_checkbox)
        self.execute_button = QPushButton("Execute Prompt")
        self.execute_button.setMinimumHeight(40)
        self.execute_button.clicked.connect(self.execute_prompt)
        control_layout.addWidget(self.execute_button)
        
        # Progress and output areas
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        output_group = QGroupBox("Execution Output")
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        
        # Assemble prompt tab
        layout.addWidget(template_group)
        layout.addWidget(context_group)
        layout.addWidget(code_group)
        layout.addLayout(control_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(output_group)
        
        return tab
        
    def _create_sequence_tab(self) -> QWidget:
        """Create the sequence execution tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Sequence selection group
        seq_group = QGroupBox("Sequence Selection")
        seq_layout = QVBoxLayout(seq_group)
        self.sequence_combo = QComboBox()
        seq_layout.addWidget(QLabel("Select Sequence:"))
        seq_layout.addWidget(self.sequence_combo)
        
        # Sequence info display
        self.seq_info_text = QTextEdit()
        self.seq_info_text.setReadOnly(True)
        
        # Sequence control buttons
        seq_control_layout = QHBoxLayout()
        self.seq_auto_checkbox = QCheckBox("Auto Mode")
        seq_control_layout.addWidget(self.seq_auto_checkbox)
        self.load_seq_button = QPushButton("Load Sequence")
        self.load_seq_button.clicked.connect(self.load_sequence_info)
        seq_control_layout.addWidget(self.load_seq_button)
        self.run_seq_button = QPushButton("Run Sequence")
        self.run_seq_button.setMinimumHeight(40)
        self.run_seq_button.clicked.connect(self.run_sequence)
        seq_control_layout.addWidget(self.run_seq_button)
        
        # Steps table
        self.seq_steps_table = QTableWidget(0, 3)
        self.seq_steps_table.setHorizontalHeaderLabels(["Step", "Template", "Output File"])
        self.seq_steps_table.horizontalHeader().setStretchLastSection(True)
        
        # Sequence output area
        seq_output_group = QGroupBox("Sequence Output")
        seq_output_layout = QVBoxLayout(seq_output_group)
        self.seq_output_text = QTextEdit()
        self.seq_output_text.setReadOnly(True)
        seq_output_layout.addWidget(self.seq_output_text)
        
        # Assemble sequence tab
        layout.addWidget(seq_group)
        layout.addWidget(self.seq_info_text)
        layout.addLayout(seq_control_layout)
        layout.addWidget(self.seq_steps_table)
        layout.addWidget(seq_output_group)
        
        return tab
        
    def _create_test_tab(self) -> QWidget:
        """Create the test management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Test file selection group
        test_file_group = QGroupBox("Test File Selection")
        test_file_layout = QHBoxLayout(test_file_group)
        self.test_file_edit = QLineEdit()
        test_file_layout.addWidget(QLabel("File to Test:"))
        test_file_layout.addWidget(self.test_file_edit)
        self.browse_test_button = QPushButton("Browse")
        self.browse_test_button.clicked.connect(self.browse_test_file)
        test_file_layout.addWidget(self.browse_test_button)
        
        # Test control buttons
        test_control_layout = QHBoxLayout()
        self.generate_test_button = QPushButton("Generate Tests")
        self.generate_test_button.clicked.connect(self.generate_tests)
        test_control_layout.addWidget(self.generate_test_button)
        self.run_test_button = QPushButton("Run Tests")
        self.run_test_button.clicked.connect(self.run_tests)
        test_control_layout.addWidget(self.run_test_button)
        
        # Test results display
        test_results_group = QGroupBox("Test Results")
        test_results_layout = QVBoxLayout(test_results_group)
        self.test_results_text = QTextEdit()
        self.test_results_text.setReadOnly(True)
        test_results_layout.addWidget(self.test_results_text)
        
        # Assemble test tab
        layout.addWidget(test_file_group)
        layout.addLayout(test_control_layout)
        layout.addWidget(test_results_group)
        
        return tab
        
    def _create_git_tab(self) -> QWidget:
        """Create the Git integration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Git commit controls
        commit_group = QGroupBox("Git Operations")
        commit_layout = QVBoxLayout(commit_group)
        self.commit_message_edit = QLineEdit()
        self.commit_message_edit.setPlaceholderText("Commit message")
        commit_layout.addWidget(QLabel("Commit Message:"))
        commit_layout.addWidget(self.commit_message_edit)
        git_buttons_layout = QHBoxLayout()
        self.install_hooks_button = QPushButton("Install Git Hooks")
        self.install_hooks_button.clicked.connect(self.install_git_hooks)
        git_buttons_layout.addWidget(self.install_hooks_button)
        self.commit_button = QPushButton("Commit Changes")
        self.commit_button.clicked.connect(self.commit_changes)
        git_buttons_layout.addWidget(self.commit_button)
        commit_layout.addLayout(git_buttons_layout)
        
        # Files to commit
        git_files_group = QGroupBox("Files to Commit")
        git_files_layout = QVBoxLayout(git_files_group)
        self.git_files_edit = QTextEdit()
        self.git_files_edit.setPlaceholderText("One file path per line")
        git_files_layout.addWidget(self.git_files_edit)
        
        # Git output display
        git_output_group = QGroupBox("Git Output")
        git_output_layout = QVBoxLayout(git_output_group)
        self.git_output_text = QTextEdit()
        self.git_output_text.setReadOnly(True)
        git_output_layout.addWidget(self.git_output_text)
        
        # Assemble Git tab
        layout.addWidget(commit_group)
        layout.addWidget(git_files_group)
        layout.addWidget(git_output_group)
        
        return tab
        
    def _create_cursor_task_tab(self) -> QWidget:
        """Create the Cursor task injection tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Template selection
        template_group = QGroupBox("Template Selection")
        template_layout = QVBoxLayout(template_group)
        
        template_header = QHBoxLayout()
        template_header.addWidget(QLabel("Select Template:"))
        self.cursor_template_combo = QComboBox()
        template_header.addWidget(self.cursor_template_combo)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_cursor_templates)
        template_header.addWidget(refresh_btn)
        template_layout.addLayout(template_header)
        
        # Context input group
        context_group = QGroupBox("Context Variables")
        context_layout = QVBoxLayout(context_group)
        self.cursor_context_edit = QTextEdit()
        self.cursor_context_edit.setPlaceholderText('{"STRATEGY_DESCRIPTION": "Create a modular PyQt5 tab..."}')
        context_layout.addWidget(QLabel("Context JSON:"))
        context_layout.addWidget(self.cursor_context_edit)
        
        # Target output
        target_group = QGroupBox("Output Target")
        target_layout = QHBoxLayout(target_group)
        target_layout.addWidget(QLabel("Target Output File/Folder:"))
        self.cursor_target_edit = QLineEdit()
        self.cursor_target_edit.setPlaceholderText("output/path/filename.py")
        target_layout.addWidget(self.cursor_target_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_cursor_target)
        target_layout.addWidget(browse_btn)
        
        # Controls - Add auto-execute checkbox
        controls_layout = QHBoxLayout()
        self.auto_execute_checkbox = QCheckBox("⚡ Auto-execute after injection")
        self.auto_execute_checkbox.setToolTip("Mark the task for automatic execution by Cursor without requiring manual approval")
        controls_layout.addWidget(self.auto_execute_checkbox)
        controls_layout.addStretch()
        self.create_task_btn = QPushButton("Create Cursor Task")
        self.create_task_btn.setMinimumHeight(40)
        self.create_task_btn.clicked.connect(self._create_cursor_task)
        controls_layout.addWidget(self.create_task_btn)
        
        # Task list display
        task_list_group = QGroupBox("Queued Tasks")
        task_list_layout = QVBoxLayout(task_list_group)
        self.task_table = QTableWidget(0, 4)
        self.task_table.setHorizontalHeaderLabels(["ID", "Template", "Target", "Timestamp"])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        task_list_layout.addWidget(self.task_table)
        
        task_controls = QHBoxLayout()
        self.refresh_tasks_btn = QPushButton("Refresh Task List")
        self.refresh_tasks_btn.clicked.connect(self._refresh_cursor_tasks)
        task_controls.addWidget(self.refresh_tasks_btn)
        self.delete_task_btn = QPushButton("Delete Selected Task")
        self.delete_task_btn.clicked.connect(self._delete_cursor_task)
        task_controls.addWidget(self.delete_task_btn)
        task_list_layout.addLayout(task_controls)
        
        # Result display
        result_group = QGroupBox("Task Creation Result")
        result_layout = QVBoxLayout(result_group)
        self.cursor_result_text = QTextEdit()
        self.cursor_result_text.setReadOnly(True)
        result_layout.addWidget(self.cursor_result_text)
        
        # Assemble the tab
        layout.addWidget(template_group)
        layout.addWidget(context_group)
        layout.addWidget(target_group)
        layout.addLayout(controls_layout)
        layout.addWidget(task_list_group)
        layout.addWidget(result_group)
        
        # Load available templates and initial task list
        self._load_cursor_templates()
        self._refresh_cursor_tasks()
        
        return tab
        
    def _create_task_history_tab(self) -> QWidget:
        """Create the task history tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Filter controls
        filter_group = QGroupBox("Filter Options")
        filter_layout = QHBoxLayout(filter_group)
        
        # Status filter
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Queued", "Completed", "Failed"])
        self.status_filter.currentTextChanged.connect(self._refresh_task_history)
        filter_layout.addWidget(self.status_filter)
        
        # Template filter
        filter_layout.addWidget(QLabel("Template:"))
        self.template_filter = QComboBox()
        self.template_filter.addItem("All")
        self.template_filter.currentTextChanged.connect(self._refresh_task_history)
        filter_layout.addWidget(self.template_filter)
        
        # Search
        filter_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search tasks...")
        self.search_edit.textChanged.connect(self._refresh_task_history)
        filter_layout.addWidget(self.search_edit)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_task_history)
        filter_layout.addWidget(refresh_btn)
        
        layout.addWidget(filter_group)
        
        # Task history table
        self.history_table = QTableWidget(0, 6)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "Template", "Target", "Status", "Timestamp", "Actions"
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.history_table)
        
        # Initialize task history
        self._refresh_task_history()
        self._update_template_filter()
        
        return tab
    
    def load_templates(self):
        """Load available templates into the UI."""
        try:
            self.template_combo.clear()
            # Use dispatcher's template directory
            templates_path = self.dispatcher.templates_path
            template_files = list(templates_path.glob("*.j2"))
            for template_file in template_files:
                self.template_combo.addItem(template_file.name)
            self.log_message(f"Loaded {len(template_files)} templates from {templates_path}")
        except Exception as e:
            self.log_message(f"Error loading templates: {str(e)}")
    
    def load_sequences(self):
        """Load available sequences into the UI."""
        try:
            self.sequence_combo.clear()
            sequences_path = self.dispatcher.templates_path.parent / "sequences"
            if not sequences_path.exists():
                self.log_message(f"Sequences directory not found: {sequences_path}")
                return
            sequence_files = list(sequences_path.glob("*.json"))
            for sequence_file in sequence_files:
                self.sequence_combo.addItem(sequence_file.stem)
            self.log_message(f"Loaded {len(sequence_files)} sequences from {sequences_path}")
        except Exception as e:
            self.log_message(f"Error loading sequences: {str(e)}")
    
    @pyqtSlot()
    def load_sequence_info(self):
        """Load and display information about the selected sequence."""
        try:
            sequence_name = self.sequence_combo.currentText()
            if not sequence_name:
                return
            sequence_path = self.dispatcher.templates_path.parent / "sequences" / f"{sequence_name}.json"
            if not sequence_path.exists():
                self.log_message(f"Sequence file not found: {sequence_path}")
                return
            with open(sequence_path, 'r') as f:
                sequence_data = json.load(f)
            info_text = f"Name: {sequence_data.get('name', sequence_name)}\n"
            info_text += f"Description: {sequence_data.get('description', 'No description')}\n"
            info_text += f"Steps: {len(sequence_data.get('steps', []))}\n"
            self.seq_info_text.setText(info_text)
            
            steps = sequence_data.get("steps", [])
            self.seq_steps_table.setRowCount(len(steps))
            for i, step in enumerate(steps):
                self.seq_steps_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
                self.seq_steps_table.setItem(i, 1, QTableWidgetItem(step.get("template", "")))
                self.seq_steps_table.setItem(i, 2, QTableWidgetItem(step.get("output_file", f"step_{i+1}")))
            self.log_message(f"Loaded sequence: {sequence_name}")
        except Exception as e:
            self.log_message(f"Error loading sequence info: {str(e)}")
    
    @pyqtSlot()
    def execute_prompt(self):
        """Execute a single prompt using the CursorDispatcher."""
        try:
            template_name = self.template_combo.currentText()
            if not template_name:
                self.log_message("No template selected")
                return
            try:
                context = json.loads(self.context_edit.toPlainText() or "{}")
            except json.JSONDecodeError:
                self.log_message("Invalid JSON in context field")
                return
            initial_code = self.code_edit.toPlainText() or "# Code will be generated by Cursor"
            skip_wait = self.auto_checkbox.isChecked()
            run_tests = self.run_tests_checkbox.isChecked()
            git_commit = self.git_commit_checkbox.isChecked()
            
            self.log_message(f"Executing prompt: {template_name}")
            self.progress_bar.setValue(10)
            
            def execute_task():
                self.update_progress(20)
                self.log_message("Rendering template...")
                prompt_text = self.dispatcher.run_prompt(template_name, context)
                self.update_progress(40)
                self.log_message("Sending prompt to Cursor...")
                code_result = self.dispatcher.send_and_wait(initial_code, prompt_text, skip_wait=skip_wait)
                if run_tests:
                    self.update_progress(60)
                    self.log_message("Running tests...")
                    code_file = self.dispatcher.output_path / "generated_tab.py"
                    test_success, test_output = self.dispatcher.run_tests(str(code_file))
                    self.log_message(f"Test result: {'PASSED' if test_success else 'FAILED'}")
                    if not test_success:
                        self.log_message(f"Test failures: {test_output}")
                if git_commit:
                    self.update_progress(80)
                    self.log_message("Committing changes...")
                    commit_context = {"CODE_DIFF_OR_FINAL": code_result}
                    commit_message = self.dispatcher.run_prompt("05_commit_and_version.j2", commit_context)
                    commit_message = commit_message.split("\n")[0]
                    files_to_commit = [str(self.dispatcher.output_path / "*.py")]
                    success = self.dispatcher.git_commit_changes(commit_message, files_to_commit)
                    if success:
                        self.log_message(f"Successfully committed: {commit_message}")
                    else:
                        self.log_message("Failed to commit changes")
                self.update_progress(100)
                return "Execution completed successfully"
            
            self.worker = WorkerThread(execute_task)
            self.worker.update_signal.connect(self.log_message)
            self.worker.progress_signal.connect(self.update_progress)
            self.worker.finished_signal.connect(self.execution_finished)
            self.worker.start()
            self.execute_button.setEnabled(False)
        except Exception as e:
            self.log_message(f"Error executing prompt: {str(e)}")
            self.progress_bar.setValue(0)
            self.execute_button.setEnabled(True)
    
    @pyqtSlot()
    def run_sequence(self):
        """Run a prompt sequence using the CursorDispatcher."""
        try:
            sequence_name = self.sequence_combo.currentText()
            if not sequence_name:
                self.log_message("No sequence selected")
                return
            skip_wait = self.seq_auto_checkbox.isChecked()
            self.log_message(f"Starting sequence: {sequence_name}")
            self.seq_output_text.clear()
            
            def execute_sequence_task():
                initial_context = {"STRATEGY_DESCRIPTION": "Create a modular PyQt5 tab for UX testing and live preview of widgets."}
                try:
                    self.log_message(f"Executing sequence {sequence_name}...")
                    final_code = self.dispatcher.execute_prompt_sequence(sequence_name, initial_context, skip_wait=skip_wait)
                    self.log_message("Sequence execution completed successfully")
                    return final_code
                except Exception as e:
                    self.log_message(f"Error during sequence execution: {str(e)}")
                    raise
            
            self.seq_worker = WorkerThread(execute_sequence_task)
            self.seq_worker.update_signal.connect(self.log_sequence_message)
            self.seq_worker.finished_signal.connect(self.sequence_finished)
            self.seq_worker.start()
            self.run_seq_button.setEnabled(False)
        except Exception as e:
            self.log_sequence_message(f"Error running sequence: {str(e)}")
            self.run_seq_button.setEnabled(True)
    
    @pyqtSlot()
    def browse_test_file(self):
        """Open file dialog to select a file to test."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Test", str(self.dispatcher.output_path), "Python Files (*.py)")
        if file_path:
            self.test_file_edit.setText(file_path)
    
    @pyqtSlot()
    def generate_tests(self):
        """Generate tests for the selected file."""
        try:
            file_path = self.test_file_edit.text()
            if not file_path:
                self.log_test_message("No file selected")
                return
            code_path = Path(file_path)
            if not code_path.exists():
                self.log_test_message(f"File not found: {file_path}")
                return
            test_file_path = self.dispatcher.output_path / f"test_{code_path.stem}.py"
            self.log_test_message(f"Generating tests for: {file_path}")
            self.log_test_message(f"Target test file: {test_file_path}")
            
            def generate_tests_task():
                self.dispatcher._create_test_file(file_path, str(test_file_path))
                return f"Tests generated successfully: {test_file_path}"
            
            self.test_worker = WorkerThread(generate_tests_task)
            self.test_worker.update_signal.connect(self.log_test_message)
            self.test_worker.finished_signal.connect(self.tests_generated)
            self.test_worker.start()
            self.generate_test_button.setEnabled(False)
            self.run_test_button.setEnabled(False)
        except Exception as e:
            self.log_test_message(f"Error generating tests: {str(e)}")
            self.generate_test_button.setEnabled(True)
            self.run_test_button.setEnabled(True)
    
    @pyqtSlot()
    def run_tests(self):
        """Run tests for the selected file."""
        try:
            file_path = self.test_file_edit.text()
            if not file_path:
                self.log_test_message("No file selected")
                return
            code_path = Path(file_path)
            if not code_path.exists():
                self.log_test_message(f"File not found: {file_path}")
                return
            self.log_test_message(f"Running tests for: {file_path}")
            
            def run_tests_task():
                success, output = self.dispatcher.run_tests(file_path)
                self.log_test_message("✅ Tests PASSED" if success else "❌ Tests FAILED")
                self.log_test_message(output)
                return f"Test execution completed: {'PASSED' if success else 'FAILED'}"
            
            self.test_worker = WorkerThread(run_tests_task)
            self.test_worker.update_signal.connect(self.log_test_message)
            self.test_worker.finished_signal.connect(self.tests_run)
            self.test_worker.start()
            self.generate_test_button.setEnabled(False)
            self.run_test_button.setEnabled(False)
        except Exception as e:
            self.log_test_message(f"Error running tests: {str(e)}")
            self.generate_test_button.setEnabled(True)
            self.run_test_button.setEnabled(True)
    
    @pyqtSlot()
    def install_git_hooks(self):
        """Install Git hooks using the CursorDispatcher."""
        try:
            self.log_git_message("Installing Git hooks...")
            def install_hooks_task():
                success = self.dispatcher.install_git_hook("post-commit")
                return f"Git hooks installation: {'Successful' if success else 'Failed'}"
            
            self.git_worker = WorkerThread(install_hooks_task)
            self.git_worker.update_signal.connect(self.log_git_message)
            self.git_worker.finished_signal.connect(self.git_operation_finished)
            self.git_worker.start()
            self.install_hooks_button.setEnabled(False)
        except Exception as e:
            self.log_git_message(f"Error installing Git hooks: {str(e)}")
            self.install_hooks_button.setEnabled(True)
    
    @pyqtSlot()
    def commit_changes(self):
        """Commit changes to Git using the CursorDispatcher."""
        try:
            commit_message = self.commit_message_edit.text()
            if not commit_message:
                self.log_git_message("No commit message provided")
                return
            files_text = self.git_files_edit.toPlainText()
            if not files_text:
                self.log_git_message("No files specified for commit")
                return
            files_to_commit = [line.strip() for line in files_text.split("\n") if line.strip()]
            self.log_git_message(f"Committing {len(files_to_commit)} files with message: {commit_message}")
            
            def commit_task():
                success = self.dispatcher.git_commit_changes(commit_message, files_to_commit)
                return f"Git commit: {'Successful' if success else 'Failed'}"
            
            self.git_worker = WorkerThread(commit_task)
            self.git_worker.update_signal.connect(self.log_git_message)
            self.git_worker.finished_signal.connect(self.git_operation_finished)
            self.git_worker.start()
            self.commit_button.setEnabled(False)
        except Exception as e:
            self.log_git_message(f"Error committing changes: {str(e)}")
            self.commit_button.setEnabled(True)
    
    def log_message(self, message: str):
        """Log a message to the main output text area."""
        self.output_text.append(message)
    
    def log_sequence_message(self, message: str):
        """Log a message to the sequence output text area."""
        self.seq_output_text.append(message)
    
    def log_test_message(self, message: str):
        """Log a message to the test results text area."""
        self.test_results_text.append(message)
    
    def log_git_message(self, message: str):
        """Log a message to the Git output text area."""
        self.git_output_text.append(message)
    
    def update_progress(self, value: int):
        """Update the progress bar value."""
        self.progress_bar.setValue(value)
    
    @pyqtSlot(bool, str)
    def execution_finished(self, success: bool, message: str):
        """Handle completion of prompt execution."""
        self.log_message(message)
        self.execute_button.setEnabled(True)
        if success:
            self.log_message("✅ Execution completed successfully")
        else:
            self.log_message(f"❌ Execution failed: {message}")
        self.prompt_executed.emit(success, message, "" if success else message)
    
    @pyqtSlot(bool, str)
    def sequence_finished(self, success: bool, message: str):
        """Handle completion of sequence execution."""
        self.log_sequence_message(message)
        self.run_seq_button.setEnabled(True)
        if success:
            self.log_sequence_message("✅ Sequence completed successfully")
        else:
            self.log_sequence_message(f"❌ Sequence failed: {message}")
        self.sequence_executed.emit(success, message, "" if success else message)
    
    @pyqtSlot(bool, str)
    def tests_generated(self, success: bool, message: str):
        """Handle completion of test generation."""
        self.log_test_message(message)
        self.generate_test_button.setEnabled(True)
        self.run_test_button.setEnabled(True)
        self.tests_generated.emit(success, message, "" if success else message)
    
    @pyqtSlot(bool, str)
    def tests_run(self, success: bool, message: str):
        """Handle completion of test execution."""
        self.log_test_message(message)
        self.generate_test_button.setEnabled(True)
        self.run_test_button.setEnabled(True)
        self.tests_run.emit(success, message, "" if success else message)
    
    @pyqtSlot(bool, str)
    def git_operation_finished(self, success: bool, message: str):
        """Handle completion of Git operations."""
        self.log_git_message(message)
        self.install_hooks_button.setEnabled(True)
        self.commit_button.setEnabled(True)
        self.git_operation_completed.emit(success, message)
    
    def _load_cursor_templates(self):
        """Load templates for Cursor task injection."""
        try:
            templates_dir = Path("templates")
            if not templates_dir.exists():
                templates_dir.mkdir(parents=True, exist_ok=True)
                
            templates = [
                f.name for f in templates_dir.iterdir() 
                if f.is_file() and f.suffix in ['.txt', '.md', '.jinja']
            ]
            
            self.cursor_template_combo.clear()
            self.cursor_template_combo.addItems(templates)
            
            if not templates:
                self.log_message("No templates found in 'templates' directory")
        except Exception as e:
            self.log_message(f"Error loading cursor templates: {e}")
    
    def _browse_cursor_target(self):
        """Browse for target output file."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Select Target Output", "", "All Files (*)"
        )
        if path:
            self.cursor_target_edit.setText(path)
    
    def _create_cursor_task(self):
        """Create a new Cursor queued task."""
        template_name = self.cursor_template_combo.currentText()
        if not template_name:
            self.cursor_result_text.setText("Please select a template")
            return
            
        context_str = self.cursor_context_edit.toPlainText().strip()
        target_output = self.cursor_target_edit.text().strip() or "output.py"
        auto_execute = self.auto_execute_checkbox.isChecked()
        
        try:
            if context_str:
                context = json.loads(context_str)
            else:
                context = {}
                
            self.cursor_result_text.clear()
            self.cursor_result_text.append("Creating Cursor task...")
            
            # Create the task
            task_path = self.prompt_service.execute_prompt(
                template_name, 
                context, 
                target_output,
                auto_execute=auto_execute
            )
            
            self.cursor_result_text.append(f"✅ Task created successfully at: {task_path}")
            if auto_execute:
                self.cursor_result_text.append("⚡ Task is marked for auto-execution by Cursor.")
            else:
                self.cursor_result_text.append("Cursor will process this task when approved.")
            
            # Refresh the task list
            self._refresh_cursor_tasks()
            self._refresh_task_history()
            
            # Emit signal
            self.cursor_task_injected.emit(True, task_path)
            
        except json.JSONDecodeError as e:
            self.cursor_result_text.setText(f"Invalid JSON context: {str(e)}")
            self.cursor_task_injected.emit(False, str(e))
        except Exception as e:
            self.cursor_result_text.setText(f"Error creating task: {str(e)}")
            self.cursor_task_injected.emit(False, str(e))
    
    def _refresh_cursor_tasks(self):
        """Refresh the list of queued Cursor tasks."""
        try:
            tasks = self.prompt_service.get_queued_tasks()
            
            self.task_table.setRowCount(len(tasks))
            for row, task in enumerate(tasks):
                # ID
                id_item = QTableWidgetItem(task["id"][:8] + "...")
                id_item.setData(Qt.UserRole, task["id"])  # Store full ID
                self.task_table.setItem(row, 0, id_item)
                
                # Template
                self.task_table.setItem(row, 1, QTableWidgetItem(task["template_name"]))
                
                # Target
                self.task_table.setItem(row, 2, QTableWidgetItem(task["target_output"]))
                
                # Timestamp
                timestamp = datetime.fromisoformat(task["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                self.task_table.setItem(row, 3, QTableWidgetItem(timestamp))
        except Exception as e:
            self.cursor_result_text.setText(f"Error refreshing task list: {str(e)}")
    
    def _delete_cursor_task(self):
        """Delete the selected task."""
        selected_items = self.task_table.selectedItems()
        if not selected_items:
            self.cursor_result_text.setText("No task selected")
            return
            
        # Get the task ID from the first column
        row = selected_items[0].row()
        task_id = self.task_table.item(row, 0).data(Qt.UserRole)
        
        try:
            if self.prompt_service.delete_task(task_id):
                self.cursor_result_text.setText(f"Task {task_id[:8]}... deleted successfully")
                self._refresh_cursor_tasks()
            else:
                self.cursor_result_text.setText(f"Failed to delete task {task_id[:8]}...")
        except Exception as e:
            self.cursor_result_text.setText(f"Error deleting task: {str(e)}")
    
    def _refresh_task_history(self):
        """Refresh the task history display with filtering."""
        try:
            # Get all tasks
            all_tasks = self.prompt_service.get_all_tasks()
            
            # Apply filters
            filtered_tasks = self._apply_task_filters(all_tasks)
            
            # Update table
            self.history_table.setRowCount(len(filtered_tasks))
            for row, task in enumerate(filtered_tasks):
                # ID
                id_item = QTableWidgetItem(task["id"][:8] + "...")
                id_item.setData(Qt.UserRole, task["id"])  # Store full ID
                self.history_table.setItem(row, 0, id_item)
                
                # Template
                self.history_table.setItem(row, 1, QTableWidgetItem(task.get("template_name", "Unknown")))
                
                # Target
                self.history_table.setItem(row, 2, QTableWidgetItem(task.get("target_output", "Unknown")))
                
                # Status with color
                status = task.get("status", "unknown")
                status_item = QTableWidgetItem(status)
                status_color = {
                    'queued': Qt.blue,
                    'running': Qt.darkYellow,
                    'completed': Qt.darkGreen,
                    'failed': Qt.darkRed
                }.get(status.lower(), Qt.gray)
                status_item.setForeground(status_color)
                status_item.setFont(QFont("", -1, QFont.Bold))
                self.history_table.setItem(row, 3, status_item)
                
                # Timestamp
                timestamp = task.get("completed_at", task.get("timestamp", "Unknown"))
                if timestamp != "Unknown":
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        pass
                self.history_table.setItem(row, 4, QTableWidgetItem(timestamp))
                
                # Actions
                actions_cell = QWidget()
                actions_layout = QHBoxLayout(actions_cell)
                actions_layout.setContentsMargins(2, 2, 2, 2)
                
                view_btn = QPushButton("View")
                view_btn.setProperty("task_id", task["id"])
                view_btn.clicked.connect(self._view_task_details)
                actions_layout.addWidget(view_btn)
                
                delete_btn = QPushButton("Delete")
                delete_btn.setProperty("task_id", task["id"])
                delete_btn.clicked.connect(self._delete_history_task)
                actions_layout.addWidget(delete_btn)
                
                if task.get("status") == "queued":
                    complete_btn = QPushButton("Mark Complete")
                    complete_btn.setProperty("task_id", task["id"])
                    complete_btn.clicked.connect(lambda: self._mark_task_complete(task["id"]))
                    actions_layout.addWidget(complete_btn)
                
                self.history_table.setCellWidget(row, 5, actions_cell)
            
            # Adjust column widths
            self.history_table.resizeColumnsToContents()
            self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            
        except Exception as e:
            logger.error(f"Error refreshing task history: {e}")
    
    def _apply_task_filters(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply filters to the task list."""
        # Status filter
        status_filter = self.status_filter.currentText().lower()
        if status_filter != "all":
            tasks = [t for t in tasks if t.get("status", "").lower() == status_filter]
        
        # Template filter
        template_filter = self.template_filter.currentText()
        if template_filter != "All":
            tasks = [t for t in tasks if t.get("template_name") == template_filter]
        
        # Search filter
        search_text = self.search_edit.text().lower()
        if search_text:
            filtered_tasks = []
            for task in tasks:
                task_id = task.get("id", "").lower()
                template = task.get("template_name", "").lower()
                target = task.get("target_output", "").lower()
                if (search_text in task_id or 
                    search_text in template or 
                    search_text in target):
                    filtered_tasks.append(task)
            tasks = filtered_tasks
        
        return tasks
    
    def _update_template_filter(self):
        """Update the template filter combobox with available templates."""
        try:
            # Get all unique template names
            all_tasks = self.prompt_service.get_all_tasks()
            templates = sorted(set(t.get("template_name", "") for t in all_tasks if t.get("template_name")))
            
            # Save current selection
            current = self.template_filter.currentText()
            
            # Clear and repopulate
            self.template_filter.clear()
            self.template_filter.addItem("All")
            self.template_filter.addItems(templates)
            
            # Restore selection if still available
            index = self.template_filter.findText(current)
            if index >= 0:
                self.template_filter.setCurrentIndex(index)
        except Exception as e:
            logger.error(f"Error updating template filter: {e}")
    
    def _view_task_details(self):
        """View details of the selected task."""
        try:
            # Get the sender button
            sender = self.sender()
            task_id = sender.property("task_id")
            
            # Find the task data
            task_data = None
            all_tasks = self.prompt_service.get_all_tasks()
            for task in all_tasks:
                if task.get("id") == task_id:
                    task_data = task
                    break
            
            if task_data:
                # Show the task details modal
                dialog = TaskDetailsModal(task_data, self)
                dialog.exec_()
            else:
                logger.warning(f"Task not found: {task_id}")
        except Exception as e:
            logger.error(f"Error viewing task details: {e}")
    
    def _delete_history_task(self):
        """Delete a task from history via the action button."""
        try:
            # Get the sender button
            sender = self.sender()
            task_id = sender.property("task_id")
            
            # Delete the task
            if self.prompt_service.delete_task(task_id):
                self._refresh_task_history()
                self._refresh_cursor_tasks()
            else:
                logger.warning(f"Failed to delete task: {task_id}")
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
    
    def _mark_task_complete(self, task_id: str):
        """Mark a task as complete."""
        try:
            if self.prompt_service.mark_task_complete(task_id):
                self._refresh_task_history()
                self._refresh_cursor_tasks()
            else:
                logger.warning(f"Failed to mark task as complete: {task_id}")
        except Exception as e:
            logger.error(f"Error marking task as complete: {e}")

class CursorExecutionWindow(QWidget):
    """Main window wrapper for CursorExecutionTab with proper close event handling."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cursor Execution Interface")
        self.setGeometry(100, 100, 900, 800)
        
        layout = QVBoxLayout(self)
        self.tab = CursorExecutionTab()
        layout.addWidget(self.tab)
        
    def closeEvent(self, event):
        """Handle window close event to ensure proper cleanup."""
        try:
            for attr in ['worker', 'seq_worker', 'test_worker', 'git_worker']:
                worker = getattr(self.tab, attr, None)
                if worker is not None and worker.isRunning():
                    worker.quit()
                    worker.wait()
            if hasattr(self.tab, 'dispatcher'):
                self.tab.dispatcher.shutdown()
            event.accept()
            QApplication.quit()
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
            event.accept()
            QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CursorExecutionWindow()
    window.show()
    sys.exit(app.exec_())
