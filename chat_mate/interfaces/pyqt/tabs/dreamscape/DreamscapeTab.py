import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QTextEdit, QListWidget, QListWidgetItem, QSplitter,
    QProgressBar, QCheckBox, QFileDialog, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer

# from chat_mate.interfaces.pyqt.tabs.dreamscape.ServiceInitializer import ServiceInitializer # Absolute import failed
from .ServiceInitializer import ServiceInitializer # Use relative import

from core.services.dreamscape.dreamscape_service import DreamscapeGenerationService

# Assuming these components and the controller will be created
# We'll need to import them properly once they exist
try:
    from .components.EpisodeList import EpisodeList
    from .components.TemplateEditor import TemplateEditor
    from .components.ContextViewer import ContextViewer
    from .dreamscape_controller import DreamscapeController
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"DreamscapeTab: Could not import components or controller: {e}")
    COMPONENTS_AVAILABLE = False
    # Define dummy classes if imports fail to allow basic structure loading
    class EpisodeList(QWidget):
        def __init__(self, ctrl): super().__init__(); self.layout = QVBoxLayout(self); self.layout.addWidget(QLabel("EpisodeList (Not Loaded)"))
    class TemplateEditor(QWidget):
        def __init__(self, ctrl): super().__init__(); self.layout = QVBoxLayout(self); self.layout.addWidget(QLabel("TemplateEditor (Not Loaded)"))
    class ContextViewer(QWidget):
        def __init__(self, ctrl): super().__init__(); self.layout = QVBoxLayout(self); self.layout.addWidget(QLabel("ContextViewer (Not Loaded)"))
    class DreamscapeController:
        def __init__(self, service, chat_manager): pass # Dummy controller

