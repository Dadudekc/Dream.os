"""
Prompt Operations Handler for AIDE

This module contains the PromptOperationsHandler class that manages prompt-related
operations including sending prompts and batch processing.
"""

from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QPlainTextEdit

from interfaces.pyqt.GuiHelpers import GuiHelpers
from core.chatgpt_automation.automation_engine import AutomationEngine

# Define the folder for updated files
UPDATED_FOLDER = Path("updated")
UPDATED_FOLDER.mkdir(exist_ok=True)

class PromptOperationsHandler:
    def __init__(self, parent, helpers, engine, dispatcher=None, logger=None):
        """
        Initialize the PromptOperationsHandler.
        
        Args:
            parent: Parent widget
            helpers: GuiHelpers instance
            engine: AutomationEngine instance
            dispatcher: Signal dispatcher
            logger: Logger instance
        """
        self.parent = parent
        self.helpers = helpers
        self.engine = engine
        self.dispatcher = dispatcher
        self.logger = logger
        
        # UI Components
        self.prompt_input = None
        self.prompt_response = None
        
    def create_prompt_widget(self):
        """Create and return the prompt widget."""
        prompt_widget = QWidget()
        prompt_layout = QVBoxLayout(prompt_widget)
        
        # Prompt input area
        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setPlaceholderText("Enter your prompt here...")
        prompt_layout.addWidget(self.prompt_input)
        
        # Send button
        send_button = QPushButton("Send Prompt to ChatGPT")
        send_button.clicked.connect(self.send_prompt)
        prompt_layout.addWidget(send_button)
        
        # Batch button
        batch_button = QPushButton("Process Batch with Prompt")
        batch_button.clicked.connect(self.process_batch_files)
        prompt_layout.addWidget(batch_button)
        
        # Response area
        self.prompt_response = QPlainTextEdit()
        self.prompt_response.setReadOnly(True)
        self.prompt_response.setPlaceholderText("Response will appear here...")
        prompt_layout.addWidget(self.prompt_response)
        
        return prompt_widget
        
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
            
            # Update progress bar if available
            if hasattr(self.parent, 'file_operations') and hasattr(self.parent.file_operations, 'progress_bar'):
                self.parent.file_operations.progress_bar.setValue(progress_percent)
            
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
        
    def append_output(self, message):
        """Append a message to the output area."""
        current_text = self.prompt_response.toPlainText()
        if current_text:
            self.prompt_response.setPlainText(f"{current_text}\n{message}")
        else:
            self.prompt_response.setPlainText(message)
            
        # Log the message if logger is available
        if self.logger:
            self.logger.info(f"[AIDE:Prompt] {message}") 
