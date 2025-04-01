"""
Prompt Panel Component

This panel handles prompt template rendering and configuration.
It provides template selection, variable injection, and prompt preview.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QPlainTextEdit, QPushButton, QGroupBox,
    QLabel, QTreeWidget, QTreeWidgetItem, QSplitter,
    QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor

logger = logging.getLogger(__name__)

class JinjaHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Jinja2 templates."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Jinja2 syntax formats
        self.formats = {
            'variable': self._create_format('#c678dd'),  # Purple for {{ var }}
            'statement': self._create_format('#61afef'),  # Blue for {% if %}
            'comment': self._create_format('#98c379'),   # Green for {# comment #}
        }
        
    def _create_format(self, color: str) -> QTextCharFormat:
        """Create a text format with the specified color."""
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        return fmt
        
    def highlightBlock(self, text: str):
        """Highlight Jinja2 syntax in the text block."""
        # Highlight variables {{ var }}
        start = text.find('{{')
        while start >= 0:
            end = text.find('}}', start)
            if end >= 0:
                self.setFormat(start, end - start + 2, self.formats['variable'])
                start = text.find('{{', end + 2)
            else:
                break
                
        # Highlight statements {% if %}
        start = text.find('{%')
        while start >= 0:
            end = text.find('%}', start)
            if end >= 0:
                self.setFormat(start, end - start + 2, self.formats['statement'])
                start = text.find('{%', end + 2)
            else:
                break
                
        # Highlight comments {# comment #}
        start = text.find('{#')
        while start >= 0:
            end = text.find('#}', start)
            if end >= 0:
                self.setFormat(start, end - start + 2, self.formats['comment'])
                start = text.find('{#', end + 2)
            else:
                break

class PromptPanel(QWidget):
    """
    Prompt Template Panel
    
    Features:
    - Template selection and preview
    - Variable injection and validation
    - Rendered prompt preview
    - Token count estimation
    """
    
    # Signals
    prompt_ready = pyqtSignal(str)     # Emitted when prompt is ready
    status_update = pyqtSignal(str)    # Emitted for status bar updates
    
    def __init__(self, services: Optional[Dict[str, Any]] = None):
        """Initialize the Prompt Panel.
        
        Args:
            services: Dictionary containing required services:
                     - template_engine: For template rendering
                     - prompt_service: For validation
        """
        super().__init__()
        
        self.services = services or {}
        self.logger = logger
        self.current_content = None
        
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Create main splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # --- Create Right Panel First (Contains template_preview) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Template preview
        template_preview_group = QGroupBox("Template Preview")
        template_preview_layout = QVBoxLayout()
        
        self.template_preview = QPlainTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setFont(QFont("Consolas", 10))
        
        # Add syntax highlighting
        self.highlighter = JinjaHighlighter(self.template_preview.document())
        
        template_preview_layout.addWidget(self.template_preview)
        template_preview_group.setLayout(template_preview_layout)
        right_layout.addWidget(template_preview_group)
        
        # Rendered prompt preview
        prompt_preview_group = QGroupBox("Rendered Prompt")
        prompt_preview_layout = QVBoxLayout()
        
        self.prompt_preview = QPlainTextEdit()
        self.prompt_preview.setReadOnly(True)
        self.prompt_preview.setFont(QFont("Consolas", 10))
        
        # Add token counter
        preview_header = QHBoxLayout()
        self.tokens_label = QLabel("Tokens: 0")
        preview_header.addStretch()
        preview_header.addWidget(self.tokens_label)
        
        prompt_preview_layout.addLayout(preview_header)
        prompt_preview_layout.addWidget(self.prompt_preview)
        
        prompt_preview_group.setLayout(prompt_preview_layout)
        right_layout.addWidget(prompt_preview_group)
        # --- End Right Panel ---

        # --- Create Left Panel --- 
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Template selection
        template_group = QGroupBox("Template")
        template_layout = QFormLayout()
        
        self.template_combo = QComboBox()
        self._load_templates()
        
        self.model_combo = QComboBox()
        # Add OpenAI Models group
        self.model_combo.addItem("🧠 OpenAI Models")
        self.model_combo.insertSeparator(self.model_combo.count())
        self.model_combo.addItems([
            "GPT-4o",
            "GPT-4o mini",
            "GPT-4o with scheduled tasks",
            "GPT-4.5",
            "GPT-4"
        ])
        # Add Custom Models group
        self.model_combo.addItem("")  # Empty item as spacer
        self.model_combo.addItem("🔧 Custom Models")
        self.model_combo.insertSeparator(self.model_combo.count())
        self.model_combo.addItems([
            "o1",
            "o3-mini",
            "o3-mini-high"
        ])
        # Set default model
        self.model_combo.setCurrentText("GPT-4o")
        
        template_layout.addRow("Template:", self.template_combo)
        template_layout.addRow("Model:", self.model_combo)
        
        template_group.setLayout(template_layout)
        left_layout.addWidget(template_group)
        
        # Variables tree
        variables_group = QGroupBox("Template Variables")
        variables_layout = QVBoxLayout()
        
        self.variables_tree = QTreeWidget()
        self.variables_tree.setHeaderLabels(["Name", "Value", "Status"])
        self.variables_tree.setColumnWidth(0, 150)
        
        variables_layout.addWidget(self.variables_tree)
        variables_group.setLayout(variables_layout)
        left_layout.addWidget(variables_group)
        # --- End Left Panel ---
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set splitter sizes (40% left, 60% right)
        splitter.setSizes([400, 600])
        
        # Add splitter to main layout
        layout.addWidget(splitter)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.validate_button = QPushButton("Validate")
        self.reload_button = QPushButton("Reload Template")
        self.send_button = QPushButton("Send to Execution")
        self.send_button.setEnabled(False)
        
        action_layout.addWidget(self.validate_button)
        action_layout.addWidget(self.reload_button)
        action_layout.addStretch()
        action_layout.addWidget(self.send_button)
        
        layout.addLayout(action_layout)
        
    def _connect_signals(self):
        """Connect widget signals to slots."""
        # Button clicks
        self.validate_button.clicked.connect(self._validate_prompt)
        self.reload_button.clicked.connect(self.reload_template)
        self.send_button.clicked.connect(self._send_prompt)
        
        # Template selection
        self.template_combo.currentTextChanged.connect(self._load_template)
        
        # Model selection
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        
        # Variable changes
        self.variables_tree.itemChanged.connect(self._update_preview)
        
    def _on_model_changed(self, model_label: str):
        """Reload templates when the model changes."""
        model_key = self._resolve_model_key(model_label)
        self._load_templates(model_key)
        
    def set_content(self, content: Dict[str, Any]):
        """Set content from the Ingest Panel."""
        self.current_content = content
        self._update_variables()
        self._update_preview()
        
    def _load_templates(self, model_key: Optional[str] = None):
        """Load available templates into the combo box."""
        if template_engine := self.services.get('template_engine'):
            try:
                templates = template_engine.get_available_templates(model_key=model_key)
                current = self.template_combo.currentText()
                
                self.template_combo.clear()
                self.template_combo.addItems(templates)
                
                # Try to restore previous selection if it's still available
                if current in templates:
                    self.template_combo.setCurrentText(current)
                elif templates:
                    # Otherwise select first available template
                    self._load_template(templates[0])
                    
            except Exception as e:
                self.logger.error(f"Error loading templates: {str(e)}")
                self.status_update.emit("Error loading templates")
                
    def _load_template(self, template_name: str):
        """Load the selected template and update the preview."""
        if not template_name:
            return
            
        if template_engine := self.services.get('template_engine'):
            try:
                template_content = template_engine.get_template_content(template_name)
                self.template_preview.setPlainText(template_content)
                self._update_variables()
            except Exception as e:
                self.logger.error(f"Error loading template: {str(e)}")
                self.status_update.emit(f"Error loading template: {str(e)}")
                
    def _update_variables(self):
        """Update the variables tree with current content."""
        self.variables_tree.clear()
        
        if not self.current_content:
            return
            
        # Add content variables
        content_item = QTreeWidgetItem(["content"])
        content_item.setText(1, str(len(self.current_content.get('content', ''))))
        content_item.setText(2, "✓")
        
        # Add URL
        url_item = QTreeWidgetItem(["url"])
        url_item.setText(1, self.current_content.get('url', ''))
        url_item.setText(2, "✓" if self.current_content.get('url') else "✗")
        
        # Add options
        options = self.current_content.get('options', {})
        options_item = QTreeWidgetItem(["options"])
        for key, value in options.items():
            option_item = QTreeWidgetItem(options_item)
            option_item.setText(0, key)
            option_item.setText(1, str(value))
            option_item.setText(2, "✓")
            
        self.variables_tree.addTopLevelItems([content_item, url_item, options_item])
        self.variables_tree.expandAll()
        
    def _update_preview(self):
        """Update the rendered prompt preview."""
        if not self.current_content:
            return
            
        if template_engine := self.services.get('template_engine'):
            try:
                template_name = self.template_combo.currentText()
                prompt = template_engine.render_from_template(
                    template_name,
                    self.current_content
                )
                
                self.prompt_preview.setPlainText(prompt)
                
                # Update token count
                token_count = len(prompt.split())
                self.tokens_label.setText(f"Tokens: {token_count}")
                
                # Enable send button if valid
                self.send_button.setEnabled(True)
                
            except Exception as e:
                self.logger.error(f"Error rendering prompt: {str(e)}")
                self.status_update.emit(f"Error rendering prompt: {str(e)}")
                self.send_button.setEnabled(False)
                
    def _validate_prompt(self):
        """Validate the current prompt."""
        if not self.prompt_preview.toPlainText():
            self.status_update.emit("No prompt to validate")
            return
            
        if prompt_service := self.services.get('prompt_service'):
            try:
                is_valid = prompt_service.validate_prompt(
                    self.prompt_preview.toPlainText(),
                    self.model_combo.currentText()
                )
                
                if is_valid:
                    QMessageBox.information(self, "Validation", "Prompt is valid!")
                    self.send_button.setEnabled(True)
                else:
                    QMessageBox.warning(self, "Validation", "Prompt validation failed")
                    self.send_button.setEnabled(False)
                    
            except Exception as e:
                self.logger.error(f"Error validating prompt: {str(e)}")
                self.status_update.emit(f"Error validating prompt: {str(e)}")
                
    def _resolve_model_key(self, label: str) -> str:
        """Convert display model name to internal model key.
        
        Args:
            label: Display name of the model from dropdown
            
        Returns:
            Internal model key used by the backend
        """
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
        return mapping.get(label, label)
        
    def _send_prompt(self):
        """Send the prompt to the execution panel."""
        prompt = self.prompt_preview.toPlainText()
        if not prompt:
            return
            
        # Include resolved model key
        model_key = self._resolve_model_key(self.model_combo.currentText())
        self.prompt_ready.emit(prompt)
        self.status_update.emit(f"Prompt sent to execution panel (using {model_key})")
        
    def reload_template(self):
        """Reload the current template."""
        current_template = self.template_combo.currentText()
        if current_template:
            self._load_template(current_template)
            self.status_update.emit("Template reloaded")
            
    def regenerate_prompt(self):
        """Regenerate the prompt with current content."""
        self._update_preview()
        
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the panel."""
        # Ensure token count parsing is safe
        try:
            token_count = int(self.tokens_label.text().split(":")[1].strip())
        except (IndexError, ValueError):
            token_count = 0
            
        return {
            'template': self.template_combo.currentText(),
            'model': self.model_combo.currentText(),
            'content': self.current_content,
            'prompt': self.prompt_preview.toPlainText(),
            'token_count': token_count 
        }

    def restore_state(self, state: Dict[str, Any]):
        """Restore panel state from saved data.
        
        Args:
            state: Dictionary containing saved state
        """
        try:
            if 'template' in state and self.template_combo.findText(state['template']) != -1:
                self.template_combo.setCurrentText(state['template']) # Triggers _load_template
            
            if 'model' in state and self.model_combo.findText(state['model']) != -1:
                self.model_combo.setCurrentText(state['model'])
                
            # Note: Restoring 'content' might require re-populating variables tree 
            # and re-rendering, which is complex. For now, focus on selections.
            if 'prompt' in state:
                 self.prompt_preview.setPlainText(state.get('prompt', ''))
                 
            if 'token_count' in state:
                 self.tokens_label.setText(f"Tokens: {state.get('token_count', 0)}")
                 
            self.logger.info("PromptPanel state restored.")
            # Manually trigger update after restoring state if needed
            # self._update_preview()
            
        except Exception as e:
            self.logger.error(f"Error restoring PromptPanel state: {e}", exc_info=True) 