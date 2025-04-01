"""
Factory for creating AgentFailureHook instances.
"""

import logging
from typing import Optional, Any
from core.services.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

class AgentFailureHookFactory:
    """Factory for creating AgentFailureHook instances."""
    
    @staticmethod
    def create(registry: ServiceRegistry) -> Optional[Any]:
        """
        Create and return a configured AgentFailureHook instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured AgentFailureHook instance
        """
        try:
            # Get dependencies
            recovery_engine = registry.get("recovery_engine")
            metrics_service = registry.get("metrics_service")
            memory_manager = registry.get("memory_manager")
            config = registry.get("config_manager")
            logger_obj = registry.get("logger")
            
            # Import here to avoid circular dependencies
            from core.recovery.agent_failure_hooks import AgentFailureHook
            
            # Get config path from config if available
            config_path = "config/failure_hooks.json"
            if config:
                config_path = config.get("failure_hooks_config", config_path)
            
            # Create and return the hook
            hook = AgentFailureHook(
                recovery_engine=recovery_engine,
                metrics_service=metrics_service,
                memory_manager=memory_manager,
                config_path=config_path
            )
            
            if logger_obj:
                logger_obj.info("✅ AgentFailureHook created successfully")
                
            return hook
            
        except Exception as e:
            if logger_obj:
                logger_obj.error(f"❌ Failed to create AgentFailureHook: {e}")
            return None 