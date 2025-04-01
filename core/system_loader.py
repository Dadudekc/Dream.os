#!/usr/bin/env python3
"""
SystemLoader - Centralized Service Initialization System
=======================================================

This module provides a centralized system for initializing and wiring all
Dream.OS services with proper dependency injection and sequencing using
the unified factory system.

It ensures:
- Services are initialized in the correct dependency order
- Configuration is properly extracted and passed
- Factories are used for proper dependency injection
- Singleton services are properly maintained
- Proper fallbacks for missing or failing services
"""

import logging
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

# Core service registry import
from core.services.service_registry import ServiceRegistry

# Base factory imports
from core.utils.path_manager import PathManager
from core.config.config_manager import ConfigManager

# Import the factory registry
from core.factories import FactoryRegistry

# Utility imports
from core.memory.utils import fix_memory_file

# Import services
from core.services.cursor_ui_service import CursorUIServiceFactory

# Configure the logger at module level
logger = logging.getLogger(__name__)


class SystemLoader:
    """Manages system initialization and service loading."""
    
    def __init__(self):
        """Initialize the system loader."""
        self.registry = ServiceRegistry.get_instance()
        self.factory_registry = FactoryRegistry.get_instance()
        
    def boot(self) -> bool:
        """
        Boot the system by initializing all required services.
        
        Returns:
            bool: True if boot successful, False otherwise
        """
        try:
            self._initialize_services()
            return True
        except Exception as e:
            logger.error(f"System boot failed: {e}")
            return False
            
    def _initialize_services(self) -> None:
        """Initialize core services using factories."""
        try:
            # Initialize core services
            for service_name, factory in self.factory_registry.get_factories().items():
                logger.info(f"Initializing service: {service_name}")
                try:
                    instance = factory.create(self.registry)
                    if instance:
                        self.registry.register(service_name, instance)
                        logger.info(f"Service '{service_name}' initialized successfully")
                    else:
                        logger.error(f"Failed to create service: {service_name}")
                except Exception as e:
                    logger.error(f"Error initializing {service_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise


# Convenience function to create and boot the system
def initialize_system(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Initialize and boot the entire system with a single function call.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Dict of initialized services
    """
    loader = SystemLoader()
    if loader.boot():
        return ServiceRegistry.get_all_services()
    else:
        return {}


class DreamscapeSystemLoader:
    """
    System loader that handles registration and initialization of services.
    
    This class implements a simple service registry pattern that allows different 
    components of the system to access shared services through dependency injection.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the system loader.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.services = {}
        self.config = {}
        
        # Load configuration if provided
        if config_path:
            self.load_config(config_path)
        
        logger.info("DreamscapeSystemLoader initialized")
    
    def load_config(self, config_path: str):
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to configuration file
        """
        if not os.path.exists(config_path):
            logger.warning(f"Configuration file not found: {config_path}")
            return
        
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    def register_service(self, name: str, service: Any):
        """
        Register a service with the system loader.
        
        Args:
            name: Service name
            service: Service instance
        """
        self.services[name] = service
        logger.info(f"Service registered: {name}")
    
    def get_service(self, name: str) -> Optional[Any]:
        """
        Get a service by name.
        
        Args:
            name: Service name
            
        Returns:
            Service instance if found, None otherwise
        """
        return self.services.get(name)
    
    def unregister_service(self, name: str):
        """
        Unregister a service.
        
        Args:
            name: Service name
        """
        if name in self.services:
            del self.services[name]
            logger.info(f"Service unregistered: {name}")
    
    def initialize_cursor_ui_service(self, 
                                   browser_path: Optional[str] = None,
                                   debug_mode: bool = False) -> Any:
        """
        Initialize and register the CursorUIService.
        
        Args:
            browser_path: Path to browser executable
            debug_mode: Whether to enable debug mode
            
        Returns:
            Initialized CursorUIService
        """
        # Get settings from config if not provided
        if browser_path is None and "browser_path" in self.config.get("cursor_ui", {}):
            browser_path = self.config.get("cursor_ui", {}).get("browser_path")
        
        if not debug_mode and self.config.get("cursor_ui", {}).get("debug_mode", False):
            debug_mode = True
        
        # Create service using factory
        service = CursorUIServiceFactory.create(
            browser_path=browser_path,
            debug_mode=debug_mode,
            service_registry=self.services
        )
        
        # Register the service
        self.register_service("cursor_ui_service", service)
        
        return service
    
    def initialize_service(self, service_name: str, **kwargs) -> Optional[Any]:
        """
        Initialize and register a service by name.
        
        Args:
            service_name: Name of the service to initialize
            **kwargs: Arguments to pass to the initialization method
            
        Returns:
            Initialized service or None if service type is unknown
        """
        if service_name == "cursor_ui_service":
            return self.initialize_cursor_ui_service(**kwargs)
        # Add additional service initializers here
        else:
            logger.warning(f"Unknown service type: {service_name}")
            return None
    
    def initialize_all_services(self):
        """
        Initialize all services defined in the configuration.
        """
        if "services" in self.config:
            for service_def in self.config.get("services", []):
                service_type = service_def.get("type")
                service_args = service_def.get("args", {})
                
                if service_type:
                    self.initialize_service(service_type, **service_args)
    
    def get_registered_services(self) -> List[str]:
        """
        Get a list of all registered service names.
        
        Returns:
            List of service names
        """
        return list(self.services.keys())
    
    def shutdown(self):
        """
        Shutdown and cleanup all services.
        """
        # Call any cleanup methods on services that support it
        for name, service in self.services.items():
            if hasattr(service, "shutdown") and callable(service.shutdown):
                try:
                    service.shutdown()
                    logger.info(f"Service shutdown: {name}")
                except Exception as e:
                    logger.error(f"Error shutting down service {name}: {e}")
        
        # Clear all services
        self.services.clear()
        logger.info("All services unregistered")


# Singleton instance
_system_loader = None

def get_system_loader(config_path: Optional[str] = None) -> DreamscapeSystemLoader:
    """
    Get the singleton system loader instance.
    
    Args:
        config_path: Path to configuration file (only used if creating new instance)
        
    Returns:
        DreamscapeSystemLoader instance
    """
    global _system_loader
    if _system_loader is None:
        _system_loader = DreamscapeSystemLoader(config_path)
    return _system_loader


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

    # Create and initialize system loader
    system_loader = get_system_loader()
    
    # Initialize UI service
    ui_service = system_loader.initialize_cursor_ui_service(debug_mode=True)
    
    # Get service
    retrieved_service = system_loader.get_service("cursor_ui_service")
    
    # List registered services
    services = system_loader.get_registered_services()
    print(f"Registered services: {services}")
    
    # Shutdown
    system_loader.shutdown() 
