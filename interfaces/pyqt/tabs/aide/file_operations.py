"""
File Operations Handler for AIDE

This module contains the FileOperationsHandler class that manages file-related
operations including loading, processing, self-healing, and testing.
"""

import sys
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QProgressBar, QPlainTextEdit)
from PyQt5.QtCore import Qt

from interfaces.pyqt.GuiHelpers import GuiHelpers
from core.chatgpt_automation.automation_engine import AutomationEngine

# Define the folder for updated files
UPDATED_FOLDER = Path("updated")
UPDATED_FOLDER.mkdir(exist_ok=True)

class FileOperationsHandler:
    def __init__(self, parent, helpers, engine, dispatcher=None, logger=None, project_scanner=None):
        """
        Initialize the FileOperationsHandler.
        
        Args:
            parent: Parent widget
            helpers: GuiHelpers instance
            engine: AutomationEngine instance
            dispatcher: Signal dispatcher
            logger: Logger instance
            project_scanner: Project scanner service
        """
        self.parent = parent
        self.helpers = helpers
        self.engine = engine
        self.dispatcher = dispatcher
        self.logger = logger
        self.project_scanner = project_scanner
        self.current_file_path = None
        
        # UI Components
        self.file_preview = None
        self.progress_bar = None
        
    def create_preview_widget(self):
        """Create and return the file preview widget."""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        # File preview text area
        self.file_preview = QPlainTextEdit()
        self.file_preview.setPlaceholderText(
            "File preview will appear here.\nDouble-click a file in the browser to load it for editing."
        )
        preview_layout.addWidget(self.file_preview)
        
        # Action buttons layout
        button_layout = QHBoxLayout()
        
        # Add Scan Project button
        scan_project_btn = QPushButton("Scan Project")
        scan_project_btn.clicked.connect(self.on_scan_project)
        button_layout.addWidget(scan_project_btn)
        
        # File processing buttons
        process_button = QPushButton("Process File")
        process_button.clicked.connect(self.process_file)
        button_layout.addWidget(process_button)
        
        self_heal_button = QPushButton("Self-Heal")
        self_heal_button.clicked.connect(self.self_heal)
        button_layout.addWidget(self_heal_button)
        
        run_tests_button = QPushButton("Run Tests")
        run_tests_button.clicked.connect(self.run_tests)
        button_layout.addWidget(run_tests_button)
        
        # Debug buttons
        run_debug_btn = QPushButton("Run Debug")
        run_debug_btn.clicked.connect(self.parent.debug_operations.on_run_debug)
        button_layout.addWidget(run_debug_btn)
        
        apply_fix_btn = QPushButton("Apply Fix")
        apply_fix_btn.clicked.connect(self.parent.debug_operations.on_apply_fix)
        button_layout.addWidget(apply_fix_btn)
        
        rollback_btn = QPushButton("Rollback Fix")
        rollback_btn.clicked.connect(self.parent.debug_operations.on_rollback_fix)
        button_layout.addWidget(rollback_btn)
        
        cursor_exec_btn = QPushButton("Execute via Cursor")
        cursor_exec_btn.clicked.connect(self.parent.debug_operations.on_cursor_execute)
        button_layout.addWidget(cursor_exec_btn)
        
        preview_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        preview_layout.addWidget(self.progress_bar)
        
        return preview_widget
    
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
    
    def append_output(self, message):
        """Pass the message to the parent for output handling."""
        if self.parent:
            self.parent.append_output(message) 
