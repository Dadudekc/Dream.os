#!/usr/bin/env python3
"""
SystemLoader - Centralized Service Initialization System
=======================================================

This module provides a centralized system for initializing and wiring all
Dream.OS services with proper dependency injection and sequencing.

It ensures:
- Services are initialized in the correct dependency order
- Configuration is properly extracted and passed
- Path objects are correctly handled
- Singleton services are properly maintained
- Proper fallbacks for missing or failing services
"""

import logging
import sys
import os
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Core service imports
from core.services.service_registry import ServiceRegistry
from core.factories.prompt_factory import PromptFactory
from core.factories.feedback_engine_factory import FeedbackEngineFactory
from core.PathManager import PathManager
from config.ConfigManager import ConfigManager
from core.DriverManager import DriverManager
from core.chatgpt_automation.OpenAIClient import OpenAIClient
from core.memory_utils import fix_memory_file

# Import these only on demand to avoid circular dependencies
# from core.services.prompt_execution_service import UnifiedPromptService
# from core.AletheiaPromptManager import AletheiaPromptManager


class SystemLoader:
    """
    Centralized service loader that initializes all Dream.OS components
    in the correct order with proper dependency handling.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the system loader.
        
        Args:
            config_path: Optional custom path to config file
        """
        self.logger = logging.getLogger(__name__)
        self.registry = ServiceRegistry()
        self.path_manager = PathManager()
        
        # Initialize config manager
        try:
            self.config_manager = ConfigManager(config_path)
            self.logger.info("✅ ConfigManager initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize ConfigManager: {e}")
            self.config_manager = ConfigManager()  # Fallback to default
        
        # Register these core services immediately
        ServiceRegistry.register("config_manager", self.config_manager)
        ServiceRegistry.register("logger", self.logger)
        ServiceRegistry.register("path_manager", self.path_manager)
        
    def boot(self) -> Dict[str, Any]:
        """
        Boot all core services in proper dependency order.
        
        Returns:
            Dict of initialized services
        """
        self.logger.info("🚀 Starting Dream.OS SystemLoader...")
        
        # Verify and repair memory files early
        self._repair_memory_files()
        
        # Initialize in dependency order
        self._init_prompt_manager()
        self._init_feedback_engine()
        self._init_openai_client()
        self._init_driver_manager()
        self._init_prompt_service()
        self._init_orchestration_services()
        
        # Verify core services
        missing_services = self.registry.validate_service_registry()
        if missing_services:
            self.logger.warning(f"⚠️ Missing required services: {missing_services}")
        else:
            self.logger.info("✅ All required services registered and available")
        
        # Return all registered services
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
                    fix_memory_file(str(file_path), self.logger)
            
            self.logger.info("✅ Memory files verified/repaired")
        except Exception as e:
            self.logger.error(f"❌ Error repairing memory files: {e}")
    
    def _init_prompt_manager(self) -> None:
        """Initialize the PromptManager service."""
        if not ServiceRegistry.has_service("prompt_manager"):
            try:
                prompt_manager = PromptFactory.create(ServiceRegistry)
                if prompt_manager:
                    ServiceRegistry.register("prompt_manager", prompt_manager)
                    self.logger.info("✅ PromptManager initialized via factory")
                else:
                    self.logger.warning("⚠️ PromptFactory.create() returned None")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize PromptManager: {e}")
    
    def _init_feedback_engine(self) -> None:
        """Initialize the FeedbackEngine service."""
        if not ServiceRegistry.has_service("feedback_engine"):
            try:
                feedback_engine = FeedbackEngineFactory.create_singleton()
                ServiceRegistry.register("feedback_engine", feedback_engine)
                self.logger.info("✅ FeedbackEngine initialized as singleton")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize FeedbackEngine: {e}")
    
    def _init_driver_manager(self) -> None:
        """Initialize the DriverManager service."""
        if not ServiceRegistry.has_service("driver_manager"):
            try:
                # Extract configuration values instead of passing ConfigManager directly
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
                    timeout=30
                )
                ServiceRegistry.register("driver_manager", driver_manager)
                self.logger.info("✅ DriverManager initialized")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize DriverManager: {e}")
    
    def _init_openai_client(self) -> None:
        """Initialize the OpenAIClient service."""
        if not ServiceRegistry.has_service("openai_client"):
            try:
                profile_dir = os.path.join(self.path_manager.get_path("cache"), "openai_profile")
                openai_client = OpenAIClient(profile_dir=profile_dir)
                openai_client.boot()  # Explicitly boot the client at startup
                ServiceRegistry.register("openai_client", openai_client)
                self.logger.info("✅ OpenAIClient initialized and booted")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize OpenAIClient: {e}")
    
    def _init_prompt_service(self) -> None:
        """Initialize the UnifiedPromptService."""
        if not ServiceRegistry.has_service("prompt_service"):
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
                
                ServiceRegistry.register("prompt_service", prompt_service)
                self.logger.info("✅ UnifiedPromptService initialized")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize UnifiedPromptService: {e}")
    
    def _init_orchestration_services(self) -> None:
        """Initialize the orchestration services (cycle_service, task_orchestrator, dreamscape_generator)."""
        # Initialize cycle service if not already registered
        if not ServiceRegistry.has_service("cycle_service"):
            try:
                # Avoid circular import
                from core.PromptCycleOrchestrator import PromptCycleOrchestrator
                
                # Get required dependencies
                config_manager = ServiceRegistry.get("config_manager")
                prompt_service = ServiceRegistry.get("prompt_service")
                
                # Create cycle service
                cycle_service = PromptCycleOrchestrator(
                    config_manager=config_manager,
                    prompt_service=prompt_service
                )
                
                ServiceRegistry.register("cycle_service", cycle_service)
                self.logger.info("✅ CycleService initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to initialize CycleService: {e}")
        
        # Register placeholder for task_orchestrator (if you want to implement it later)
        if not ServiceRegistry.has_service("task_orchestrator"):
            from core.micro_factories.orchestrator_factory import OrchestratorFactory
            try:
                task_orchestrator = OrchestratorFactory.create()
                if task_orchestrator:
                    ServiceRegistry.register("task_orchestrator", task_orchestrator)
                    self.logger.info("✅ TaskOrchestrator initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ TaskOrchestrator not yet implemented: {e}")
        
        # Register placeholder for dreamscape_generator (if you want to implement it later)
        if not ServiceRegistry.has_service("dreamscape_generator"):
            try:
                # Import if you have a factory for it
                # from core.micro_factories.dreamscape_factory import DreamscapeFactory
                # dreamscape_generator = DreamscapeFactory.create()
                # ServiceRegistry.register("dreamscape_generator", dreamscape_generator)
                self.logger.info("🧩 DreamscapeGenerator not yet wired")
            except Exception as e:
                self.logger.warning(f"⚠️ DreamscapeGenerator not yet implemented: {e}")


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
    
    logger = logging.getLogger(__name__)
    logger.info("System initialized with the following services:")
    for name, service in services.items():
        status = "✅ Available" if service else "⚠️ Empty implementation"
        logger.info(f"  - {name}: {status}") 