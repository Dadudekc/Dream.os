"""
Generation Controls Component

This module provides the UI controls for generating Dreamscape episodes.
It encapsulates all generation-related settings and actions.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QCheckBox, QComboBox, QLineEdit,
    QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Dict, Any, Optional
import logging

class GenerationControls(QWidget):
    """Widget containing all controls for episode generation."""
    
    # Signals
    generationRequested = pyqtSignal(dict)  # Emits generation parameters
    generationCancelled = pyqtSignal()
    modelChanged = pyqtSignal(str)  # Emits when model selection changes
    
    def __init__(self, parent=None):
        """Initialize the generation controls widget."""
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # Initialize UI elements
        self.setup_ui()
        
        # Connect signals
        self._connect_signals()
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Settings group
        settings_group = QGroupBox("Generation Settings")
        settings_layout = QFormLayout()
        
        # Template selection
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template:"))
        self.template_dropdown = QComboBox()
        template_layout.addWidget(self.template_dropdown)
        settings_layout.addRow("Template:", template_layout)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItems([
            "GPT-4o",
            "GPT-4o mini",
            "GPT-4o with scheduled tasks",
            "GPT-4.5",
            "GPT-4",
            "o1",
            "o3-mini",
            "o3-mini-high"
        ])
        model_layout.addWidget(self.model_dropdown)
        settings_layout.addRow("Model:", model_layout)
        
        # Target chat input
        chat_layout = QHBoxLayout()
        chat_layout.addWidget(QLabel("Target Chat:"))
        self.target_chat_input = QLineEdit()
        chat_layout.addWidget(self.target_chat_input)
        settings_layout.addRow("Target Chat:", chat_layout)
        
        # Options
        self.process_all_chats_checkbox = QCheckBox("Process All Chats")
        self.reverse_order_checkbox = QCheckBox("Reverse Order")
        self.headless_checkbox = QCheckBox("Headless Mode")
        self.post_discord_checkbox = QCheckBox("Post to Discord")
        
        options_layout = QHBoxLayout()
        options_layout.addWidget(self.process_all_chats_checkbox)
        options_layout.addWidget(self.reverse_order_checkbox)
        options_layout.addWidget(self.headless_checkbox)
        options_layout.addWidget(self.post_discord_checkbox)
        settings_layout.addRow("Options:", options_layout)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.generate_button = QPushButton("Generate Episode")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        
        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
    def _connect_signals(self):
        """Connect internal signals and slots."""
        self.generate_button.clicked.connect(self._on_generate_clicked)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.model_dropdown.currentTextChanged.connect(self.modelChanged.emit)
        
    def _on_generate_clicked(self):
        """Handle generate button click."""
        try:
            self.generate_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # Get generation parameters
            params = {
                'template_name': self.template_dropdown.currentText(),
                'target_chat': self.target_chat_input.text(),
                'model': self._resolve_model_key(self.model_dropdown.currentText()),
                'process_all': self.process_all_chats_checkbox.isChecked(),
                'reverse_order': self.reverse_order_checkbox.isChecked(),
                'headless': self.headless_checkbox.isChecked(),
                'post_discord': self.post_discord_checkbox.isChecked()
            }
            
            # Emit generation request
            self.generationRequested.emit(params)
            
        except Exception as e:
            self.logger.error(f"Error preparing generation parameters: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to prepare generation: {str(e)}")
            self._reset_buttons()
            
    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        self.generationCancelled.emit()
        self._reset_buttons()
        
    def _reset_buttons(self):
        """Reset button states."""
        self.generate_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
    def set_templates(self, templates: list):
        """Update the template dropdown with new templates."""
        self.template_dropdown.clear()
        self.template_dropdown.addItems(templates)
        
    def disable_feature(self, feature: str):
        """Disable a specific feature."""
        if feature == 'discord':
            self.post_discord_checkbox.setEnabled(False)
            self.post_discord_checkbox.setToolTip("Discord integration not available")
        elif feature == 'headless':
            self.headless_checkbox.setEnabled(False)
            self.headless_checkbox.setToolTip("Headless mode not available")
            
    def _resolve_model_key(self, label: str) -> str:
        """Map UI model label to an internal model key."""
        mapping = {
            "GPT-4o": "gpt-4o",
            "GPT-4o mini": "gpt-4o-mini",
            "GPT-4o with scheduled tasks": "gpt-4o-scheduled",
            "GPT-4.5": "gpt-4.5",
            "GPT-4": "gpt-4",
            "o1": "o1",
            "o3-mini": "o3-mini",
            "o3-mini-high": "o3-mini-high"
        }
        return mapping.get(label, label.lower()) 
