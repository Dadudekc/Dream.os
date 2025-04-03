"""Service container for dependency injection.

This module provides a service container for dependency injection,
allowing modules to register and retrieve services.
"""
from typing import Dict, Any, Optional, Type, Callable
import logging


class ServiceContainer:
    """Container for managing services and dependencies.
    
    This class provides methods for registering and retrieving services,
    supporting dependency injection patterns.
    """
    
    def __init__(self):
        """Initialize the service container."""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._logger = logging.getLogger(__name__)
    
    def register(self, service_name: str, service: Any) -> bool:
        """Register a service in the container.
        
        Args:
            service_name: The name to register the service under
            service: The service instance
            
        Returns:
            True if registration was successful, False if the service already exists
        """
        if service_name in self._services:
            self._logger.warning(f"Service '{service_name}' already registered")
            return False
        
        self._services[service_name] = service
        self._logger.debug(f"Registered service '{service_name}'")
        return True
    
    def register_factory(self, service_name: str, factory: Callable[[], Any]) -> bool:
        """Register a factory function for lazy service creation.
        
        Args:
            service_name: The name to register the factory under
            factory: A callable that creates and returns the service instance
            
        Returns:
            True if registration was successful, False if the factory already exists
        """
        if service_name in self._factories:
            self._logger.warning(f"Factory for '{service_name}' already registered")
            return False
        
        self._factories[service_name] = factory
        self._logger.debug(f"Registered factory for '{service_name}'")
        return True
    
    def get(self, service_name: str) -> Optional[Any]:
        """Get a service from the container.
        
        Args:
            service_name: The name of the service to retrieve
            
        Returns:
            The service instance, or None if not found
        """
        # Check if service is already instantiated
        if service_name in self._services:
            return self._services[service_name]
        
        # Check if we have a factory for this service
        if service_name in self._factories:
            try:
                # Create service using factory
                service = self._factories[service_name]()
                # Store for future use
                self._services[service_name] = service
                return service
            except Exception as e:
                self._logger.error(f"Error creating service '{service_name}': {e}")
                return None
        
        self._logger.warning(f"Service '{service_name}' not found")
        return None
    
    def has(self, service_name: str) -> bool:
        """Check if a service is registered.
        
        Args:
            service_name: The name of the service to check
            
        Returns:
            True if the service is registered, False otherwise
        """
        return service_name in self._services or service_name in self._factories
    
    def remove(self, service_name: str) -> bool:
        """Remove a service from the container.
        
        Args:
            service_name: The name of the service to remove
            
        Returns:
            True if the service was removed, False if it wasn't registered
        """
        if service_name in self._services:
            del self._services[service_name]
            self._logger.debug(f"Removed service '{service_name}'")
            return True
        
        if service_name in self._factories:
            del self._factories[service_name]
            self._logger.debug(f"Removed factory for '{service_name}'")
            return True
        
        self._logger.warning(f"Cannot remove non-existent service '{service_name}'")
        return False
    
    def clear(self) -> None:
        """Clear all services and factories from the container."""
        self._services.clear()
        self._factories.clear()
        self._logger.debug("Cleared all services and factories")


# Global instance for singleton access
_container = ServiceContainer()

def get_container() -> ServiceContainer:
    """Get the global service container instance.
    
    Returns:
        The global ServiceContainer instance
    """
    return _container 