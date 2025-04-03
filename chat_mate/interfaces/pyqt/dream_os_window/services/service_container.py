"""
Service container for managing Dream.OS services and their lifecycle.
"""

import logging
from typing import Optional, Dict, Any

from core.chatgpt_automation.OpenAIClient import OpenAIClient
from core.chatgpt_automation.controllers.assistant_mode_controller import AssistantModeController
from core.chatgpt_automation.automation_engine import AutomationEngine
from core.PathManager import PathManager

from .service_initializer import ServiceInitializer
from .service_validator import ServiceValidator


class ServiceContainer:
    """
    Container for managing Dream.OS services.
    Handles initialization, validation, and lifecycle management.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the service container.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger("ServiceContainer")
        self.path_manager = PathManager()
        self.services = {}
        self.openai_client = None
        self.assistant_controller = None
        self.engine = None
        
    def initialize_services(self, services: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize all required services.
        
        Args:
            services: Optional dictionary of pre-initialized services
        """
        self.services = services or {}
        
        # Initialize core services
        self._init_openai_client()
        self._init_assistant_controller()
        self._init_automation_engine()
        
        # Initialize additional services
        initializer = ServiceInitializer()
        try:
            additional_services = initializer.initialize_core_services()
            self.services.update(additional_services)
            self.logger.info("✅ Core services initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            
    def _init_openai_client(self) -> None:
        """Initialize the OpenAI client."""
        try:
            profile_dir = self.path_manager.get_path("cache") / "openai_profile"
            self.openai_client = OpenAIClient(profile_dir=str(profile_dir))
            self.services['openai_client'] = self.openai_client
            self.logger.info("OpenAI client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None
            
    def _init_assistant_controller(self) -> None:
        """Initialize the assistant controller."""
        try:
            self.assistant_controller = AssistantModeController(engine=self.openai_client)
            self.services['assistant_controller'] = self.assistant_controller
            self.logger.info("Assistant controller initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize assistant controller: {e}")
            self.assistant_controller = None
            
    def _init_automation_engine(self) -> None:
        """Initialize the automation engine."""
        try:
            self.engine = AutomationEngine()
            self.services['automation_engine'] = self.engine
            self.logger.info("Automation engine initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize automation engine: {e}")
            self.engine = None
            
    def validate_services(self) -> Dict[str, Any]:
        """
        Validate all services and return validation results.
        
        Returns:
            Dictionary containing validation results
        """
        validator = ServiceValidator(self.logger)
        warnings = validator.verify_services(self.services)
        health_status = validator.check_service_health(self.services)
        
        return {
            'warnings': warnings,
            'health_status': health_status
        }
        
    def shutdown_services(self) -> None:
        """Gracefully shutdown all services."""
        # Shutdown OpenAI client
        if self.openai_client:
            self.logger.info("Shutting down OpenAI Client...")
            if OpenAIClient.is_booted():
                try:
                    self.openai_client.shutdown()
                except Exception as e:
                    self.logger.error(f"❌ Error during OpenAIClient shutdown: {e}", exc_info=True)
            else:
                self.logger.info("OpenAI Client was not booted, skipping shutdown.")
                
        # Shutdown other services
        for service_name in ['orchestrator', 'prompt_manager', 'chat_manager']:
            service = self.services.get(service_name)
            if service and hasattr(service, 'shutdown'):
                try:
                    service.shutdown()
                    self.logger.info(f"✅ Service {service_name} shut down successfully")
                except Exception as e:
                    self.logger.error(f"❌ Error shutting down {service_name}: {e}")
                    
    def get_service(self, service_name: str) -> Optional[Any]:
        """
        Get a service by name.
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            Service instance if found, None otherwise
        """
        return self.services.get(service_name) 