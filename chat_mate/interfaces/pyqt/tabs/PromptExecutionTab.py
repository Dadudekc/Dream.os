#!/usr/bin/env python3
"""
AIDE_tabs.py

This file defines two key PyQt5 tabs used in the AI Development Environment (AIDE):
    
1. PromptExecutionTab: 
   - Provides a unified interface for selecting, editing, and executing prompts.
   - Supports both online (remote API) and offline (local LLM) modes.
   - Includes asynchronous loading and execution with status tracking via signals.

2. FullSyncTab:
   - Provides a dedicated interface to run and monitor a full synchronization process.
   - Displays status, progress, and log messages for long-running sync tasks.
   - Emits a signal with a summary result upon sync completion.

Both tabs are designed to plug into the larger Dream.OS ecosystem, support dependency injection,
and are built with FULL SYNC (object-oriented, scalable, and modular) in mind.
"""

import os
import re
import json
import logging
import asyncio
import ast
import subprocess
from pathlib import Path
from typing import Dict, List

# PyQt5 imports (consolidated)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QPlainTextEdit, 
    QLabel, QSplitter, QTabWidget, QProgressBar, QComboBox, QCheckBox, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from qasync import asyncSlot  # For async slots if needed

# Core services / configurations (adjust paths as necessary)
from core.PromptCycleOrchestrator import PromptCycleOrchestrator
from core.AletheiaPromptManager import AletheiaPromptManager
from core.PromptResponseHandler import PromptResponseHandler
from core.services.discord.DiscordQueueProcessor import DiscordQueueProcessor
from config.ConfigManager import ConfigManager

# Example local LLM wrapper using HuggingFace Transformers
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# =============================================================================
# Local LLM Wrapper (for Offline Mode)
# =============================================================================
class LocalLLMWrapper:
    """
    Example local LLM wrapper for demonstration purposes.
    Replace the model name or adapt for other frameworks as needed.
    """
    def __init__(self, model_name="EleutherAI/gpt-neo-1.3B"):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.model.eval()
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(device)
        logging.getLogger(__name__).info(f"LocalLLMWrapper loaded {model_name} on {device}")

    def generate(self, prompt, max_new_tokens=64):
        """Synchronous local inference."""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

