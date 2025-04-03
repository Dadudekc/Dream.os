"""
Service initialization for DreamOS.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import QWidget

from chat_mate.core.micro_factories.chat_factory import create_chat_manager
from chat_mate.core.services.service_registry import ServiceRegistry
from chat_mate.core.config.ConfigManager import ConfigManager
from chat_mate.core.PathManager import PathManager
from chat_mate.core.PromptCycleOrchestrator import PromptCycleOrchestrator
from chat_mate.core.services.service_registry import create_prompt_service
from chat_mate.utils.safe_json import repair_memory_files

from ..utils.empty_service import EmptyService


class ServiceInitializer:
    """Handles initialization and management of all Dream.OS services."""
    
    def __init__(self):
        self.logger = logging.getLogger("Services")
        self.path_manager = PathManager()
        
    def initialize_core_services(self) -> Dict[str, Any]:
        """Initialize and connect core services with proper dependency injection."""
        try:
            # Initialize ConfigManager with proper path
            config_file_path = self.path_manager.get_config_path("base.yaml")
            config_manager = ConfigManager(config_file=str(config_file_path))
            
            # Repair any corrupted memory files
            memory_dir = self.path_manager.get_path("memory")
            repair_memory_files(memory_dir, self.logger)
            
            # Create prompt service first
            prompt_service = create_prompt_service(config_manager)
            if not prompt_service:
                raise RuntimeError("Failed to create PromptService")
            
            # Create chat manager with prompt service
            chat_manager = create_chat_manager(config_manager, self.logger, prompt_service)
            if not chat_manager:
                raise RuntimeError("Failed to create ChatManager")
            
            # Create orchestrator with injected dependencies
            orchestrator = self._create_orchestrator(config_manager, chat_manager, prompt_service)
            
            services = {
                'config_manager': config_manager,
                'chat_manager': chat_manager,
                'orchestrator': orchestrator,
                'prompt_service': prompt_service,
                'path_manager': self.path_manager
            }
            
            # Register services in the service registry
            registry = ServiceRegistry()
            for name, service in services.items():
                registry.register(name, service)
            
            return services
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            raise
            
    def _create_orchestrator(self, config_manager: ConfigManager, 
                           chat_manager: Any, prompt_service: Any) -> Any:
        """Create the PromptCycleOrchestrator with proper error handling."""
        try:
            orchestrator = PromptCycleOrchestrator(
                config_manager=config_manager,
                chat_manager=chat_manager,
                prompt_service=prompt_service
            )
            self.logger.info("PromptCycleOrchestrator initialized successfully")
            return orchestrator
        except Exception as e:
            self.logger.error(f"Failed to initialize PromptCycleOrchestrator: {e}")
            return EmptyService("orchestrator")
            
    def create_empty_service_stub(self) -> Any:
        """Create a minimal service stub for graceful degradation."""
        return type('ServiceStub', (), {
            'prompt_manager': None,
            'chat_manager': None,
            'prompt_handler': None,
            'discord': None,
            'reinforcement_engine': None,
            'cycle_service': None,
            'task_orchestrator': None,
            'dreamscape_generator': None,
            'get_service': lambda x: None
        })
        
    @staticmethod
    def ensure_service(service: Optional[Any], service_name: str, logger: logging.Logger) -> Any:
        """Ensure a service exists or return an empty implementation."""
        if service is None:
            logger.warning(f"Service '{service_name}' not available - creating empty implementation")
            return EmptyService(service_name)
        return service 