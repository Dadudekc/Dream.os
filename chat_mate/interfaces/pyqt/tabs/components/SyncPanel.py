"""
Sync Panel Component

This panel handles prompt execution and monitoring.
It provides real-time execution status, token usage tracking,
and response streaming.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPlainTextEdit, QPushButton, QGroupBox,
    QLabel, QProgressBar, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)

class ExecutionMetrics(QWidget):
    """Widget for displaying execution metrics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Execution time
        self.time_label = QLabel("0:00")
        layout.addRow("Time:", self.time_label)
        
        # Token usage
        self.tokens_label = QLabel("0/0")
        layout.addRow("Tokens:", self.tokens_label)
        
        # Cost estimate
        self.cost_label = QLabel("$0.00")
        layout.addRow("Est. Cost:", self.cost_label)
        
        self.start_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_time)
        
    def start(self):
        """Start tracking execution time."""
        self.start_time = datetime.now()
        self.timer.start(1000)  # Update every second
        
    def stop(self):
        """Stop tracking execution time."""
        self.timer.stop()
        
    def reset(self):
        """Reset all metrics."""
        self.stop()
        self.start_time = None
        self.time_label.setText("0:00")
        self.tokens_label.setText("0/0")
        self.cost_label.setText("$0.00")
        
    def _update_time(self):
        """Update the execution time display."""
        if not self.start_time:
            return
            
        elapsed = datetime.now() - self.start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        self.time_label.setText(f"{minutes}:{seconds:02d}")
        
    def update_tokens(self, used: int, total: int):
        """Update token usage display."""
        self.tokens_label.setText(f"{used}/{total}")
        
        # Update cost estimate (based on GPT-4 pricing)
        cost = (used / 1000) * 0.03  # $0.03 per 1K tokens
        self.cost_label.setText(f"${cost:.2f}")

