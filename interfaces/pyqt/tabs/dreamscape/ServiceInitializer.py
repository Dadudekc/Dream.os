"""
Service Initializer Module

This module handles the initialization of services and components for the Dreamscape Generation tab.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Import core services correctly
from core.services.dreamscape.engine import DreamscapeGenerationService # Renamed from dreamscape_generator_service.py
from core.TemplateManager import TemplateManager # Assuming a core TemplateManager exists
from core.PathManager import PathManager # Assuming a core PathManager exists
# Add other necessary core service imports here (e.g., ChatManager if needed directly)

class ServiceInitializer:
    """Handles initialization of services and components for the Dreamscape Generation tab."""
    
    def __init__(self, parent=None, logger=None):
        """Initialize the service initializer.
        
        Args:
            parent: Parent widget
            logger: Optional logger instance
        """
        self.parent = parent
        self.logger = logger or logging.getLogger(__name__)
        
    def initialize_services(self) -> Dict[str, Any]:
        """Initialize all required services and components.
        
        Returns:
            Dict containing initialized services and components
        """
        services = {}
        
        # Initialize Core Dreamscape Services
        try:
            path_manager = PathManager() # Get or init PathManager
            template_manager = TemplateManager() # Get or init TemplateManager
            
            # Initialize Dreamscape Engine (using its new class name if changed, assuming DreamscapeGenerationService for now)
            dreamscape_engine = DreamscapeGenerationService(
                path_manager=path_manager,
                template_manager=template_manager,
                logger=self.logger
            )
            services['dreamscape_engine'] = dreamscape_engine
            self.logger.info("Dreamscape Engine initialized successfully")
            
            # Provide managers needed by the engine or tab
            services['path_manager'] = path_manager
            services['template_manager'] = template_manager
            
            # Add other core services if needed by the tab directly
            # e.g., from core.ChatManager import ChatManager
            # services['chat_manager'] = ChatManager()

        except Exception as e:
            self.logger.error(f"Failed to initialize core Dreamscape services: {e}", exc_info=True)
            # Handle error, maybe provide mock services
            services['dreamscape_engine'] = None
            services['path_manager'] = None
            services['template_manager'] = None

        # Ensure output directory exists (can use path_manager)
        try:
            if services.get('path_manager'):
                output_dir = services['path_manager'].get_path("dreamscape")
                output_dir.mkdir(parents=True, exist_ok=True)
                services['output_dir'] = str(output_dir)
            else:
                 # Fallback if path_manager failed
                output_dir = Path("outputs/dreamscape")
                output_dir.mkdir(parents=True, exist_ok=True)
                services['output_dir'] = str(output_dir)
        except Exception as e:
             self.logger.warning(f"Could not create or verify output directory: {e}")
             services['output_dir'] = "outputs/dreamscape" # Default fallback

        return services

    # Removed old _initialize_core_services and _initialize_component_managers
    # as the logic is now consolidated in initialize_services
