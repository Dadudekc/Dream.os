#!/usr/bin/env python3
"""
SystemLoader - Centralized Service Initialization System
=======================================================

This module provides a centralized system for initializing and wiring all
Dream.OS services with proper dependency injection and sequencing using
the micro-factory pattern.

It ensures:
- Services are initialized in the correct dependency order
- Configuration is properly extracted and passed
- Factories are used for proper dependency injection
- Singleton services are properly maintained
- Proper fallbacks for missing or failing services
"""

import logging
import os
from typing import Dict, Any, Optional, List, Union, Type
from pathlib import Path

# Core service registry import
from core.services.service_registry import ServiceRegistry

# Base factory imports
from core.PathManager import PathManager
from config.ConfigManager import ConfigManager

# Core micro-factories
from core.micro_factories.prompt_factory import PromptFactory
from core.micro_factories.feedback_factory import FeedbackFactory
from core.micro_factories.chat_factory import ChatFactory
from core.micro_factories.orchestrator_factory import OrchestratorFactory
from core.micro_factories.dreamscape_factory import DreamscapeFactory
from core.micro_factories.merit_test_factory import MeritTestFactory

# Utility imports
from core.memory_utils import fix_memory_file

# Configure the logger at module level
logger = logging.getLogger(__name__)


class SystemLoader:
    """
    Centralized service loader that initializes all Dream.OS components
    using the micro-factory pattern with proper dependency handling.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the system loader.
        
        Args:
            config_path: Optional custom path to config file
        """
        # Initialize logger first
        self.logger = logging.getLogger(__name__)

        # Core services to initialize first (these are not from factories)
        self.path_manager = PathManager()
        
        # Initialize config manager
        try:
            self.config_manager = ConfigManager(config_path)
            logger.info("✅ ConfigManager initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize ConfigManager: {e}")
            self.config_manager = ConfigManager()  # Fallback to default
        
        # Register these core services immediately
        ServiceRegistry.register("config_manager", self.config_manager)
        ServiceRegistry.register("logger", logger)
        ServiceRegistry.register("path_manager", self.path_manager)
        
        # Define the factory registry with service name to factory class mapping
        self.factories = {
            "prompt_manager": PromptFactory,
            "feedback_engine": FeedbackFactory,
            "openai_client": self._create_openai_client,  # Special handler function
            "driver_manager": self._create_driver_manager,  # Special handler function
            "prompt_service": self._create_prompt_service,  # Special handler
            "chat_manager": ChatFactory,
            "cycle_service": OrchestratorFactory,
            "task_orchestrator": OrchestratorFactory,
            "dreamscape_generator": DreamscapeFactory,
            "merit_chain_manager": MeritTestFactory,
            "test_coverage_analyzer": MeritTestFactory,
            "test_generator_service": MeritTestFactory
        }
    
    def boot(self) -> Dict[str, Any]:
        """
        Boot all core services in proper dependency order using registered factories.
        
        Returns:
            Dict of initialized services
        """
        logger.info("🚀 Starting Dream.OS SystemLoader...")
        
        try:
            # Verify and repair memory files early
            self._repair_memory_files()
            
            # Initialize all services in dependency order
            self._initialize_services()
            
            # Verify core services
            missing_services = self._validate_required_services()
            if missing_services:
                logger.warning(f"⚠️ Missing required services: {missing_services}")
            else:
                logger.info("✅ All required services registered and available")
            
            # Return all registered services
            return {name: ServiceRegistry.get(name) for name in ServiceRegistry._services}
        except Exception as e:
            # Fallback logger in case of unexpected errors
            fallback_logger = logging.getLogger(__name__)
            fallback_logger.error(f"Failed to initialize core services: {e}", exc_info=True)
            # Return whatever services were successfully initialized
            return {name: ServiceRegistry.get(name) for name in ServiceRegistry._services}
    
    def _repair_memory_files(self) -> None:
        """Verify and repair all memory files."""
        try:
            memory_dir = self.path_manager.get_memory_path()
            memory_files = [
                "prompt_memory.json",
                "engagement_memory.json",
                "conversation_memory.json",
                "cycle_memory.json"
            ]
            
            for memory_file in memory_files:
                file_path = memory_dir / memory_file
                if file_path.exists():
                    fix_memory_file(str(file_path), logger)
            
            logger.info("✅ Memory files verified/repaired")
        except Exception as e:
            logger.error(f"❌ Error repairing memory files: {e}")
    
    def _initialize_services(self) -> None:
        """Initialize all services using their registered factories in dependency order."""
        # Process services in a specific order to respect dependencies
        service_init_order = [
            "prompt_manager",
            "feedback_engine",
            "openai_client",
            "driver_manager",
            "chat_manager",
            "prompt_service",
            "cycle_service",
            "task_orchestrator",
            "dreamscape_generator",
            "merit_chain_manager",
            "test_coverage_analyzer",
            "test_generator_service"
        ]
        
        # Initialize services in the specified order
        for service_name in service_init_order:
            if service_name in self.factories and not ServiceRegistry.has_service(service_name):
                self._initialize_service(service_name)
    
    def _initialize_service(self, service_name: str) -> None:
        """Initialize a single service using its factory."""
        if ServiceRegistry.has_service(service_name):
            logger.info(f"✓ Service '{service_name}' already initialized.")
            return
        
        try:
            factory = self.factories.get(service_name)
            if factory is None:
                logger.warning(f"⚠️ No factory registered for service '{service_name}'")
                return
            
            # Handle special factory functions vs factory classes
            if callable(factory) and not isinstance(factory, type):
                # It's a method that handles creation directly
                instance = factory()
            else:
                # It's a factory class with a create method
                instance = factory.create()
            
            if instance:
                ServiceRegistry.register(service_name, instance)
                logger.info(f"✅ Service '{service_name}' initialized via factory")
            else:
                logger.warning(f"⚠️ Factory for '{service_name}' returned None")
        except Exception as e:
            logger.error(f"❌ Failed to initialize '{service_name}': {e}")
    
    def _validate_required_services(self) -> List[str]:
        """Validate that all required services are registered."""
        required_services = [
            "config_manager",
            "path_manager",
            "prompt_manager",
            "feedback_engine",
            "prompt_service"
        ]
        
        missing = []
        for service in required_services:
            if not ServiceRegistry.has_service(service):
                missing.append(service)
        
        return missing
    
    def _create_openai_client(self) -> Any:
        """Special handler to create the OpenAIClient service."""
        try:
            from core.chatgpt_automation.OpenAIClient import OpenAIClient
            
            profile_dir = os.path.join(self.path_manager.get_path("cache"), "openai_profile")
            openai_client = OpenAIClient(profile_dir=profile_dir)
            openai_client.boot()  # Explicitly boot the client at startup
            return openai_client
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAIClient: {e}")
            return None
    
    def _create_driver_manager(self) -> Any:
        """Special handler to create the DriverManager service."""
        try:
            from core.DriverManager import DriverManager
            
            # Extract configuration values
            headless = self.config_manager.get("headless", True)
            profile_dir = self.config_manager.get("profile_dir", None)
            cookie_file = self.config_manager.get("cookie_file", None)
            chrome_options = self.config_manager.get("chrome_options", [])
            
            driver_manager = DriverManager(
                headless=headless,
                profile_dir=profile_dir,
                cookie_file=cookie_file,
                undetected_mode=True,
                additional_arguments=chrome_options,
                timeout=30,
                logger=self.logger
            )
            return driver_manager
        except Exception as e:
            logger.error(f"❌ Failed to initialize DriverManager: {e}")
            return None
    
    def _create_prompt_service(self) -> Any:
        """Special handler to create the UnifiedPromptService."""
        try:
            # Avoid circular import
            from core.services.prompt_execution_service import UnifiedPromptService
            
            # Get required dependencies from registry
            config_manager = ServiceRegistry.get("config_manager")
            path_manager = ServiceRegistry.get("path_manager")
            prompt_manager = ServiceRegistry.get("prompt_manager")
            driver_manager = ServiceRegistry.get("driver_manager")
            feedback_engine = ServiceRegistry.get("feedback_engine")
            
            # Create the prompt service with properly extracted config values
            prompt_service = UnifiedPromptService(
                config_manager=config_manager,
                path_manager=path_manager,
                config_service=config_manager,  # Use config_manager as config_service
                prompt_manager=prompt_manager,
                driver_manager=driver_manager,
                feedback_engine=feedback_engine,
                model=config_manager.get("default_model", "gpt-4o-mini")
            )
            
            return prompt_service
        except Exception as e:
            logger.error(f"❌ Failed to initialize UnifiedPromptService: {e}")
            return None


# Convenience function to create and boot the system
def initialize_system(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Initialize and boot the entire system with a single function call.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Dict of initialized services
    """
    loader = SystemLoader(config_path)
    return loader.boot()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize system and print status
    services = initialize_system()
    
    print("System initialized with the following services:")
    for name, service in services.items():
        status = "✅ Available" if service else "⚠️ Empty implementation"
        print(f"  - {name}: {status}") 