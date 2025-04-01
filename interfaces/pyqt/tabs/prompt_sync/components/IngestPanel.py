"""
Ingest Panel Component

This panel provides the web scraping control interface for the Prompt Sync Engine.
It handles URL input, scraping options, and content preview.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QCheckBox, QTextEdit, QPushButton,
    QGroupBox, QLabel, QSpinBox, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)

class IngestPanel(QWidget):
    """
    Web Scraper Control Panel
    
    Features:
    - URL input with validation
    - Scraping options (metadata, content selection)
    - Live HTML preview
    - Cleansed content preview
    - Token estimation
    """
    
    # Signals
    content_ready = pyqtSignal(dict)  # Emitted when content is scraped and processed
    status_update = pyqtSignal(str)   # Emitted for status bar updates
    
    def __init__(self, services: Optional[Dict[str, Any]] = None):
        """Initialize the Ingest Panel.
        
        Args:
            services: Dictionary containing required services:
                     - web_scraper: For content fetching
                     - template_engine: For preview rendering
        """
        super().__init__()
        
        self.services = services or {}
        self.logger = logger
        
        # Initialize UI
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # URL Input Group
        url_group = QGroupBox("Target URL")
        url_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL to scrape...")
        
        self.scrape_button = QPushButton("Scrape")
        self.scrape_button.setFixedWidth(100)
        
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.scrape_button)
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)
        
        # Options Group
        options_group = QGroupBox("Scraping Options")
        options_layout = QFormLayout()
        
        # Checkboxes for content selection
        self.extract_title = QCheckBox("Extract Title")
        self.extract_meta = QCheckBox("Extract Metadata")
        self.extract_body = QCheckBox("Full Body")
        
        # Custom selector input
        self.custom_selector = QLineEdit()
        self.custom_selector.setPlaceholderText("CSS Selector (optional)")
        
        # Token limit
        self.token_limit = QSpinBox()
        self.token_limit.setRange(100, 4000)
        self.token_limit.setValue(2000)
        self.token_limit.setSingleStep(100)
        
        # Content format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown", "Plain Text", "HTML"])
        
        options_layout.addRow("", self.extract_title)
        options_layout.addRow("", self.extract_meta)
        options_layout.addRow("", self.extract_body)
        options_layout.addRow("Custom Selector:", self.custom_selector)
        options_layout.addRow("Token Limit:", self.token_limit)
        options_layout.addRow("Output Format:", self.format_combo)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Preview Group
        preview_group = QGroupBox("Content Preview")
        preview_layout = QVBoxLayout()
        
        # Preview tabs
        preview_header = QHBoxLayout()
        self.html_button = QPushButton("HTML")
        self.text_button = QPushButton("Text")
        self.tokens_label = QLabel("Tokens: 0")
        
        preview_header.addWidget(self.html_button)
        preview_header.addWidget(self.text_button)
        preview_header.addStretch()
        preview_header.addWidget(self.tokens_label)
        
        # Preview text area
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 10))
        
        preview_layout.addLayout(preview_header)
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear")
        self.send_button = QPushButton("Send to Prompt")
        self.send_button.setEnabled(False)
        
        action_layout.addWidget(self.clear_button)
        action_layout.addStretch()
        action_layout.addWidget(self.send_button)
        
        layout.addLayout(action_layout)
        
    def _connect_signals(self):
        """Connect widget signals to slots."""
        # Button clicks
        self.scrape_button.clicked.connect(self._handle_scrape)
        self.clear_button.clicked.connect(self._handle_clear)
        self.send_button.clicked.connect(self._handle_send)
        self.html_button.clicked.connect(lambda: self._switch_preview('html'))
        self.text_button.clicked.connect(lambda: self._switch_preview('text'))
        
        # Input changes
        self.url_input.textChanged.connect(self._validate_url)
        self.token_limit.valueChanged.connect(self._update_preview)
        self.format_combo.currentTextChanged.connect(self._update_preview)
        
    async def _handle_scrape(self):
        """Handle the scrape button click."""
        url = self.url_input.text().strip()
        if not url:
            self.status_update.emit("Please enter a URL")
            return
            
        try:
            self.status_update.emit("Scraping content...")
            self.scrape_button.setEnabled(False)
            
            # Get scraper service
            scraper = self.services.get('web_scraper')
            if not scraper:
                raise ValueError("WebScraper service not available")
                
            # Prepare scraping options
            options = {
                'extract_title': self.extract_title.isChecked(),
                'extract_meta': self.extract_meta.isChecked(),
                'extract_body': self.extract_body.isChecked(),
                'custom_selector': self.custom_selector.text().strip(),
                'token_limit': self.token_limit.value(),
                'format': self.format_combo.currentText().lower()
            }
            
            # Scrape content
            content = await scraper.scrape_and_prompt(url, 'web_summary_prompt.jinja', options)
            
            # Update preview
            self._update_preview_content(content)
            self.send_button.setEnabled(True)
            
            self.status_update.emit("Content scraped successfully")
            
        except Exception as e:
            self.logger.error(f"Error scraping content: {str(e)}")
            self.status_update.emit(f"Error: {str(e)}")
            
        finally:
            self.scrape_button.setEnabled(True)
            
    def _handle_clear(self):
        """Clear all inputs and preview."""
        self.url_input.clear()
        self.custom_selector.clear()
        self.preview_text.clear()
        self.send_button.setEnabled(False)
        self.tokens_label.setText("Tokens: 0")
        self.status_update.emit("Content cleared")
        
    def _handle_send(self):
        """Send scraped content to the prompt panel."""
        content = {
            'url': self.url_input.text().strip(),
            'content': self.preview_text.toPlainText(),
            'options': {
                'format': self.format_combo.currentText().lower(),
                'token_count': int(self.tokens_label.text().split(":")[1])
            }
        }
        
        self.content_ready.emit(content)
        self.status_update.emit("Content sent to prompt panel")
        
    def _validate_url(self):
        """Validate the URL input."""
        url = self.url_input.text().strip()
        self.scrape_button.setEnabled(bool(url))
        
    def _update_preview_content(self, content: Dict[str, Any]):
        """Update the preview with scraped content."""
        if not content:
            return
            
        # Update preview text
        if isinstance(content, dict):
            self.preview_text.setPlainText(content.get('content', ''))
            token_count = len(content.get('content', '').split())
        else:
            self.preview_text.setPlainText(str(content))
            token_count = len(str(content).split())
            
        self.tokens_label.setText(f"Tokens: {token_count}")
        
    def _switch_preview(self, mode: str):
        """Switch between HTML and text preview modes."""
        if not self.preview_text.toPlainText():
            return
            
        if mode == 'html':
            self.html_button.setEnabled(False)
            self.text_button.setEnabled(True)
            # Show HTML with syntax highlighting
            content = self.preview_text.toPlainText()
            # TODO: Add HTML syntax highlighting
            
        else:
            self.html_button.setEnabled(True)
            self.text_button.setEnabled(False)
            # Show plain text
            content = self.preview_text.toPlainText()
            # TODO: Strip HTML tags if present
            
    def _update_preview(self):
        """Update preview based on current settings."""
        if not self.preview_text.toPlainText():
            return
            
        # Re-format content based on current settings
        content = self.preview_text.toPlainText()
        token_limit = self.token_limit.value()
        format_type = self.format_combo.currentText().lower()
        
        # TODO: Add content reformatting based on settings
        
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the panel."""
        return {
            'url': self.url_input.text().strip(),
            'options': {
                'extract_title': self.extract_title.isChecked(),
                'extract_meta': self.extract_meta.isChecked(),
                'extract_body': self.extract_body.isChecked(),
                'custom_selector': self.custom_selector.text().strip(),
                'token_limit': self.token_limit.value(),
                'format': self.format_combo.currentText().lower()
            },
            'content': self.preview_text.toPlainText(),
            'token_count': int(self.tokens_label.text().split(":")[1])
        }

    def restore_state(self, state: Dict[str, Any]):
        """Restore panel state from saved data.
        
        Args:
            state: Dictionary containing saved state
        """
        try:
            if 'url' in state:
                self.url_input.setText(state['url'])
            if 'content' in state:
                self.preview_text.setPlainText(state['content'])
            if 'metadata' in state:
                self.extract_title.setChecked(state['metadata'].get('extract_title', False))
                self.extract_meta.setChecked(state['metadata'].get('extract_meta', False))
                self.extract_body.setChecked(state['metadata'].get('extract_body', False))
                self.custom_selector.setText(state['metadata'].get('custom_selector', ''))
                self.token_limit.setValue(state['metadata'].get('token_limit', 2000))
                self.format_combo.setCurrentText(state['metadata'].get('format', 'Markdown'))
        except Exception as e:
            self.logger.error(f"Error restoring state: {e}") 