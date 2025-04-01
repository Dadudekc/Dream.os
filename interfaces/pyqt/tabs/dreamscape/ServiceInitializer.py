"""
Service Initializer Module

This module handles the initialization of services and components for the Dreamscape Generation tab.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

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
        services = {
            'core_services': self._initialize_core_services(),
            'component_managers': self._initialize_component_managers()
        }
        
        # Ensure output directory exists
        output_dir = Path("outputs/dreamscape")
        output_dir.mkdir(parents=True, exist_ok=True)
        services['output_dir'] = str(output_dir)
        
        return services
        
    def _initialize_core_services(self) -> Dict[str, Any]:
        """Initialize core services required for episode generation.
        
        Returns:
            Dict containing initialized core services
        """
        core_services = {}
        
        try:
            # Initialize Cycle Service
            from core.services.cycle_service import CycleService
            cycle_service = CycleService()
            core_services['cycle_service'] = cycle_service
            self.logger.info("Cycle Service initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Cycle Service: {e}")
            core_services['cycle_service'] = None
            
        try:
            # Initialize Prompt Handler
            from core.services.prompt_handler import PromptHandler
            prompt_handler = PromptHandler()
            core_services['prompt_handler'] = prompt_handler
            self.logger.info("Prompt Handler initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Prompt Handler: {e}")
            core_services['prompt_handler'] = None
            
        try:
            # Initialize Discord Processor
            from core.services.discord_processor import DiscordProcessor
            discord_processor = DiscordProcessor()
            core_services['discord_processor'] = discord_processor
            self.logger.info("Discord Processor initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Discord Processor: {e}")
            core_services['discord_processor'] = None
            
        try:
            # Initialize Task Orchestrator
            from core.services.task_orchestrator import TaskOrchestrator
            task_orchestrator = TaskOrchestrator()
            core_services['task_orchestrator'] = task_orchestrator
            self.logger.info("Task Orchestrator initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Task Orchestrator: {e}")
            core_services['task_orchestrator'] = None
            
        try:
            # Initialize Dreamscape Service
            from core.services.dreamscape_service import DreamscapeService
            dreamscape_service = DreamscapeService()
            core_services['dreamscape_service'] = dreamscape_service
            self.logger.info("Dreamscape Service initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Dreamscape Service: {e}")
            core_services['dreamscape_service'] = None
            
        return core_services
        
    def _initialize_component_managers(self) -> Dict[str, Any]:
        """Initialize component managers required for the UI.
        
        Returns:
            Dict containing initialized component managers
        """
        component_managers = {}
        
        try:
            # Initialize Dreamscape Episode Generator
            from .DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator
            episode_generator = DreamscapeEpisodeGenerator()
            component_managers['episode_generator'] = episode_generator
            self.logger.info("Episode Generator initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Episode Generator: {e}")
            component_managers['episode_generator'] = None
            
        try:
            # Initialize Context Manager
            from .ContextManager import ContextManager
            context_manager = ContextManager()
            component_managers['context_manager'] = context_manager
            self.logger.info("Context Manager initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Context Manager: {e}")
            component_managers['context_manager'] = None
            
        try:
            # Initialize UI Manager
            from .UIManager import UIManager
            ui_manager = UIManager(self.parent)
            component_managers['ui_manager'] = ui_manager
            self.logger.info("UI Manager initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize UI Manager: {e}")
            component_managers['ui_manager'] = None
            
        try:
            # Initialize Template Manager
            from .TemplateManager import TemplateManager
            template_manager = TemplateManager()
            component_managers['template_manager'] = template_manager
            self.logger.info("Template Manager initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Template Manager: {e}")
            component_managers['template_manager'] = None
            
        return component_managers
