"""
Service validation and health checks for Dream.OS.
"""

import logging
from typing import Dict, Any, List


class ServiceValidator:
    """Validates and monitors service health in Dream.OS."""
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize the service validator.
        
        Args:
            logger: Logger instance for validation messages
        """
        self.logger = logger
        
    def verify_services(self, services: Dict[str, Any]) -> List[str]:
        """
        Verify that essential services are available and log any issues.
        
        Args:
            services: Dictionary of service instances
            
        Returns:
            List of warning messages about service status
        """
        warnings = []
        essential_services = [
            'prompt_manager', 'chat_manager', 'response_handler',
            'memory_manager', 'discord_service'
        ]
        
        for service_name in essential_services:
            service = services.get(service_name)
            if service is None:
                msg = f"Error: Service '{service_name}' not available - services not initialized"
                self.logger.error(msg)
                warnings.append(msg)
            elif hasattr(service, '__class__') and service.__class__.__name__ == "EmptyService":
                msg = f"Warning: Service '{service_name}' is using an empty implementation"
                self.logger.warning(msg)
                warnings.append(msg)
                
        extra_deps = services.get('extra_dependencies', {})
        if not extra_deps:
            msg = "No extra dependencies provided - some functionality may be limited"
            self.logger.warning(msg)
            warnings.append(msg)
        else:
            extra_essentials = ['cycle_service', 'task_orchestrator', 'dreamscape_generator']
            for dep_name in extra_essentials:
                if dep_name not in extra_deps or extra_deps[dep_name] is None:
                    msg = f"Missing extra dependency: '{dep_name}'"
                    self.logger.warning(msg)
                    warnings.append(msg)
                    
        return warnings
        
    def check_service_health(self, services: Dict[str, Any]) -> Dict[str, bool]:
        """
        Check the health of all services.
        
        Args:
            services: Dictionary of service instances
            
        Returns:
            Dictionary mapping service names to their health status
        """
        health_status = {}
        
        for service_name, service in services.items():
            if service_name == 'extra_dependencies':
                continue
                
            # Check if service exists and is not an empty implementation
            is_healthy = (
                service is not None and
                not (hasattr(service, '__class__') and 
                     service.__class__.__name__ == "EmptyService")
            )
            
            health_status[service_name] = is_healthy
            
        return health_status 