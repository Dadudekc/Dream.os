class DynamicContainer:
    """
    A dynamic service container that supports lazy loading and dependency injection.
    """
    
    def __init__(self, logger=None):
        self.services = {}
        self.logger = logger or logging.getLogger("DynamicContainer")
        
    def register(self, name: str, service: Any) -> None:
        """Register a service with the container."""
        self.services[name] = service
        
    def get(self, name: str) -> Any:
        """Get a service from the container."""
        return self.services.get(name)
        
    def has(self, name: str) -> bool:
        """Check if a service exists in the container."""
        return name in self.services

    def _create_empty_service(self, name: str) -> Any:
        """
        Create an empty service implementation for graceful fallback.
        
        Args:
            name (str): Name of the service to create
            
        Returns:
            Any: An empty service object with basic attributes
        """
        class EmptyService:
            def __init__(self):
                self.name = name
                self.available = False
                self.status = "not initialized"
                
            def __getattr__(self, attr):
                def method(*args, **kwargs):
                    if self.logger:
                        self.logger.warning(
                            f"Call to unavailable service '{self.name}.{attr}()'. Service not initialized."
                        )
                    return None
                return method
                
        service = EmptyService()
        service.logger = self.logger
        return service 