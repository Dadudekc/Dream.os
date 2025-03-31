import logging
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import QWidget

from config.ConfigManager import ConfigManager
from core.services.service_registry import ServiceRegistry
from core.system_loaders.dreamscape_system_loader import DreamscapeSystemLoader

class ServiceInitializer:
    """
    ServiceInitializer encapsulates the initialization of all services required by
    the DreamscapeGenerationTab using the DreamscapeSystemLoader.
    
    It handles:
      - Injecting external services (or retrieving them from a ui_logic container).
      - Using DreamscapeSystemLoader for core service initialization.
      - Setting up component managers with proper dependency injection.
      - Determining and ensuring the output directory exists.
      
    After initialization, it returns a dictionary of initialized services and component managers.
    """

    def __init__(self, parent_widget: Optional[QWidget] = None, config_manager = None, logger: Optional[logging.Logger] = None):
        self.parent_widget = parent_widget
        self.config_manager = config_manager or ConfigManager()
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize the DreamscapeSystemLoader
        self.system_loader = DreamscapeSystemLoader(
            config_manager=self.config_manager,
            path_manager=None,  # Will be created by loader
            service_registry=ServiceRegistry(),
            logger=self.logger
        )
        
        # Store references to initialized services
        self.services = {}

    def initialize_services(self, prompt_manager=None, chat_manager=None, response_handler=None,
                          memory_manager=None, discord_manager=None, ui_logic=None):
        """
        Initialize services with externally provided instances using DreamscapeSystemLoader.
        This method is called from DreamscapeGenerationTab to inject dependencies.
        """
        try:
            # Load all services through DreamscapeSystemLoader
            service_registry = self.system_loader.load(
                parent_widget=self.parent_widget,
                prompt_manager=prompt_manager,
                chat_manager=chat_manager,
                headless=False,
                test_mode=False
            )
            
            # Store initialized services
            self.services = self._extract_services_from_registry(service_registry)
            
            # Return initialized services for the tab to use
            return self._get_initialized_services()
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing services: {str(e)}")
            return {
                'core_services': {},
                'component_managers': {},
                'output_dir': None
            }

    def _extract_services_from_registry(self, service_registry: ServiceRegistry) -> Dict[str, Any]:
        """Extract and categorize services from the registry."""
        services = {}
        
        # Core services
        services['cycle_service'] = service_registry.get('cycle_service')
        services['prompt_handler'] = service_registry.get('prompt_handler')
        services['discord_processor'] = service_registry.get('discord_processor')
        services['task_orchestrator'] = service_registry.get('task_orchestrator')
        services['dreamscape_generator'] = service_registry.get('dreamscape_generator')
        
        # Component managers
        services['template_manager'] = service_registry.get('template_manager')
        services['episode_generator'] = service_registry.get('episode_generator')
        services['context_manager'] = service_registry.get('context_manager')
        services['ui_manager'] = service_registry.get('ui_manager')
        
        # Output directory
        services['output_dir'] = service_registry.get('output_dir')
        
        return services

    def _get_initialized_services(self) -> Dict[str, Any]:
        """
        Returns a dictionary of all initialized services and component managers.
        """
        return {
            'core_services': {
                'cycle_service': self.services.get('cycle_service'),
                'prompt_handler': self.services.get('prompt_handler'),
                'discord_processor': self.services.get('discord_processor'),
                'task_orchestrator': self.services.get('task_orchestrator'),
                'dreamscape_generator': self.services.get('dreamscape_generator')
            },
            'component_managers': {
                'template_manager': self.services.get('template_manager'),
                'episode_generator': self.services.get('episode_generator'),
                'context_manager': self.services.get('context_manager'),
                'ui_manager': self.services.get('ui_manager')
            },
            'output_dir': self.services.get('output_dir')
        }

    def get_chat_manager(self):
        """Get the initialized chat manager instance."""
        return self.services.get('chat_manager')
    
    def get_template_manager(self):
        """Get the initialized template manager instance."""
        return self.services.get('template_manager')
    
    def get_dreamscape_generator(self):
        """Get the initialized dreamscape generator service."""
        return self.services.get('dreamscape_generator')
