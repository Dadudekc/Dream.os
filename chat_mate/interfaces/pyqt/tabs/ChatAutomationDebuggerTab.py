#!/usr/bin/env python3
"""
ChatAutomationDebuggerTab.py

A tab that integrates the chat_automations functionality into the Dreamscape interface.
This tab provides file browsing, prompt execution, and other automation features from 
the chatgpt_automation module.
"""

import sys
import random
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
                            QLabel, QSplitter, QTabWidget, QProgressBar, QPlainTextEdit, 
                            QFileDialog)
from PyQt5.QtCore import Qt, pyqtSlot

from chatgpt_automation.views.file_browser_widget import FileBrowserWidget
from chatgpt_automation.GUI.GuiHelpers import GuiHelpers
from chatgpt_automation.automation_engine import AutomationEngine

# Define the folder for updated files
UPDATED_FOLDER = Path("updated")
UPDATED_FOLDER.mkdir(exist_ok=True)


class ChatAutomationDebuggerTab(QWidget):
    def __init__(self, dispatcher=None, logger=None, **services):
        """
        Initializes the ChatAutomationDebuggerTab.
        
        Args:
            dispatcher: Centralized signal dispatcher.
            logger: Logger instance.
            services: Additional services.
        """
        super().__init__()
        self.dispatcher = dispatcher
        self.logger = logger
        self.services = services
        self.current_file_path = None
        
        # Initialize helpers and engine
        self.helpers = GuiHelpers()
        self.engine = AutomationEngine(use_local_llm=False, model_name='mistral')
        
        self._init_ui()
        self._connect_signals()
        self.logger.info("ChatAutomationDebuggerTab initialized")

    def _init_ui(self):
        """
        Set up the user interface.
        """
        self.setMinimumSize(800, 600)
        main_layout = QVBoxLayout(self)
        
        # Title label
        title_label = QLabel("Chat Automation Debugger - File Processing & Prompt Execution")
        main_layout.addWidget(title_label)
        
        # Horizontal splitter for left/right panels
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # LEFT PANEL: File Browser 
        self.file_browser = FileBrowserWidget(helpers=self.helpers)
        main_splitter.addWidget(self.file_browser)
        main_splitter.setStretchFactor(0, 1)
        
        # RIGHT PANEL: QTabWidget with "Preview" and "Prompt" tabs
        right_tab = QTabWidget()
        
        # --- Tab 1: Preview with Action Buttons ---
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        self.file_preview = QPlainTextEdit()
        self.file_preview.setPlaceholderText(
            "File preview will appear here.\nDouble-click a file in the browser to load it for editing."
        )
        preview_layout.addWidget(self.file_preview)
        
        button_layout = QHBoxLayout()
        self.process_button = QPushButton("Process File")
        self.process_button.clicked.connect(self.process_file)
        button_layout.addWidget(self.process_button)
        
        self.self_heal_button = QPushButton("Self-Heal")
        self.self_heal_button.clicked.connect(self.self_heal)
        button_layout.addWidget(self.self_heal_button)
        
        self.run_tests_button = QPushButton("Run Tests")
        self.run_tests_button.clicked.connect(self.run_tests)
        button_layout.addWidget(self.run_tests_button)
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
        Connect signals between components
        """
        # If the dispatcher has relevant signals, connect them here
        if self.dispatcher and hasattr(self.dispatcher, "automation_result"):
            self.dispatcher.automation_result.connect(self.on_automation_result)

    def load_file_into_preview(self, file_path):
        """
        Load a file into the preview pane
        
        Args:
            file_path: Path to the file to load
        """
        content = self.helpers.read_file(file_path)
        if content:
            self.file_preview.setPlainText(content)
            self.current_file_path = file_path
            self.append_output(f"Loaded: {file_path}")
        else:
            self.helpers.show_error("Could not load file.", "Error")

    def process_file(self):
        """
        Process the current file using the automation engine
        """
        if not hasattr(self, "current_file_path") or not self.current_file_path:
            self.helpers.show_warning("No file loaded.", "Warning")
            return
        
        prompt_text = "Update this file and show me the complete updated version."
        file_content = self.file_preview.toPlainText()
        combined_prompt = f"{prompt_text}\n\n---\n\n{file_content}"
        self.append_output("Processing file...")
        
        response = self.engine.get_chatgpt_response(combined_prompt)
        if response:
            # Save to the updated folder, preserving the original filename.
            updated_file = UPDATED_FOLDER / Path(self.current_file_path).name
            saved = self.helpers.save_file(str(updated_file), response)
            if saved:
                self.append_output(f"✅ Updated file saved: {updated_file}")
            else:
                self.append_output(f"❌ Failed to save: {updated_file}")
        else:
            self.append_output("❌ No response from ChatGPT.")

    def self_heal(self):
        """
        Run self-healing on the current file
        """
        if not hasattr(self, "current_file_path") or not self.current_file_path:
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
        """
        Run tests on the current file
        """
        if not hasattr(self, "current_file_path") or not self.current_file_path:
            self.helpers.show_warning("No file loaded.", "Warning")
            return
        
        self.append_output("Running tests...")
        results = self.engine.run_tests(self.current_file_path)
        self.append_output("Test run complete.")

    def send_prompt(self):
        """
        Send a prompt to ChatGPT
        """
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
        """
        Process multiple files with the same prompt
        """
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

    @pyqtSlot(str)
    def on_automation_result(self, result):
        """
        Handle automation result from the dispatcher
        
        Args:
            result: Result message
        """
        self.append_output(result)

    def append_output(self, message: str):
        """
        Append a message to the output and log it
        
        Args:
            message: Message to append
        """
        # Log message to the central log system via dispatcher if available
        if self.dispatcher and hasattr(self.dispatcher, "emit_append_output"):
            self.dispatcher.emit_append_output(message)
        
        # Also show in the prompt response area for immediate feedback
        current_text = self.prompt_response.toPlainText()
        if current_text:
            self.prompt_response.setPlainText(f"{current_text}\n{message}")
        else:
            self.prompt_response.setPlainText(message)
            
        # Log using the logger if available
        if self.logger:
            self.logger.info(f"[ChatAutomation] {message}") 