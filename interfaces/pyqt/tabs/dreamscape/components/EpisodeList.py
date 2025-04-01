"""
Episode List Component

This module provides the UI for displaying and managing generated episodes.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QGroupBox, QPlainTextEdit, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from pathlib import Path
import logging
from typing import Optional, Dict, Any

class EpisodeList(QWidget):
    """Widget for displaying and managing generated episodes."""
    
    # Signals
    episode_selected = pyqtSignal(dict)  # Emits selected episode data
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the episode list widget."""
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        # Episodes group
        episodes_group = QGroupBox("Generated Episodes")
        episodes_layout = QVBoxLayout()
        
        # Episode list
        self.episode_list = QListWidget()
        episodes_layout.addWidget(self.episode_list)
        
        # Episode content
        content_group = QGroupBox("Episode Content")
        content_layout = QVBoxLayout()
        
        self.episode_content = QPlainTextEdit()
        self.episode_content.setReadOnly(True)
        content_layout.addWidget(self.episode_content)
        
        # Export buttons
        export_layout = QHBoxLayout()
        self.save_txt_button = QPushButton("Save as TXT")
        self.save_md_button = QPushButton("Save as MD")
        self.save_html_button = QPushButton("Save as HTML")
        
        export_layout.addWidget(self.save_txt_button)
        export_layout.addWidget(self.save_md_button)
        export_layout.addWidget(self.save_html_button)
        content_layout.addLayout(export_layout)
        
        content_group.setLayout(content_layout)
        
        # Add all groups to main layout
        episodes_group.setLayout(episodes_layout)
        layout.addWidget(episodes_group)
        layout.addWidget(content_group)
        
        self.setLayout(layout)
        
        # Connect signals
        self.episode_list.currentItemChanged.connect(self._on_episode_selected)
        self.save_txt_button.clicked.connect(lambda: self._save_episode("txt"))
        self.save_md_button.clicked.connect(lambda: self._save_episode("md"))
        self.save_html_button.clicked.connect(lambda: self._save_episode("html"))
        
    def add_episode(self, episode_data: Dict[str, Any]):
        """Add an episode to the list."""
        title = episode_data.get('title', 'Untitled Episode')
        self.episode_list.addItem(title)
        # Store the episode data in the item
        item = self.episode_list.item(self.episode_list.count() - 1)
        item.setData(Qt.UserRole, episode_data)
        
    def _on_episode_selected(self, current, previous):
        """Handle episode selection."""
        if current is None:
            return
            
        episode_data = current.data(Qt.UserRole)
        if episode_data:
            self.episode_content.setPlainText(episode_data.get('content', ''))
            self.episode_selected.emit(episode_data)
            
    async def _save_episode(self, format_type: str):
        """Save the current episode content in the specified format."""
        content = self.episode_content.toPlainText()
        if not content:
            return
            
        file_filters = {
            'txt': 'Text files (*.txt)',
            'md': 'Markdown files (*.md)',
            'html': 'HTML files (*.html)'
        }
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            'Save Episode',
            '',
            file_filters.get(format_type, 'Text files (*.*)')
        )
        
        if file_path:
            try:
                path = Path(file_path)
                path.write_text(content)
            except Exception as e:
                self.logger.error(f"Error saving file: {e}")
                
    def clear(self):
        """Clear the episode list and content."""
        self.episode_list.clear()
        self.episode_content.clear()

    def get_selected_episode(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected episode data."""
        selected_items = self.episode_list.selectedItems()
        if not selected_items:
            return None
        return selected_items[0].data(Qt.UserRole) 
