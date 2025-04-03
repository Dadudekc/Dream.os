"""
Episode Panel Component

This panel handles generated content management and dispatching.
It provides content editing, metadata management, and export options.
"""

import logging
import json
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPlainTextEdit, QPushButton, QGroupBox,
    QLabel, QLineEdit, QComboBox, QCheckBox,
    QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)

class MetadataEditor(QWidget):
    """Widget for editing episode metadata."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        self.title_edit = QLineEdit()
        layout.addRow("Title:", self.title_edit)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Story", "Article", "Documentation",
            "Tutorial", "Other"
        ])
        layout.addRow("Category:", self.category_combo)
        
        # Tags
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Enter tags separated by commas")
        layout.addRow("Tags:", self.tags_edit)
        
        # Description
        self.description_edit = QPlainTextEdit()
        self.description_edit.setMaximumHeight(100)
        layout.addRow("Description:", self.description_edit)
        
    def get_metadata(self) -> Dict[str, Any]:
        """Get the current metadata values."""
        return {
            'title': self.title_edit.text(),
            'category': self.category_combo.currentText(),
            'tags': [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()],
            'description': self.description_edit.toPlainText(),
            'created_at': datetime.now().isoformat()
        }
        
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set metadata values from dictionary."""
        self.title_edit.setText(metadata.get('title', ''))
        
        category = metadata.get('category', '')
        index = self.category_combo.findText(category)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
            
        self.tags_edit.setText(','.join(metadata.get('tags', [])))
        self.description_edit.setPlainText(metadata.get('description', ''))

