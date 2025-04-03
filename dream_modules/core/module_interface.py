"""Base module interface for all Dream.OS modules.

This module defines the interface that all modules must implement
to be compatible with the Dream.OS system.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ModuleInterface(ABC):
    """Base interface that all Dream.OS modules must implement."""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the module with the given configuration.
        
        Args:
            config: Configuration dictionary for the module
            
        Returns:
            True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """Perform cleanup and shutdown procedures.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the module.
        
        Returns:
            The module name as a string
        """
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version of the module.
        
        Returns:
            The module version as a string
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of the module.
        
        Returns:
            The module description as a string
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return the status of the module.
        
        Returns:
            A dictionary containing status information
        """
        pass
    

class ServiceInterface(ModuleInterface):
    """Interface for modules that provide services to other modules."""
    
    @abstractmethod
    def register_dependency(self, service_name: str, service: Any) -> bool:
        """Register a dependency for this service.
        
        Args:
            service_name: The name of the service to register
            service: The service instance
            
        Returns:
            True if registration was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_service_interface(self) -> Dict[str, Any]:
        """Get the public interface this service provides.
        
        Returns:
            A dictionary of public methods and properties
        """
        pass


class ConfigurableModule(ModuleInterface):
    """Interface for modules that support runtime configuration changes."""
    
    @abstractmethod
    def update_config(self, config: Dict[str, Any]) -> bool:
        """Update the module configuration at runtime.
        
        Args:
            config: The new configuration to apply
            
        Returns:
            True if configuration was updated successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get the current module configuration.
        
        Returns:
            The current configuration as a dictionary
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate a configuration dictionary.
        
        Args:
            config: The configuration to validate
            
        Returns:
            True if the configuration is valid, False otherwise
        """
        pass 