#!/usr/bin/env python3
"""
CursorExecutionTab.py

PyQt5 tab interface for the CursorDispatcher system, providing GUI access to:
- Template/prompt selection and execution
- Test running and result visualization
- Sequence selection and execution
- Git operations for code versioning
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QComboBox, QTextEdit, QTabWidget, QGroupBox, QCheckBox,
    QFileDialog, QSplitter, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon

# Import the CursorDispatcher
from cursor_dispatcher import CursorDispatcher, logger

# Setup logging
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
    - Selecting and rendering templates
    - Running prompts in Cursor
    - Executing test cycles
    - Managing multi-prompt sequences
    - Committing changes to Git
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize the CursorDispatcher
        self.dispatcher = CursorDispatcher()
        
        # Setup UI
        self.init_ui()
        
        # Load available templates and sequences
        self.load_templates()
        self.load_sequences()
        
    def init_ui(self):
        """Initialize the user interface components."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Create tabbed interface for different operations
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Tab 1: Execute Single Prompt
        prompt_tab = QWidget()
        prompt_layout = QVBoxLayout(prompt_tab)
        
        # Template selection
        template_group = QGroupBox("Template Selection")
        template_layout = QVBoxLayout(template_group)
        
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(300)
        template_layout.addWidget(QLabel("Select Template:"))
        template_layout.addWidget(self.template_combo)
        
        # Context input
        context_group = QGroupBox("Context Variables")
        context_layout = QVBoxLayout(context_group)
        
        self.context_edit = QTextEdit()
        self.context_edit.setPlaceholderText('{"STRATEGY_DESCRIPTION": "Create a modular PyQt5 tab..."}')
        context_layout.addWidget(QLabel("Context JSON:"))
        context_layout.addWidget(self.context_edit)
        
        # Initial code
        code_group = QGroupBox("Initial Code")
        code_layout = QVBoxLayout(code_group)
        
        self.code_edit = QTextEdit()
        self.code_edit.setPlaceholderText("# Initial code to send to Cursor")
        code_layout.addWidget(QLabel("Starting Code:"))
        code_layout.addWidget(self.code_edit)
        
        # Control buttons
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
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # Output area
        output_group = QGroupBox("Execution Output")
        output_layout = QVBoxLayout(output_group)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        
        # Add components to prompt tab
        prompt_layout.addWidget(template_group)
        prompt_layout.addWidget(context_group)
        prompt_layout.addWidget(code_group)
        prompt_layout.addLayout(control_layout)
        prompt_layout.addWidget(self.progress_bar)
        prompt_layout.addWidget(output_group)
        
        # Tab 2: Execute Sequence
        sequence_tab = QWidget()
        sequence_layout = QVBoxLayout(sequence_tab)
        
        # Sequence selection
        seq_selection_group = QGroupBox("Sequence Selection")
        seq_selection_layout = QVBoxLayout(seq_selection_group)
        
        self.sequence_combo = QComboBox()
        seq_selection_layout.addWidget(QLabel("Select Sequence:"))
        seq_selection_layout.addWidget(self.sequence_combo)
        
        # Sequence info
        seq_info_group = QGroupBox("Sequence Information")
        seq_info_layout = QVBoxLayout(seq_info_group)
        
        self.seq_info_text = QTextEdit()
        self.seq_info_text.setReadOnly(True)
        seq_info_layout.addWidget(self.seq_info_text)
        
        # Sequence control
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
        
        # Sequence steps table
        self.seq_steps_table = QTableWidget(0, 3)
        self.seq_steps_table.setHorizontalHeaderLabels(["Step", "Template", "Output File"])
        self.seq_steps_table.horizontalHeader().setStretchLastSection(True)
        
        # Sequence output
        seq_output_group = QGroupBox("Sequence Output")
        seq_output_layout = QVBoxLayout(seq_output_group)
        
        self.seq_output_text = QTextEdit()
        self.seq_output_text.setReadOnly(True)
        seq_output_layout.addWidget(self.seq_output_text)
        
        # Add components to sequence tab
        sequence_layout.addWidget(seq_selection_group)
        sequence_layout.addWidget(seq_info_group)
        sequence_layout.addLayout(seq_control_layout)
        sequence_layout.addWidget(self.seq_steps_table)
        sequence_layout.addWidget(seq_output_group)
        
        # Tab 3: Test Management
        test_tab = QWidget()
        test_layout = QVBoxLayout(test_tab)
        
        # Test file selection
        test_file_group = QGroupBox("Test File Selection")
        test_file_layout = QHBoxLayout(test_file_group)
        
        self.test_file_edit = QLineEdit()
        test_file_layout.addWidget(QLabel("File to Test:"))
        test_file_layout.addWidget(self.test_file_edit)
        
        self.browse_test_button = QPushButton("Browse")
        self.browse_test_button.clicked.connect(self.browse_test_file)
        test_file_layout.addWidget(self.browse_test_button)
        
        # Test controls
        test_control_layout = QHBoxLayout()
        
        self.generate_test_button = QPushButton("Generate Tests")
        self.generate_test_button.clicked.connect(self.generate_tests)
        test_control_layout.addWidget(self.generate_test_button)
        
        self.run_test_button = QPushButton("Run Tests")
        self.run_test_button.clicked.connect(self.run_tests)
        test_control_layout.addWidget(self.run_test_button)
        
        # Test results
        test_results_group = QGroupBox("Test Results")
        test_results_layout = QVBoxLayout(test_results_group)
        
        self.test_results_text = QTextEdit()
        self.test_results_text.setReadOnly(True)
        test_results_layout.addWidget(self.test_results_text)
        
        # Add components to test tab
        test_layout.addWidget(test_file_group)
        test_layout.addLayout(test_control_layout)
        test_layout.addWidget(test_results_group)
        
        # Tab 4: Git Integration
        git_tab = QWidget()
        git_layout = QVBoxLayout(git_tab)
        
        # Git controls
        git_controls_group = QGroupBox("Git Operations")
        git_controls_layout = QVBoxLayout(git_controls_group)
        
        self.commit_message_edit = QLineEdit()
        self.commit_message_edit.setPlaceholderText("Commit message")
        git_controls_layout.addWidget(QLabel("Commit Message:"))
        git_controls_layout.addWidget(self.commit_message_edit)
        
        git_buttons_layout = QHBoxLayout()
        
        self.install_hooks_button = QPushButton("Install Git Hooks")
        self.install_hooks_button.clicked.connect(self.install_git_hooks)
        git_buttons_layout.addWidget(self.install_hooks_button)
        
        self.commit_button = QPushButton("Commit Changes")
        self.commit_button.clicked.connect(self.commit_changes)
        git_buttons_layout.addWidget(self.commit_button)
        
        git_controls_layout.addLayout(git_buttons_layout)
        
        # Files to commit
        git_files_group = QGroupBox("Files to Commit")
        git_files_layout = QVBoxLayout(git_files_group)
        
        self.git_files_edit = QTextEdit()
        self.git_files_edit.setPlaceholderText("One file path per line")
        git_files_layout.addWidget(self.git_files_edit)
        
        # Git output
        git_output_group = QGroupBox("Git Output")
        git_output_layout = QVBoxLayout(git_output_group)
        
        self.git_output_text = QTextEdit()
        self.git_output_text.setReadOnly(True)
        git_output_layout.addWidget(self.git_output_text)
        
        # Add components to git tab
        git_layout.addWidget(git_controls_group)
        git_layout.addWidget(git_files_group)
        git_layout.addWidget(git_output_group)
        
        # Add tabs to main tab widget
        tabs.addTab(prompt_tab, "Execute Prompt")
        tabs.addTab(sequence_tab, "Run Sequence")
        tabs.addTab(test_tab, "Test Management")
        tabs.addTab(git_tab, "Git Integration")
        
    def load_templates(self):
        """Load available templates into the UI."""
        try:
            # Clear existing items
            self.template_combo.clear()
            
            # Get templates from the dispatcher's template directory
            templates_path = self.dispatcher.templates_path
            
            # Find all .j2 files
            template_files = list(templates_path.glob("*.j2"))
            
            # Add to dropdown
            for template_file in template_files:
                self.template_combo.addItem(template_file.name)
                
            self.log_message(f"Loaded {len(template_files)} templates from {templates_path}")
        except Exception as e:
            self.log_message(f"Error loading templates: {str(e)}")
    
    def load_sequences(self):
        """Load available sequences into the UI."""
        try:
            # Clear existing items
            self.sequence_combo.clear()
            
            # Get sequences from the dispatcher's sequences directory
            sequences_path = self.dispatcher.templates_path.parent / "sequences"
            
            if not sequences_path.exists():
                self.log_message(f"Sequences directory not found: {sequences_path}")
                return
                
            # Find all .json files
            sequence_files = list(sequences_path.glob("*.json"))
            
            # Add to dropdown
            for sequence_file in sequence_files:
                self.sequence_combo.addItem(sequence_file.stem)
                
            self.log_message(f"Loaded {len(sequence_files)} sequences from {sequences_path}")
        except Exception as e:
            self.log_message(f"Error loading sequences: {str(e)}")
    
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
                
            # Load sequence data
            with open(sequence_path, 'r') as f:
                sequence_data = json.load(f)
                
            # Display sequence info
            info_text = f"Name: {sequence_data.get('name', sequence_name)}\n"
            info_text += f"Description: {sequence_data.get('description', 'No description')}\n"
            info_text += f"Steps: {len(sequence_data.get('steps', []))}\n"
            
            self.seq_info_text.setText(info_text)
            
            # Populate steps table
            steps = sequence_data.get("steps", [])
            self.seq_steps_table.setRowCount(len(steps))
            
            for i, step in enumerate(steps):
                self.seq_steps_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
                self.seq_steps_table.setItem(i, 1, QTableWidgetItem(step.get("template", "")))
                self.seq_steps_table.setItem(i, 2, QTableWidgetItem(step.get("output_file", f"step_{i+1}")))
                
            self.log_message(f"Loaded sequence: {sequence_name}")
        except Exception as e:
            self.log_message(f"Error loading sequence info: {str(e)}")
    
    def execute_prompt(self):
        """Execute a single prompt with the CursorDispatcher."""
        try:
            # Get selected template
            template_name = self.template_combo.currentText()
            if not template_name:
                self.log_message("No template selected")
                return
                
            # Parse context JSON
            context_text = self.context_edit.toPlainText()
            if context_text:
                try:
                    context = json.loads(context_text)
                except json.JSONDecodeError:
                    self.log_message("Invalid JSON in context field")
                    return
            else:
                context = {}
                
            # Get initial code
            initial_code = self.code_edit.toPlainText()
            if not initial_code:
                initial_code = "# Code will be generated by Cursor"
                
            # Get options
            skip_wait = self.auto_checkbox.isChecked()
            run_tests = self.run_tests_checkbox.isChecked()
            git_commit = self.git_commit_checkbox.isChecked()
            
            # Log execution start
            self.log_message(f"Executing prompt: {template_name}")
            self.progress_bar.setValue(10)
            
            # Start worker thread for rendering template
            def execute_task():
                # Step 1: Render template
                self.update_progress(20)
                self.log_message("Rendering template...")
                prompt_text = self.dispatcher.run_prompt(template_name, context)
                
                # Step 2: Send to Cursor and wait for edit
                self.update_progress(40)
                self.log_message("Sending to Cursor...")
                code_result = self.dispatcher.send_and_wait(initial_code, prompt_text, skip_wait=skip_wait)
                
                # Step 3: Run tests if enabled
                if run_tests:
                    self.update_progress(60)
                    self.log_message("Running tests...")
                    code_file = self.dispatcher.output_path / "generated_tab.py"
                    test_success, test_output = self.dispatcher.run_tests(str(code_file))
                    self.log_message(f"Test result: {'PASSED' if test_success else 'FAILED'}")
                    if not test_success:
                        self.log_message(f"Test failures: {test_output}")
                
                # Step 4: Commit changes if enabled
                if git_commit:
                    self.update_progress(80)
                    self.log_message("Committing changes...")
                    commit_context = {"CODE_DIFF_OR_FINAL": code_result}
                    commit_message = self.dispatcher.run_prompt("05_commit_and_version.j2", commit_context)
                    commit_message = commit_message.split("\n")[0]  # Get first line
                    
                    files_to_commit = [str(self.dispatcher.output_path / "*.py")]
                    success = self.dispatcher.git_commit_changes(commit_message, files_to_commit)
                    if success:
                        self.log_message(f"Successfully committed: {commit_message}")
                    else:
                        self.log_message("Failed to commit changes")
                
                self.update_progress(100)
                return "Execution completed successfully"
            
            # Create and start worker thread
            self.worker = WorkerThread(execute_task)
            self.worker.update_signal.connect(self.log_message)
            self.worker.progress_signal.connect(self.update_progress)
            self.worker.finished_signal.connect(self.execution_finished)
            self.worker.start()
            
            # Disable execute button while running
            self.execute_button.setEnabled(False)
            
        except Exception as e:
            self.log_message(f"Error executing prompt: {str(e)}")
            self.progress_bar.setValue(0)
            self.execute_button.setEnabled(True)
    
    def run_sequence(self):
        """Run a prompt sequence with the CursorDispatcher."""
        try:
            # Get selected sequence
            sequence_name = self.sequence_combo.currentText()
            if not sequence_name:
                self.log_message("No sequence selected")
                return
                
            # Get options
            skip_wait = self.seq_auto_checkbox.isChecked()
            
            # Log sequence start
            self.log_message(f"Starting sequence: {sequence_name}")
            self.seq_output_text.clear()
            
            # Define execution task for worker thread
            def execute_sequence_task():
                initial_context = {
                    "STRATEGY_DESCRIPTION": "Create a modular PyQt5 tab for UX testing and live preview of widgets."
                }
                
                try:
                    self.log_message(f"Executing sequence {sequence_name}...")
                    final_code = self.dispatcher.execute_prompt_sequence(sequence_name, initial_context, skip_wait=skip_wait)
                    self.log_message("Sequence execution completed successfully")
                    return final_code
                except Exception as e:
                    self.log_message(f"Error during sequence execution: {str(e)}")
                    raise
            
            # Create and start worker thread
            self.seq_worker = WorkerThread(execute_sequence_task)
            self.seq_worker.update_signal.connect(self.log_sequence_message)
            self.seq_worker.finished_signal.connect(self.sequence_finished)
            self.seq_worker.start()
            
            # Disable run button while sequence is running
            self.run_seq_button.setEnabled(False)
            
        except Exception as e:
            self.log_sequence_message(f"Error running sequence: {str(e)}")
            self.run_seq_button.setEnabled(True)
    
    def browse_test_file(self):
        """Open file dialog to select a file to test."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File to Test", 
            str(self.dispatcher.output_path), 
            "Python Files (*.py)"
        )
        
        if file_path:
            self.test_file_edit.setText(file_path)
    
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
            
            # Define task for worker thread
            def generate_tests_task():
                self.dispatcher._create_test_file(file_path, str(test_file_path))
                return f"Tests generated successfully: {test_file_path}"
            
            # Create and start worker thread
            self.test_worker = WorkerThread(generate_tests_task)
            self.test_worker.update_signal.connect(self.log_test_message)
            self.test_worker.finished_signal.connect(self.tests_generated)
            self.test_worker.start()
            
            # Disable buttons while generating
            self.generate_test_button.setEnabled(False)
            self.run_test_button.setEnabled(False)
            
        except Exception as e:
            self.log_test_message(f"Error generating tests: {str(e)}")
            self.generate_test_button.setEnabled(True)
            self.run_test_button.setEnabled(True)
    
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
            
            # Define task for worker thread
            def run_tests_task():
                success, output = self.dispatcher.run_tests(file_path)
                if success:
                    self.log_test_message("✅ Tests PASSED")
                else:
                    self.log_test_message("❌ Tests FAILED")
                self.log_test_message(output)
                return f"Test execution completed with result: {'PASSED' if success else 'FAILED'}"
            
            # Create and start worker thread
            self.test_worker = WorkerThread(run_tests_task)
            self.test_worker.update_signal.connect(self.log_test_message)
            self.test_worker.finished_signal.connect(self.tests_run)
            self.test_worker.start()
            
            # Disable buttons while running
            self.generate_test_button.setEnabled(False)
            self.run_test_button.setEnabled(False)
            
        except Exception as e:
            self.log_test_message(f"Error running tests: {str(e)}")
            self.generate_test_button.setEnabled(True)
            self.run_test_button.setEnabled(True)
    
    def install_git_hooks(self):
        """Install Git hooks using the dispatcher."""
        try:
            self.log_git_message("Installing Git hooks...")
            
            # Define task for worker thread
            def install_hooks_task():
                success = self.dispatcher.install_git_hook("post-commit")
                return f"Git hooks installation: {'Successful' if success else 'Failed'}"
            
            # Create and start worker thread
            self.git_worker = WorkerThread(install_hooks_task)
            self.git_worker.update_signal.connect(self.log_git_message)
            self.git_worker.finished_signal.connect(self.git_operation_finished)
            self.git_worker.start()
            
            # Disable button while installing
            self.install_hooks_button.setEnabled(False)
            
        except Exception as e:
            self.log_git_message(f"Error installing Git hooks: {str(e)}")
            self.install_hooks_button.setEnabled(True)
    
    def commit_changes(self):
        """Commit changes to Git using the dispatcher."""
        try:
            # Get commit message
            commit_message = self.commit_message_edit.text()
            if not commit_message:
                self.log_git_message("No commit message provided")
                return
                
            # Get files to commit
            files_text = self.git_files_edit.toPlainText()
            if not files_text:
                self.log_git_message("No files specified for commit")
                return
                
            files_to_commit = [line.strip() for line in files_text.split("\n") if line.strip()]
            
            self.log_git_message(f"Committing {len(files_to_commit)} files with message: {commit_message}")
            
            # Define task for worker thread
            def commit_task():
                success = self.dispatcher.git_commit_changes(commit_message, files_to_commit)
                return f"Git commit: {'Successful' if success else 'Failed'}"
            
            # Create and start worker thread
            self.git_worker = WorkerThread(commit_task)
            self.git_worker.update_signal.connect(self.log_git_message)
            self.git_worker.finished_signal.connect(self.git_operation_finished)
            self.git_worker.start()
            
            # Disable button while committing
            self.commit_button.setEnabled(False)
            
        except Exception as e:
            self.log_git_message(f"Error committing changes: {str(e)}")
            self.commit_button.setEnabled(True)
    
    def log_message(self, message):
        """Log a message to the output text area."""
        self.output_text.append(message)
    
    def log_sequence_message(self, message):
        """Log a message to the sequence output text area."""
        self.seq_output_text.append(message)
    
    def log_test_message(self, message):
        """Log a message to the test results text area."""
        self.test_results_text.append(message)
    
    def log_git_message(self, message):
        """Log a message to the git output text area."""
        self.git_output_text.append(message)
    
    def update_progress(self, value):
        """Update the progress bar value."""
        self.progress_bar.setValue(value)
    
    def execution_finished(self, success, message):
        """Handle completion of prompt execution."""
        self.log_message(message)
        self.execute_button.setEnabled(True)
        if success:
            self.log_message("✅ Execution completed successfully")
        else:
            self.log_message(f"❌ Execution failed: {message}")
    
    def sequence_finished(self, success, message):
        """Handle completion of sequence execution."""
        self.log_sequence_message(message)
        self.run_seq_button.setEnabled(True)
        if success:
            self.log_sequence_message("✅ Sequence completed successfully")
        else:
            self.log_sequence_message(f"❌ Sequence failed: {message}")
    
    def tests_generated(self, success, message):
        """Handle completion of test generation."""
        self.log_test_message(message)
        self.generate_test_button.setEnabled(True)
        self.run_test_button.setEnabled(True)
    
    def tests_run(self, success, message):
        """Handle completion of test execution."""
        self.log_test_message(message)
        self.generate_test_button.setEnabled(True)
        self.run_test_button.setEnabled(True)
    
    def git_operation_finished(self, success, message):
        """Handle completion of a Git operation."""
        self.log_git_message(message)
        self.install_hooks_button.setEnabled(True)
        self.commit_button.setEnabled(True)

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
            # Stop all worker threads
            worker_attributes = ['worker', 'seq_worker', 'test_worker', 'git_worker']
            for attr in worker_attributes:
                if hasattr(self.tab, attr):
                    worker = getattr(self.tab, attr)
                    if worker is not None and worker.isRunning():
                        worker.quit()
                        worker.wait()
            
            # Clean up dispatcher resources
            if hasattr(self.tab, 'dispatcher'):
                self.tab.dispatcher.shutdown()
                
            # Ensure application quits completely
            event.accept()
            QApplication.quit()
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
            event.accept()
            QApplication.quit()

# Main execution
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = CursorExecutionWindow()
    window.show()
    
    sys.exit(app.exec_()) 