class EpisodePanel(QWidget):
    """
    Episode Panel for content management and dispatching
    
    Features:
    - Content editing and formatting
    - Metadata management
    - Export options
    - Dispatch to various services
    """
    
    # Signals
    episode_saved = pyqtSignal(dict)    # Emitted when episode is saved
    status_update = pyqtSignal(str)     # Emitted for status bar updates
    
    def __init__(self, services: Optional[Dict[str, Any]] = None):
        """Initialize the Episode Panel.
        
        Args:
            services: Dictionary containing required services:
                     - episode_service: For episode management
                     - export_service: For exporting content
        """
        super().__init__()
        
        self.services = services or {}
        self.logger = logger
        self.current_episode = None
        
        # Initialize UI
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Content editor
        content_group = QGroupBox("Content")
        content_layout = QVBoxLayout()
        
        # Editor toolbar
        toolbar_layout = QHBoxLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown", "Plain Text", "HTML"])
        
        self.word_count_label = QLabel("Words: 0")
        
        toolbar_layout.addWidget(QLabel("Format:"))
        toolbar_layout.addWidget(self.format_combo)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.word_count_label)
        
        content_layout.addLayout(toolbar_layout)
        
        # Content editor
        self.content_editor = QPlainTextEdit()
        self.content_editor.setFont(QFont("Consolas", 10))
        content_layout.addWidget(self.content_editor)
        
        content_group.setLayout(content_layout)
        layout.addWidget(content_group)
        
        # Metadata section
        metadata_group = QGroupBox("Metadata")
        metadata_layout = QVBoxLayout()
        
        self.metadata_editor = MetadataEditor()
        metadata_layout.addWidget(self.metadata_editor)
        
        metadata_group.setLayout(metadata_layout)
        layout.addWidget(metadata_group)
        
        # Export options
        export_group = QGroupBox("Export & Dispatch")
        export_layout = QVBoxLayout()
        
        # Export format
        format_layout = QHBoxLayout()
        
        self.export_combo = QComboBox()
        self.export_combo.addItems(["JSON", "Markdown", "Text", "HTML"])
        
        self.include_metadata = QCheckBox("Include Metadata")
        self.include_metadata.setChecked(True)
        
        format_layout.addWidget(QLabel("Export Format:"))
        format_layout.addWidget(self.export_combo)
        format_layout.addStretch()
        format_layout.addWidget(self.include_metadata)
        
        export_layout.addLayout(format_layout)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save")
        self.export_button = QPushButton("Export")
        self.dispatch_button = QPushButton("Dispatch")
        
        action_layout.addWidget(self.save_button)
        action_layout.addWidget(self.export_button)
        action_layout.addStretch()
        action_layout.addWidget(self.dispatch_button)
        
        export_layout.addLayout(action_layout)
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
    def _connect_signals(self):
        """Connect widget signals to slots."""
        # Content changes
        self.content_editor.textChanged.connect(self._update_word_count)
        
        # Button clicks
        self.save_button.clicked.connect(self._save_episode)
        self.export_button.clicked.connect(self._export_episode)
        self.dispatch_button.clicked.connect(self._dispatch_episode)
        
    def set_content(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Set the episode content and metadata."""
        self.content_editor.setPlainText(content)
        
        if metadata:
            self.metadata_editor.set_metadata(metadata)
            
        self._update_word_count()
        
    def _update_word_count(self):
        """Update the word count display."""
        text = self.content_editor.toPlainText()
        word_count = len(text.split())
        self.word_count_label.setText(f"Words: {word_count}")
        
    def _save_episode(self):
        """Save the current episode."""
        if not self.content_editor.toPlainText():
            self.status_update.emit("No content to save")
            return
            
        try:
            episode = {
                'content': self.content_editor.toPlainText(),
                'format': self.format_combo.currentText(),
                'metadata': self.metadata_editor.get_metadata()
            }
            
            if episode_service := self.services.get('episode_service'):
                episode = episode_service.save_episode(episode)
                self.current_episode = episode
                self.episode_saved.emit(episode)
                self.status_update.emit("Episode saved successfully")
            else:
                # Fallback: Save to local file
                self._save_to_file(episode)
                
        except Exception as e:
            self.logger.error(f"Error saving episode: {str(e)}")
            self.status_update.emit(f"Error saving episode: {str(e)}")
            
    def _export_episode(self):
        """Export the episode to a file."""
        if not self.content_editor.toPlainText():
            self.status_update.emit("No content to export")
            return
            
        try:
            # Get export format
            export_format = self.export_combo.currentText().lower()
            include_metadata = self.include_metadata.isChecked()
            
            # Prepare content
            content = self.content_editor.toPlainText()
            metadata = self.metadata_editor.get_metadata() if include_metadata else None
            
            if export_service := self.services.get('export_service'):
                # Use export service if available
                exported = export_service.export_content(
                    content,
                    export_format,
                    metadata
                )
                self.status_update.emit(f"Content exported using {export_format} format")
            else:
                # Fallback: Basic file export
                self._export_to_file(content, metadata, export_format)
                
        except Exception as e:
            self.logger.error(f"Error exporting episode: {str(e)}")
            self.status_update.emit(f"Error exporting episode: {str(e)}")
            
    def _dispatch_episode(self):
        """Dispatch the episode to configured services."""
        if not self.content_editor.toPlainText():
            self.status_update.emit("No content to dispatch")
            return
            
        try:
            episode = {
                'content': self.content_editor.toPlainText(),
                'format': self.format_combo.currentText(),
                'metadata': self.metadata_editor.get_metadata()
            }
            
            if episode_service := self.services.get('episode_service'):
                # Get available dispatch targets
                targets = episode_service.get_dispatch_targets()
                
                if not targets:
                    self.status_update.emit("No dispatch targets available")
                    return
                    
                # TODO: Show dispatch target selection dialog
                # For now, just dispatch to all available targets
                for target in targets:
                    success = episode_service.dispatch_episode(episode, target)
                    if success:
                        self.status_update.emit(f"Episode dispatched to {target}")
                    else:
                        self.status_update.emit(f"Failed to dispatch to {target}")
            else:
                self.status_update.emit("Episode service not available")
                
        except Exception as e:
            self.logger.error(f"Error dispatching episode: {str(e)}")
            self.status_update.emit(f"Error dispatching episode: {str(e)}")
            
    def _save_to_file(self, episode: Dict[str, Any]):
        """Fallback method to save episode to a local file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Episode",
            "",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(episode, f, indent=2)
                self.status_update.emit(f"Episode saved to {file_path}")
            except Exception as e:
                self.logger.error(f"Error saving to file: {str(e)}")
                self.status_update.emit(f"Error saving to file: {str(e)}")
                
    def _export_to_file(self, content: str, metadata: Optional[Dict[str, Any]], 
                       export_format: str):
        """Fallback method to export content to a local file."""
        extensions = {
            'json': '.json',
            'markdown': '.md',
            'text': '.txt',
            'html': '.html'
        }
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Content",
            "",
            f"{export_format.upper()} Files (*{extensions[export_format]})"
        )
        
        if file_path:
            try:
                if export_format == 'json':
                    data = {
                        'content': content,
                        'metadata': metadata
                    } if metadata else {'content': content}
                    
                    with open(file_path, 'w') as f:
                        json.dump(data, f, indent=2)
                else:
                    # For other formats, just write the content
                    # TODO: Add proper formatting for markdown and HTML
                    with open(file_path, 'w') as f:
                        f.write(content)
                        
                self.status_update.emit(f"Content exported to {file_path}")
            except Exception as e:
                self.logger.error(f"Error exporting to file: {str(e)}")
                self.status_update.emit(f"Error exporting to file: {str(e)}")
                
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the panel."""
        return {
            'content': self.content_editor.toPlainText(),
            'format': self.format_combo.currentText(),
            'metadata': self.metadata_editor.get_metadata(),
            'export_format': self.export_combo.currentText(),
            'include_metadata': self.include_metadata.isChecked()
        } 