class DreamscapeTab(QWidget):
    """
    UI tab for generating Digital Dreamscape episodes from chat history.
    Provides interface to select past chats, generate episodes, and view results.
    """
    
    statusUpdated = pyqtSignal(str)
    
    def __init__(self, dreamscape_service, chat_manager, parent=None):
        """
        Initializes the DreamscapeTab.

        Args:
            dreamscape_service: Instance of DreamscapeGenerationService.
            chat_manager: Instance of ChatManager.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        if not COMPONENTS_AVAILABLE:
             self.logger.error("Cannot initialize DreamscapeTab properly: Components or Controller failed to import.")
             # Basic fallback UI
             layout = QVBoxLayout(self)
             layout.addWidget(QLabel("Error: DreamscapeTab components failed to load."))
             self.setLayout(layout)
             return

        # Initialize services (chat manager, template manager, etc.)
        self.service_initializer = ServiceInitializer(parent_widget=self)
        self.service_initializer.initialize_all()
        
        # Initialize controller with required services
        self.controller = DreamscapeController(dreamscape_service, chat_manager)
        
        # UI Setup
        self.init_ui()
        
        # Load available chats
        self.load_available_chats()
        
        # Load existing episodes
        self.load_episode_list()
        
    def init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("Dreamscape")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)

        # Use QSplitter for resizable sections
        main_splitter = QSplitter(Qt.Horizontal)
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0,0,0,0)

        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0,0,0,0)

        # Instantiate components with the controller
        self.episode_list = EpisodeList(self.controller)
        self.template_editor = TemplateEditor(self.controller)
        self.context_viewer = ContextViewer(self.controller)

        # Arrange components (Example Layout)
        left_layout.addWidget(self.episode_list)
        right_layout.addWidget(self.context_viewer) # Show context on the right initially

        main_splitter.addWidget(left_pane)
        main_splitter.addWidget(right_pane)
        # Adjust initial sizes if needed
        main_splitter.setSizes([300, 500])

        # Add main splitter and template editor below
        self.layout.addWidget(main_splitter, 1) # Give splitter more stretch factor
        self.layout.addWidget(self.template_editor, 1) # Give editor stretch factor

        self.setLayout(self.layout)
        self.logger.info("DreamscapeTab initialized.")
        
    def load_available_chats(self):
        """Load the list of available chats from the chat service."""
        try:
            self.update_status("Loading available chats...")
            self.episode_list.refresh()
            
        except Exception as e:
            self.logger.error(f"Error loading chat list: {e}")
            self.update_status(f"Error loading chat list: {str(e)}")
    
    def load_episode_list(self):
        """Load the list of existing episodes in the output directory."""
        try:
            self.update_status("Loading episode list...")
            self.episode_list.refresh()
            
        except Exception as e:
            self.logger.error(f"Error loading episode list: {e}")
            self.update_status(f"Error loading episode list: {str(e)}")
    
    def generate_episode_from_selected_chat(self):
        """Generate a dreamscape episode from the selected chat."""
        try:
            # Check if the "Generate All" checkbox is checked
            if self.generate_all_checkbox.isChecked():
                self.generate_episodes_for_all_chats()
                return
                
            # Get the selected chat title
            chat_title = self.chat_combo.currentText()
            if not chat_title:
                self.update_status("No chat selected")
                return
                
            self.update_status(f"Generating episode for chat: {chat_title}...")
            self.progress_bar.setValue(25)
            
            # Get the chat manager and dreamscape service
            chat_manager = self.service_initializer.get_chat_manager()
            if not chat_manager or not chat_manager.dreamscape_service:
                self.update_status("Error: Services not available")
                self.progress_bar.setValue(0)
                return
                
            # Generate the episode
            self.progress_bar.setValue(50)
            episode_path = chat_manager.generate_dreamscape_episode(chat_title)
            self.progress_bar.setValue(75)
            
            if not episode_path:
                self.update_status(f"Failed to generate episode for {chat_title}")
                self.progress_bar.setValue(0)
                return
                
            # Refresh the episode list and select the new episode
            self.load_episode_list()
            
            # Find and select the newly created episode
            for i in range(self.episode_list.count()):
                item = self.episode_list.item(i)
                if str(episode_path) in item.data(Qt.UserRole):
                    self.episode_list.setCurrentItem(item)
                    break
                    
            self.update_status(f"Successfully generated episode for {chat_title}")
            self.progress_bar.setValue(100)
            
            # Reset progress bar after a delay
            QTimer.singleShot(3000, lambda: self.progress_bar.setValue(0))
            
        except Exception as e:
            self.logger.error(f"Error generating episode: {e}")
            self.update_status(f"Error generating episode: {str(e)}")
            self.progress_bar.setValue(0)
    
    def generate_episodes_for_all_chats(self):
        """Generate episodes for all available chats."""
        try:
            self.update_status("Generating episodes for all chats...")
            
            # Get the chat manager
            chat_manager = self.service_initializer.get_chat_manager()
            if not chat_manager or not chat_manager.dreamscape_service:
                self.update_status("Error: Services not available")
                return
                
            # Get all chat titles
            chats = chat_manager.get_all_chat_titles()
            if not chats:
                self.update_status("No chats found")
                return
                
            # Confirm with the user
            confirm = QMessageBox.question(
                self, 
                "Generate Episodes",
                f"This will generate episodes for {len(chats)} chats. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm != QMessageBox.Yes:
                self.update_status("Operation cancelled")
                return
                
            # Generate episodes for each chat
            generated_count = 0
            for idx, chat in enumerate(chats):
                chat_title = chat.get('title', 'Untitled')
                self.update_status(f"Generating episode for {chat_title} ({idx+1}/{len(chats)})...")
                self.progress_bar.setValue(int((idx / len(chats)) * 100))
                
                episode_path = chat_manager.generate_dreamscape_episode(chat_title)
                if episode_path:
                    generated_count += 1
                    
            # Refresh the episode list
            self.load_episode_list()
            
            self.update_status(f"Generated {generated_count} episodes out of {len(chats)} chats")
            self.progress_bar.setValue(100)
            
            # Reset progress bar after a delay
            QTimer.singleShot(3000, lambda: self.progress_bar.setValue(0))
            
        except Exception as e:
            self.logger.error(f"Error generating episodes: {e}")
            self.update_status(f"Error generating episodes: {str(e)}")
            self.progress_bar.setValue(0)
    
    def update_status(self, message: str):
        """Update the status label and emit the statusUpdated signal."""
        self.status_label.setText(message)
        self.statusUpdated.emit(message)
        self.logger.info(message)

    def refresh_context(self):
        if hasattr(self, 'context_viewer') and self.context_viewer:
            self.context_viewer.refresh()

    def refresh_chats(self):
        if hasattr(self, 'episode_list') and self.episode_list:
            self.episode_list.refresh() 