class SyncPanel(QWidget):
    """
    Sync Panel for prompt execution and monitoring
    
    Features:
    - Real-time execution status
    - Token usage tracking
    - Response streaming
    - Execution metrics
    """
    
    # Signals
    response_ready = pyqtSignal(dict)  # Emitted when response is complete
    status_update = pyqtSignal(str)    # Emitted for status bar updates
    
    def __init__(self, services: Optional[Dict[str, Any]] = None):
        """Initialize the Sync Panel.
        
        Args:
            services: Dictionary containing required services:
                     - prompt_service: For prompt execution
                     - chat_manager: For chat history
        """
        super().__init__()
        
        self.services = services or {}
        self.logger = logger
        self.current_prompt = None
        self.current_model = None
        
        # Initialize UI
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Execution controls
        controls_group = QGroupBox("Execution Controls")
        controls_layout = QHBoxLayout()
        
        # Temperature control
        temp_layout = QFormLayout()
        self.temp_spin = QSpinBox()
        self.temp_spin.setRange(0, 100)
        self.temp_spin.setValue(70)  # Default 0.7
        self.temp_spin.setSingleStep(10)
        temp_layout.addRow("Temperature:", self.temp_spin)
        
        # Max tokens
        tokens_layout = QFormLayout()
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(1, 4096)
        self.max_tokens.setValue(2048)
        tokens_layout.addRow("Max Tokens:", self.max_tokens)
        
        # Action buttons
        self.execute_button = QPushButton("Execute")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.clear_button = QPushButton("Clear")
        
        controls_layout.addLayout(temp_layout)
        controls_layout.addLayout(tokens_layout)
        controls_layout.addStretch()
        controls_layout.addWidget(self.execute_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.clear_button)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Progress section
        progress_group = QGroupBox("Execution Progress")
        progress_layout = QVBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        # Status message
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        # Metrics
        self.metrics = ExecutionMetrics()
        progress_layout.addWidget(self.metrics)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Response preview
        response_group = QGroupBox("Response")
        response_layout = QVBoxLayout()
        
        self.response_preview = QPlainTextEdit()
        self.response_preview.setReadOnly(True)
        self.response_preview.setFont(QFont("Consolas", 10))
        
        response_layout.addWidget(self.response_preview)
        response_group.setLayout(response_layout)
        layout.addWidget(response_group)
        
    def _connect_signals(self):
        """Connect widget signals to slots."""
        self.execute_button.clicked.connect(self._execute_prompt)
        self.stop_button.clicked.connect(self._stop_execution)
        self.clear_button.clicked.connect(self._clear_response)
        
    def set_prompt(self, prompt: str, model: str = "gpt-4o"):
        """Set the prompt for execution.
        
        Args:
            prompt: The prompt text to execute
            model: The model key to use (e.g. 'gpt-4o', 'gpt-4o-mini')
        """
        self.current_prompt = prompt
        self.current_model = model
        self.execute_button.setEnabled(bool(prompt))
        
        # Update max tokens based on model
        max_tokens = {
            'gpt-4o': 4096,
            'gpt-4o-mini': 2048,
            'gpt-4o-scheduled': 4096,
            'gpt-4.5': 8192,
            'gpt-4': 4096,
            'o1': 4096,
            'o3-mini': 2048,
            'o3-mini-high': 4096
        }.get(model, 4096)
        
        self.max_tokens.setValue(max_tokens)
        self.status_label.setText(f"Ready (using {model})")
        
    def _execute_prompt(self):
        """Execute the current prompt."""
        if not self.current_prompt or not self.current_model:
            self.status_update.emit("No prompt to execute")
            return
            
        if prompt_service := self.services.get('prompt_service'):
            try:
                # Update UI state
                self.execute_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.clear_button.setEnabled(False)
                self.response_preview.clear()
                self.progress_bar.setValue(0)
                self.metrics.reset()
                self.metrics.start()
                
                # Prepare execution parameters
                params = {
                    'temperature': self.temp_spin.value() / 100,
                    'max_tokens': self.max_tokens.value(),
                    'stream': True
                }
                
                # Start execution
                self.status_label.setText("Executing prompt...")
                prompt_service.execute_async(
                    self.current_prompt,
                    self.current_model,
                    params,
                    on_token=self._handle_token,
                    on_complete=self._handle_complete,
                    on_error=self._handle_error
                )
                
            except Exception as e:
                self.logger.error(f"Error executing prompt: {str(e)}")
                self._handle_error(str(e))
                
    def _stop_execution(self):
        """Stop the current execution."""
        if prompt_service := self.services.get('prompt_service'):
            try:
                prompt_service.stop_execution()
                self.status_label.setText("Execution stopped")
                self._reset_ui_state()
            except Exception as e:
                self.logger.error(f"Error stopping execution: {str(e)}")
                
    def _clear_response(self):
        """Clear the response preview."""
        self.response_preview.clear()
        self.progress_bar.setValue(0)
        self.metrics.reset()
        self.status_label.setText("Ready")
        
    def _handle_token(self, token: str, progress: float):
        """Handle streaming token updates."""
        self.response_preview.insertPlainText(token)
        self.response_preview.verticalScrollBar().setValue(
            self.response_preview.verticalScrollBar().maximum()
        )
        
        # Update progress
        self.progress_bar.setValue(int(progress * 100))
        
        # Update metrics
        current_tokens = len(self.response_preview.toPlainText().split())
        self.metrics.update_tokens(current_tokens, self.max_tokens.value())
        
    def _handle_complete(self, response: Dict[str, Any]):
        """Handle completion of execution."""
        self.status_label.setText("Execution complete")
        self.metrics.stop()
        self._reset_ui_state()
        
        # Emit response
        self.response_ready.emit(response)
        
    def _handle_error(self, error: str):
        """Handle execution error."""
        self.status_label.setText(f"Error: {error}")
        self.status_update.emit(f"Execution error: {error}")
        self._reset_ui_state()
        
    def _reset_ui_state(self):
        """Reset UI state after execution."""
        self.execute_button.setEnabled(bool(self.current_prompt))
        self.stop_button.setEnabled(False)
        self.clear_button.setEnabled(True)
        
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the panel."""
        return {
            'temperature': self.temp_spin.value() / 100,
            'max_tokens': self.max_tokens.value(),
            'response': self.response_preview.toPlainText(),
            'status': self.status_label.text(),
            'progress': self.progress_bar.value()
        } 