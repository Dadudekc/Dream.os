"""
Core Factory System

This module provides a unified factory system for creating service instances
with proper dependency injection and configuration.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
import logging
from threading import Lock

T = TypeVar('T')

logger = logging.getLogger(__name__)

class BaseFactory(ABC):
    """Base factory class that all service factories must inherit from."""
    
    @abstractmethod
    def create(self, registry: Any) -> Optional[Any]:
        """
        Create and return a configured service instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A configured service instance or None if creation fails
        """
        pass

    def get_dependencies(self, registry: Any) -> Dict[str, Any]:
        """
        Get common dependencies from the registry.
        
        Args:
            registry: The service registry
            
        Returns:
            Dictionary of common dependencies
        """
        return {
            "logger": registry.get("logger"),
            "config": registry.get("config_manager"),
            "path_manager": registry.get("path_manager"),
            "service_registry": registry
        }

class FactoryRegistry:
    """
    Central registry for managing service factories.
    """
    _instance = None
    _lock = Lock()
    _factories: Dict[str, Any] = {}
    
    def __init__(self):
        """Initialize the factory registry."""
        if not hasattr(self, '_factories'):
            self._factories = {}
            
    @classmethod
    def get_instance(cls) -> 'FactoryRegistry':
        """Get the singleton instance of the registry."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
        
    def register_factory(self, name: str, factory: Any) -> None:
        """
        Register a factory.
        
        Args:
            name: Factory name
            factory: Factory instance
        """
        if name in self._factories:
            logger.warning(f"Factory '{name}' is already registered. Overwriting.")
        self._factories[name] = factory
        logger.debug(f"Factory '{name}' registered successfully.")
        
    def get_factory(self, name: str) -> Optional[Any]:
        """
        Get a factory instance.
        
        Args:
            name: Factory name
            
        Returns:
            Factory instance or None if not found
        """
        if name not in self._factories:
            logger.warning(f"Factory '{name}' not found.")
            return None
        return self._factories[name]
        
    def get_factories(self) -> Dict[str, Any]:
        """
        Get all registered factories.
        
        Returns:
            Dictionary of factory name to instance
        """
        return self._factories.copy()
        
    def reset(self) -> None:
        """Reset the registry, clearing all factories."""
        self._factories.clear()
        logger.info("Factory registry reset.")

    def create_service(self, name: str, registry: Any) -> Optional[Any]:
        """
        Create a service instance using its registered factory.
        
        Args:
            name: Service name
            registry: Service registry
            
        Returns:
            Created service instance or None
        """
        factory = self.get_factory(name)
        if factory:
            return factory.create(registry)
        return None 