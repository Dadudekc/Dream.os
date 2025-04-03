"""
Empty service implementation for graceful fallback when a service is unavailable.
"""

import logging


class EmptyService:
    """
    Empty service implementation that logs warnings when methods are called.
    Used for graceful degradation when a service is unavailable.
    """
    
    def __init__(self, name: str):
        """
        Initialize the empty service.
        
        Args:
            name: Name of the service this instance is standing in for
        """
        self.service_name = name
        self.logger = logging.getLogger(f"EmptyService.{name}")
        
    def __getattr__(self, attr_name: str):
        """
        Catch all attribute access and return a warning method.
        
        Args:
            attr_name: Name of the attribute being accessed
            
        Returns:
            A method that logs a warning and returns None
        """
        def method(*args, **kwargs):
            self.logger.warning(
                f"Call to unavailable service '{self.service_name}.{attr_name}()'. Service not initialized."
            )
            return None
        return method 