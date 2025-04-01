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
            self.service_initializer = ServiceInitializer()
            self.services = self.service_initializer.initialize_services()
        else:
            self.services = services
            
        # Set up UI
        self.setup_ui()
        
        # Load initial data
        self._load_initial_data()
        
    @property
    def template_manager(self):
        """Get the template manager service."""
        return self.services['component_managers']['template_manager']
        
    @property
    def episode_generator(self):
        """Get the episode generator service."""
        return self.services['component_managers']['episode_generator']
        
    @property
    def task_orchestrator(self):
        """Get the task orchestrator service."""
        return self.services['core_services']['task_orchestrator']
        
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
            # Load templates
            template_manager = self.services['component_managers']['template_manager']
            if template_manager:
                templates = template_manager.get_available_templates()
                self.generation_controls.set_templates(templates)
                
            # Load existing episodes
            episode_generator = self.services['component_managers']['episode_generator']
            if episode_generator:
                episodes = episode_generator.get_episodes()
                for episode in episodes:
                    self.episode_list.add_episode(episode)
                    
        except Exception as e:
            self.logger.error(f"Error loading initial data: {e}")
            
    async def _on_generate_clicked(self, params: Dict[str, Any]):
        """Handle generate button click.
        
        Args:
            params: Dictionary containing generation parameters
        """
        try:
            # Get episode generator
            episode_generator = self.services['component_managers']['episode_generator']
            if not episode_generator:
                raise RuntimeError("Episode generator not available")
                
            # Generate episode
            episode_data = await episode_generator.generate_episode(params)
            if episode_data:
                self.episode_list.add_episode(episode_data)
                # Select the newly added episode
                self.episode_list.episode_list.setCurrentRow(self.episode_list.episode_list.count() - 1)
                
        except Exception as e:
            self.logger.error(f"Error generating episode: {e}")
            
    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        try:
            task_orchestrator = self.services['core_services']['task_orchestrator']
            if task_orchestrator:
                task_orchestrator.cancel_current_task()
                
        except Exception as e:
            self.logger.error(f"Error canceling task: {e}")
            
    def _on_episode_selected(self, episode_data: Dict[str, Any]):
        """Handle episode selection.
        
        Args:
            episode_data: Dictionary containing episode data
        """
        try:
            # Update context tree
            self.context_tree.update_context(episode_data.get('context', {}))
            
        except Exception as e:
            self.logger.error(f"Error handling episode selection: {e}")
            
    def cleanup(self):
        """Clean up resources."""
        try:
            # Clean up UI managers
            ui_manager = self.services['component_managers']['ui_manager']
            if ui_manager:
                ui_manager.cleanup()
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            
    def get_services(self) -> Dict[str, Any]:
        """Get the services dictionary.
        
        Returns:
            Dictionary containing services and managers.
        """
        return self.services