# =============================================================================
# PromptExecutionTab: Handles prompt selection, editing, and execution.
# =============================================================================
class PromptExecutionTab(QWidget):
    """
    Tab for executing prompts through various services.
    Provides a unified interface for prompt selection, editing, and execution.
    Supports both online and offline (local LLM) modes.
    """
    prompt_loaded = pyqtSignal(str)
    execution_started = pyqtSignal()
    execution_finished = pyqtSignal(str)
    execution_error = pyqtSignal(str)

    def __init__(self, dispatcher=None, parent=None, config=None, logger=None, prompt_manager=None):
        super().__init__(parent)
        self.dispatcher = dispatcher
        self.config = config or ConfigManager()
        self.logger = logger or logging.getLogger("PromptExecutionTab")
        self.prompt_manager = prompt_manager
        self.current_file_path = None  # Track current file if needed

        # Initialize internal services
        self.prompt_orchestrator = PromptCycleOrchestrator(
            config_manager=self.config,
            chat_manager=getattr(self, "chat_manager", None)  # Should be injected appropriately
        )
        self.template_manager = AletheiaPromptManager()
        self.response_handler = PromptResponseHandler(self.config, self.logger)
        self.discord_processor = DiscordQueueProcessor(self.config, self.logger)
        self.local_llm = None  # Lazy-loaded local LLM wrapper for offline mode
        self.running_tasks = {}

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize UI components for prompt execution."""
        layout = QVBoxLayout()

        # Prompt selector
        layout.addWidget(QLabel("Select Prompt:"))
        self.prompt_selector = QComboBox()
        prompts = self.prompt_orchestrator.list_prompts() if hasattr(self.prompt_orchestrator, 'list_prompts') else []
        self.prompt_selector.addItems(prompts)
        layout.addWidget(self.prompt_selector)

        # Offline mode checkbox
        self.offline_mode_checkbox = QCheckBox("Offline Mode (Local LLM)")
        self.offline_mode_checkbox.setToolTip("Use a local model instead of remote API calls.")
        layout.addWidget(self.offline_mode_checkbox)

        # Prompt editor
        layout.addWidget(QLabel("Edit Prompt:"))
        self.prompt_editor = QTextEdit()
        layout.addWidget(self.prompt_editor)

        # Execute button
        self.execute_btn = QPushButton("Execute")
        layout.addWidget(self.execute_btn)

        # Output display
        layout.addWidget(QLabel("Output:"))
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(self.output_display)

        self.setLayout(layout)

    def _connect_signals(self):
        """Connect signals and slots for prompt execution."""
        self.prompt_selector.currentTextChanged.connect(self.load_prompt)
        self.execute_btn.clicked.connect(self.execute_prompt)
        self.prompt_loaded.connect(self.on_prompt_loaded)
        self.execution_started.connect(lambda: self.log_output("🚀 Executing prompt..."))
        self.execution_finished.connect(lambda msg: self.log_output(f"✅ {msg}"))
        self.execution_error.connect(lambda err: self.log_output(f"❌ {err}"))

    def log_output(self, message: str):
        """Log message to the UI and logger."""
        self.output_display.append(message)
        self.logger.info(message)
        if self.dispatcher and hasattr(self.dispatcher, "emit_log_output"):
            self.dispatcher.emit_log_output(message)

    def ensure_local_llm_loaded(self):
        """Lazy-load the local LLM wrapper."""
        if self.local_llm is None:
            self.local_llm = LocalLLMWrapper(model_name="EleutherAI/gpt-neo-1.3B")
            self.log_output("Loaded local LLM model.")

    @asyncSlot(str)
    async def load_prompt(self, prompt_name):
        """Asynchronously load the selected prompt into the editor."""
        try:
            task_id = f"load_prompt_{prompt_name}"
            if self.dispatcher:
                self.dispatcher.emit_task_started(task_id)
            task = asyncio.create_task(self._load_prompt_async(task_id, prompt_name))
            self.running_tasks[task_id] = task
            task.add_done_callback(lambda t: self._on_task_done(task_id, t))
        except Exception as e:
            self.execution_error.emit(f"Error starting prompt load: {str(e)}")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(f"load_prompt_{prompt_name}", str(e))

    async def _load_prompt_async(self, task_id, prompt_name):
        """Internal asynchronous prompt load task."""
        try:
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 25, "Loading prompt template")
            await asyncio.sleep(0.5)
            if not hasattr(self.prompt_orchestrator, 'get_prompt'):
                raise ValueError("Prompt orchestrator unavailable.")
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 75, "Processing template")
            prompt_text = self.prompt_orchestrator.get_prompt(prompt_name)
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 100, "Template loaded")
            self.prompt_loaded.emit(prompt_text)
            return {'prompt_name': prompt_name, 'prompt_text': prompt_text}
        except Exception as e:
            self.execution_error.emit(f"Error loading prompt: {str(e)}")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, str(e))
            raise e

    @pyqtSlot(str)
    def on_prompt_loaded(self, prompt_text):
        """Update prompt editor when prompt is loaded."""
        self.prompt_editor.setPlainText(prompt_text)
        self.log_output("✅ Prompt loaded successfully.")

    @asyncSlot()
    async def execute_prompt(self):
        """Asynchronously execute the current prompt."""
        prompt_text = self.prompt_editor.toPlainText().strip()
        prompt_name = self.prompt_selector.currentText()
        if not prompt_text:
            self.execution_error.emit("No prompt provided.")
            return
        self.execution_started.emit()
        task_id = f"execute_prompt_{id(prompt_text)}"
        if self.dispatcher:
            self.dispatcher.emit_task_started(task_id)
        task = asyncio.create_task(self._execute_prompt_async(task_id, prompt_name, prompt_text))
        self.running_tasks[task_id] = task
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))

    async def _execute_prompt_async(self, task_id, prompt_name, prompt_text):
        """Internal asynchronous prompt execution task."""
        try:
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 10, "Preparing prompt execution")
            await asyncio.sleep(0.5)
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 30, "Processing prompt")
            offline_mode = self.offline_mode_checkbox.isChecked()
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 50, "Executing prompt")
            if offline_mode:
                if self.dispatcher:
                    self.dispatcher.emit_task_progress(task_id, 40, "Local LLM mode detected")
                self.ensure_local_llm_loaded()
                if self.dispatcher:
                    self.dispatcher.emit_task_progress(task_id, 50, "Generating locally...")
                response = await asyncio.to_thread(self.local_llm.generate, prompt_text, 128)
            else:
                if self.parent and hasattr(self.parent, 'execute_prompt'):
                    if self.dispatcher:
                        self.dispatcher.emit_task_progress(task_id, 50, "Executing through parent")
                    await asyncio.sleep(1)
                    response = f"[Simulated remote API response] for: {prompt_text[:20]}..."
                elif hasattr(self.prompt_orchestrator, 'run_cycle'):
                    if self.dispatcher:
                        self.dispatcher.emit_task_progress(task_id, 50, "Running prompt cycle")
                    await asyncio.sleep(1)
                    response = f"[Cycle response for {prompt_text[:20]}...]"
                else:
                    raise ValueError("No remote execution service available.")
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 90, "Processing response")
            result = {"prompt": prompt_text, "response": response}
            await asyncio.sleep(0.3)
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 100, "Execution complete")
            self.execution_finished.emit("Prompt executed successfully.")
            return result
        except Exception as e:
            self.execution_error.emit(f"Exception during execution: {str(e)}")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, str(e))
            raise e

    def _on_task_done(self, task_id, task):
        """Handle completion of asynchronous tasks."""
        self.running_tasks.pop(task_id, None)
        try:
            result = task.result()
            if not task_id.startswith("execute_prompt_"):
                self.log_output(f"✅ Task {task_id} completed successfully!")
            if self.dispatcher:
                self.dispatcher.emit_task_completed(task_id, result)
                if task_id.startswith("execute_prompt_") and 'prompt' in result:
                    prompt_name = self.prompt_selector.currentText()
                    self.dispatcher.emit_prompt_executed(prompt_name, result)
            if 'response' in result:
                self.log_output(f"Response:\n{result['response']}")
        except asyncio.CancelledError:
            self.log_output(f"❌ Task {task_id} was cancelled.")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, "Task was cancelled.")
        except Exception as e:
            self.log_output(f"❌ Task {task_id} failed with error: {str(e)}")

    # --- End of PromptExecutionTab ---

# =============================================================================
# FullSyncTab: Handles full synchronization operations with UI feedback.
# =============================================================================
class FullSyncTab(QWidget):
    """
    Tab interface for running and monitoring full sync operations.
    Provides visual feedback and control over the sync process.
    """
    sync_completed = pyqtSignal(dict)  # Emits a result dict upon completion

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._init_ui()
        self.sync_completed.connect(self._on_sync_completed)

    def _init_ui(self):
        """Initialize the UI components for full sync."""
        layout = QVBoxLayout()

        # Status section: Label and progress bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        layout.addLayout(status_layout)

        # Control buttons: Run Full Sync and Cancel
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Full Sync")
        self.run_button.clicked.connect(self.run_full_sync)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_sync)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Output area for log messages
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.setLayout(layout)

    def log(self, msg: str, level: str = "info"):
        """Log a message with color coding in the output area."""
        color_map = {
            "error": "red",
            "warning": "orange",
            "success": "green",
            "info": "black"
        }
        color = color_map.get(level, "black")
        self.output.append(f'<span style="color: {color}">{msg}</span>')

    async def run_full_sync(self):
        """Asynchronously run the full sync process."""
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Syncing...")
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        try:
            self.log("🚀 Starting full sync process...")
            # TODO: Insert actual sync logic here
            await asyncio.sleep(2)  # Simulate work
            
            result = {
                "status": "success",
                "files_processed": 10,
                "errors": [],
                "warnings": []
            }
            self.sync_completed.emit(result)
        except Exception as e:
            self.log(f"❌ Error during sync: {str(e)}", "error")
            self.sync_completed.emit({"status": "error", "message": str(e)})
        finally:
            self.run_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.progress_bar.setRange(0, 100)

    def cancel_sync(self):
        """Cancel the full sync operation."""
        self.log("⚠️ Sync cancelled by user", "warning")
        self.status_label.setText("Cancelled")
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def _on_sync_completed(self, result: Dict):
        """Handle the result once the sync process is completed."""
        if result["status"] == "success":
            self.status_label.setText("✅ Sync Complete")
            self.log("✅ Full sync completed successfully!", "success")
            if result.get("warnings"):
                for warning in result["warnings"]:
                    self.log(f"⚠️ {warning}", "warning")
        else:
            self.status_label.setText("❌ Sync Failed")
            self.log(f"❌ Sync failed: {result.get('message', 'Unknown error')}", "error")

# =============================================================================
# End of AIDE_tabs.py
# =============================================================================
