"""
Dreamscape Generation Tab Module

This module provides the UI for generating Digital Dreamscape episodes.
It now supports dynamic model selection and filtering of templates based on the selected model.
"""

import os
import logging
from datetime import datetime
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from qasync import asyncSlot

# Import the ServiceInitializer and component managers
from .ServiceInitializer import ServiceInitializer
from .components.GenerationControls import GenerationControls
from .components.EpisodeList import EpisodeList
from .components.ContextTree import ContextTree

logger = logging.getLogger(__name__)

class DreamscapeGenerationTab(QWidget):
    """Main tab for Dreamscape episode generation."""
    
    # Add default update intervals
    UPDATE_INTERVALS = {
        "1 day": 24 * 60 * 60,
        "3 days": 3 * 24 * 60 * 60,
        "7 days": 7 * 24 * 60 * 60,
        "14 days": 14 * 24 * 60 * 60,
        "30 days": 30 * 24 * 60 * 60
    }
    
    def __init__(self, services: Optional[Dict[str, Any]] = None):
        """Initialize the Dreamscape Generation tab.
        
        Args:
            services: Optional dictionary containing services and managers.
                     If not provided, services will be initialized.
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        if services is None:
            self.service_initializer = ServiceInitializer(parent=self)
            self.services = self.service_initializer.initialize_services()
        else:
            self.services = services
            
        # Set up UI
        self.setup_ui()
        
        # Load initial data
        self._load_initial_data()
        
    @property
    def template_manager(self):
        """Get the core template manager service."""
        return self.services.get('template_manager')
        
    @property
    def dreamscape_engine(self):
        """Get the core dreamscape engine service."""
        return self.services.get('dreamscape_engine')
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        # Generation controls
        self.generation_controls = GenerationControls()
        layout.addWidget(self.generation_controls)
        
        # Episode list and context tree
        self.episode_list = EpisodeList()
        layout.addWidget(self.episode_list)
        
        self.context_tree = ContextTree()
        layout.addWidget(self.context_tree)
        
        self.setLayout(layout)
        
        # Connect signals
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect component signals."""
        # Generation controls signals
        self.generation_controls.generationRequested.connect(self._on_generate_clicked)
        self.generation_controls.generationCancelled.connect(self._on_cancel_clicked)
        
        # Episode list signals
        self.episode_list.episode_selected.connect(self._on_episode_selected)
        
    def _load_initial_data(self):
        """Load initial data for components."""
        try:
            # Load templates using the core template_manager
            tm = self.template_manager
            if tm:
                templates = tm.get_available_templates(subfolder='dreamscape')
                self.generation_controls.set_templates(templates)
                
            # Load existing episodes using the core dreamscape_engine
            engine = self.dreamscape_engine
            if engine:
                self.episode_list.load_episodes(engine.output_dir)
                    
        except Exception as e:
            self.logger.error(f"Error loading initial data: {e}", exc_info=True)
            
    @asyncSlot
    async def _on_generate_clicked(self, params: Dict[str, Any]):
        """Handle generate button click.
        
        Args:
            params: Dictionary containing generation parameters
        """
        try:
            # Get the core dreamscape_engine
            engine = self.dreamscape_engine
            if not engine:
                raise RuntimeError("Dreamscape engine not available")
                
            # Call the appropriate generation method on the engine
            # We need to determine if we need chat history first based on params
            # This logic might need refinement depending on engine methods
            
            # Example: If processing a single chat, get history first (if chat_manager available)
            if not params.get('process_all') and params.get('target_chat'):
                # Assuming ChatManager is accessible via self.services if needed
                chat_manager = self.services.get('chat_manager') 
                if chat_manager:
                    chat_history = chat_manager.get_chat_history(params['target_chat'])
                    if chat_history:
                        messages = [entry['content'] for entry in chat_history if 'content' in entry]
                        episode_path = await asyncio.to_thread(
                            engine.generate_episode_from_history, 
                            params['target_chat'], 
                            messages
                        )
                        # TODO: Load episode_path data into episode_list
                    else:
                        self.logger.warning(f"Could not get history for {params['target_chat']}")
                else:
                     self.logger.warning("ChatManager not available to fetch history.")
            elif params.get('process_all'):
                 # TODO: Implement logic to process all chats 
                 # This might involve calling engine methods differently or looping
                 self.logger.warning("Process all chats not fully implemented yet.")
            else:
                 # Maybe generate from memory directly?
                 episode_path = await asyncio.to_thread(
                     engine.generate_episode_from_memory,
                     params['template_name']
                 )
                 # TODO: Load episode_path data into episode_list

            # Simplified: Assume episode_data is returned or load from path
            # self.episode_list.add_episode(episode_data)
            # self.episode_list.episode_list.setCurrentRow(self.episode_list.episode_list.count() - 1)
                
        except Exception as e:
            self.logger.error(f"Error generating episode: {e}", exc_info=True)
            
    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        task_orchestrator = self.services.get('task_orchestrator')
        if task_orchestrator:
             try:
                 task_orchestrator.cancel_current_task()
             except Exception as e:
                 self.logger.error(f"Error canceling task: {e}")
        else:
             self.logger.warning("Task Orchestrator service not found for cancellation.")
            
    def _on_episode_selected(self, episode_data: Dict[str, Any]):
        """Handle episode selection.
        
        Args:
            episode_data: Dictionary containing episode data
        """
        try:
            # Update context tree
            self.context_tree.update_context(episode_data.get('context', {}))
            
        except Exception as e:
            self.logger.error(f"Error handling episode selection: {e}", exc_info=True)
            
    def get_services(self) -> Dict[str, Any]:
        """Get the services dictionary.
        
        Returns:
            Dictionary containing services and managers.
        """
        return self.services
