import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QTextEdit, QListWidget, QListWidgetItem, QSplitter,
    QProgressBar, QCheckBox, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer

from interfaces.pyqt.tabs.dreamscape_generation.ServiceInitializer import ServiceInitializer


class DreamscapeGenerationTab(QWidget):
    """
    UI tab for generating Digital Dreamscape episodes from chat history.
    Provides interface to select past chats, generate episodes, and view results.
    """
    
    statusUpdated = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # Initialize services (chat manager, template manager, etc.)
        self.service_initializer = ServiceInitializer(parent_widget=self)
        self.services = self.service_initializer.initialize_all()
        
        # Store references to key services
        self.chat_manager = self.services.get("chat_manager")
        self.dreamscape_service = self.services.get("dreamscape_service")
        self.context_synthesizer = self.services.get("context_synthesizer")
        
        # UI Setup
        self.init_ui()
        
        # Load available chats
        self.load_available_chats()
        
        # Load existing episodes
        self.load_episode_list()
        
    def init_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Digital Dreamscape Episode Generator")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # Splitter for main sections
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Chat selection and generation
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Chat selection
        chat_label = QLabel("Select Chat:")
        left_layout.addWidget(chat_label)
        
        self.chat_combo = QComboBox()
        self.chat_combo.setMinimumWidth(300)
        left_layout.addWidget(self.chat_combo)
        
        # Generate episode button
        generate_button = QPushButton("Generate Episode")
        generate_button.clicked.connect(self.generate_episode_from_selected_chat)
        left_layout.addWidget(generate_button)
        
        # Generate all checkbox
        self.generate_all_checkbox = QCheckBox("Generate for All Chats")
        left_layout.addWidget(self.generate_all_checkbox)
        
        # Refresh button
        refresh_button = QPushButton("Refresh Chat List")
        refresh_button.clicked.connect(self.load_available_chats)
        left_layout.addWidget(refresh_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        left_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        left_layout.addWidget(self.status_label)
        
        # Add stretch
        left_layout.addStretch()
        
        # Right panel - Episode list and viewer
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        episode_label = QLabel("Generated Episodes:")
        right_layout.addWidget(episode_label)
        
        # Episode list
        self.episode_list = QListWidget()
        self.episode_list.setMinimumWidth(400)
        self.episode_list.currentItemChanged.connect(self.load_selected_episode)
        right_layout.addWidget(self.episode_list)
        
        # Episode viewer
        viewer_label = QLabel("Episode Content:")
        right_layout.addWidget(viewer_label)
        
        self.episode_viewer = QTextEdit()
        self.episode_viewer.setReadOnly(True)
        right_layout.addWidget(self.episode_viewer)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial sizes
        splitter.setSizes([300, 500])
        
    def load_available_chats(self):
        """Load the list of available chats from the chat service."""
        try:
            self.update_status("Loading available chats...")
            self.chat_combo.clear()
            
            if not self.chat_manager:
                self.update_status("Error: Chat manager not available")
                return
                
            # Get chat titles
            chats = self.chat_manager.get_all_chat_titles()
            if not chats:
                self.update_status("No chats found")
                return
                
            # Add chats to the dropdown
            for chat in chats:
                title = chat.get('title', 'Untitled')
                self.chat_combo.addItem(title)
                
            self.update_status(f"Loaded {len(chats)} chats")
            
        except Exception as e:
            self.logger.error(f"Error loading chat list: {e}")
            self.update_status(f"Error loading chat list: {str(e)}")
    
    def load_episode_list(self):
        """Load the list of existing episodes in the output directory."""
        try:
            self.update_status("Loading episode list...")
            self.episode_list.clear()
            
            # Get the dreamscape output directory
            output_dir = Path("outputs/dreamscape")
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
                self.update_status("Created new episode directory")
                return
                
            # List episode files
            episode_files = list(output_dir.glob("*.md"))
            if not episode_files:
                self.update_status("No episodes found")
                return
                
            # Add episodes to the list widget
            for episode_file in sorted(episode_files, key=os.path.getmtime, reverse=True):
                item = QListWidgetItem(episode_file.name)
                item.setData(Qt.UserRole, str(episode_file))
                self.episode_list.addItem(item)
                
            self.update_status(f"Loaded {len(episode_files)} episodes")
            
            # Select the first episode
            if self.episode_list.count() > 0:
                self.episode_list.setCurrentRow(0)
                
        except Exception as e:
            self.logger.error(f"Error loading episode list: {e}")
            self.update_status(f"Error loading episode list: {str(e)}")
    
    def load_selected_episode(self, current, previous):
        """Load the selected episode content into the viewer."""
        try:
            if not current:
                self.episode_viewer.clear()
                return
                
            # Get the file path from the item data
            file_path = current.data(Qt.UserRole)
            if not file_path or not Path(file_path).exists():
                self.episode_viewer.setText("Episode file not found")
                return
                
            # Load and display the episode content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            self.episode_viewer.setText(content)
            self.update_status(f"Loaded episode: {Path(file_path).name}")
            
        except Exception as e:
            self.logger.error(f"Error loading episode content: {e}")
            self.update_status(f"Error loading episode content: {str(e)}")
    
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
            
            # Check if services are available
            if not self.chat_manager or not self.dreamscape_service:
                self.update_status("Error: Required services not available")
                self.progress_bar.setValue(0)
                return
                
            # Generate the episode
            self.progress_bar.setValue(50)
            
            # Get chat history and use context synthesizer
            chat_history = self.chat_manager.get_chat_history(chat_title)
            
            # Use web source or memory based on availability
            source = "memory"
            if self.context_synthesizer:
                self.update_status("Synthesizing context from multiple sources...")
                context = self.context_synthesizer.synthesize_context(chat_history=chat_history)
                self.update_status(f"Context synthesis complete. Confidence: {context.get('confidence', 0):.2f}")
            
            # Generate episode with synthesized context
            episode_path = self.dreamscape_service.generate_dreamscape_episode(
                chat_title=chat_title,
                chat_history=chat_history,
                source=source
            )
            
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
                    self.episode_list.setCurrentRow(i)
                    break
                    
            self.progress_bar.setValue(100)
            self.update_status(f"Successfully generated episode for {chat_title}")
            
            # Reset progress bar after a delay
            QTimer.singleShot(2000, lambda: self.progress_bar.setValue(0))
            
        except Exception as e:
            self.logger.error(f"Error generating episode: {e}")
            self.update_status(f"Error generating episode: {str(e)}")
            self.progress_bar.setValue(0)
    
    def generate_episodes_for_all_chats(self):
        """Generate episodes for all available chats."""
        try:
            # Check if services are available
            if not self.chat_manager or not self.dreamscape_service:
                self.update_status("Error: Required services not available")
                return
                
            # Get all chat titles
            chats = self.chat_manager.get_all_chat_titles()
            if not chats:
                self.update_status("No chats found")
                return
                
            total_chats = len(chats)
            self.update_status(f"Generating episodes for {total_chats} chats...")
            
            # Generate episodes for each chat
            for i, chat in enumerate(chats):
                chat_title = chat.get('title', 'Untitled')
                self.update_status(f"Generating episode for chat: {chat_title} ({i+1}/{total_chats})")
                
                # Calculate progress percentage
                progress = int((i / total_chats) * 100)
                self.progress_bar.setValue(progress)
                
                # Get chat history and use context synthesizer
                chat_history = self.chat_manager.get_chat_history(chat_title)
                
                # Use web source or memory based on availability
                source = "memory"
                if self.context_synthesizer:
                    context = self.context_synthesizer.synthesize_context(chat_history=chat_history)
                    self.logger.info(f"Context synthesis complete. Confidence: {context.get('confidence', 0):.2f}")
                
                # Generate episode with synthesized context
                episode_path = self.dreamscape_service.generate_dreamscape_episode(
                    chat_title=chat_title,
                    chat_history=chat_history,
                    source=source
                )
                
                if not episode_path:
                    self.logger.error(f"Failed to generate episode for {chat_title}")
                
            # Refresh the episode list
            self.load_episode_list()
            
            self.progress_bar.setValue(100)
            self.update_status(f"Successfully generated episodes for {total_chats} chats")
            
            # Reset progress bar after a delay
            QTimer.singleShot(2000, lambda: self.progress_bar.setValue(0))
            
        except Exception as e:
            self.logger.error(f"Error generating episodes: {e}")
            self.update_status(f"Error generating episodes: {str(e)}")
            self.progress_bar.setValue(0)
    
    def update_status(self, message: str):
        """Update the status label and emit the statusUpdated signal."""
        self.status_label.setText(message)
        self.statusUpdated.emit(message)
        self.logger.info(message) 