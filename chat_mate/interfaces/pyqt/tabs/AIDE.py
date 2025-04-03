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
- Project scanning functionality (new)
"""

import sys
import random
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
                             QLabel, QSplitter, QTabWidget, QProgressBar, QPlainTextEdit, 
                             QFileDialog)
from PyQt5.QtCore import Qt, pyqtSlot

from interfaces.pyqt.widgets.file_browser_widget import FileBrowserWidget
from interfaces.pyqt.GuiHelpers import GuiHelpers
from core.chatgpt_automation.automation_engine import AutomationEngine

# Define the folder for updated files
UPDATED_FOLDER = Path("updated")
UPDATED_FOLDER.mkdir(exist_ok=True)


class AIDE(QWidget):
    def __init__(self, dispatcher=None, logger=None, engine=None, **services):
        """
        Initializes the AIDE (AI Development Environment).
        
        Args:
            dispatcher: Centralized signal dispatcher.
            logger: Logger instance.
            engine: Injected AutomationEngine instance.
            services: Additional services including debug_service, fix_service, rollback_service, 
                      cursor_manager, project_scanner.
        """
        super().__init__()
        self.dispatcher = dispatcher
        self.logger = logger
        self.services = services
        self.current_file_path = None
        
        # Initialize helpers and use injected engine
        self.helpers = GuiHelpers()
        self.engine = engine
        
        if not self.engine:
            if self.logger:
                self.logger.warning("AIDE initialized without an AutomationEngine instance!")
            else:
                print("AIDE initialized without an AutomationEngine instance!")

        # Get debug-related services
        self.debug_service = services.get("debug_service")
        self.fix_service = services.get("fix_service")
        self.rollback_service = services.get("rollback_service")
        self.cursor_manager = services.get("cursor_manager")
        self.project_scanner = services.get("project_scanner")
        
        self._init_ui()
        self._connect_signals()
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
        
        main_splitter.addWidget(right_tab)
        main_splitter.setStretchFactor(1, 3)
        
        self.file_browser.fileDoubleClicked.connect(self.load_file_into_preview)

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
        """Execute a prompt via the Cursor integration."""
        self.append_output("Executing debug prompt via Cursor...")
        if self.cursor_manager:
            try:
                prompt = "## DEBUG PROMPT\nPlease analyze the current error state and generate a suggested fix."
                generated_code = self.cursor_manager.execute_prompt(prompt)
                if generated_code:
                    self.append_output("Cursor generated code:")
                    self.append_output(generated_code)
                    if self.dispatcher:
                        self.dispatcher.emit_cursor_code_generated(generated_code)
                else:
                    self.append_output("Cursor did not generate any code.")
            except Exception as e:
                error_msg = f"Error executing prompt via Cursor: {e}"
                self.append_output(error_msg)
                if self.dispatcher:
                    self.dispatcher.emit_cursor_error(str(e))
        else:
            self.append_output("Cursor manager not available. Ensure it is added as a service.")

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
