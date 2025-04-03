"""
Service factory for DreamOS.
"""

import logging
from typing import Dict, Any, Optional

from chat_mate.core.config.ConfigManager import ConfigManager
from chat_mate.core.logging.CompositeLogger import CompositeLogger
from chat_mate.core.ConsoleLogger import ConsoleLogger
from chat_mate.core.FileLogger import FileLogger
from chat_mate.core.PromptResponseHandler import PromptResponseHandler
from chat_mate.core.CycleExecutionService import CycleExecutionService
from chat_mate.interfaces.pyqt.dreamscape_services import DreamscapeService
from chat_mate.interfaces.pyqt.dreamscape_ui_logic import DreamscapeUILogic

class ServiceFactory:
    """Factory for creating and managing DreamOS services with proper dependency injection."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = logging.getLogger("ServiceFactory")
        self._services: Dict[str, Any] = {}
        
    def create_logger(self) -> CompositeLogger:
        """Create the composite logger with console and file handlers."""
        if "logger" not in self._services:
            console_logger = ConsoleLogger(self.config_manager)
            file_logger = FileLogger(self.config_manager)
            self._services["logger"] = CompositeLogger(
                loggers=[console_logger, file_logger],
                config_manager=self.config_manager
            )
        return self._services["logger"]
        
    def create_prompt_response_handler(self) -> PromptResponseHandler:
        """Create the prompt response handler with dependencies."""
        if "prompt_response_handler" not in self._services:
            logger = self.create_logger()
            self._services["prompt_response_handler"] = PromptResponseHandler(
                config_manager=self.config_manager,
                logger=logger
            )
        return self._services["prompt_response_handler"]
        
    def create_cycle_service(self) -> CycleExecutionService:
        """Create the cycle execution service with dependencies."""
        if "cycle_service" not in self._services:
            logger = self.create_logger()
            response_handler = self.create_prompt_response_handler()
            self._services["cycle_service"] = CycleExecutionService(
                prompt_manager=None,  # Will be injected later
                config_manager=self.config_manager,
                logger=logger,
                response_handler=response_handler
            )
        return self._services["cycle_service"]
        
    def create_dreamscape_service(self) -> DreamscapeService:
        """Create the dreamscape service with dependencies."""
        if "dreamscape_service" not in self._services:
            cycle_service = self.create_cycle_service()
            response_handler = self.create_prompt_response_handler()
            self._services["dreamscape_service"] = DreamscapeService(
                config=self.config_manager,
                cycle_service=cycle_service,
                prompt_response_handler=response_handler
            )
        return self._services["dreamscape_service"]
        
    def create_ui_logic(self) -> DreamscapeUILogic:
        """Create the UI logic with dependencies."""
        if "ui_logic" not in self._services:
            dreamscape_service = self.create_dreamscape_service()
            ui_logic = DreamscapeUILogic()
            ui_logic.service = dreamscape_service
            self._services["ui_logic"] = ui_logic
        return self._services["ui_logic"]
        
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a service by name if it exists."""
        return self._services.get(service_name) 