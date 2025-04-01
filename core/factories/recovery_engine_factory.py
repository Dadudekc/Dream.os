"""
Factory for creating RecoveryEngine instances.
"""

import logging
from typing import Optional, Any
from core.services.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

class RecoveryEngineFactory:
    """Factory for creating RecoveryEngine instances."""
    
    @staticmethod
    def create(registry: ServiceRegistry) -> Optional[Any]:
        """
        Create and return a configured RecoveryEngine instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured RecoveryEngine instance
        """
        try:
            # Get dependencies
            cursor_session = registry.get("cursor_session_manager")
            metrics_service = registry.get("metrics_service")
            config = registry.get("config_manager")
            logger_obj = registry.get("logger")
            
            # Import here to avoid circular dependencies
            from core.recovery.recovery_engine import RecoveryEngine
            
            # Get configuration options
            config_path = "config/recovery_strategies.json"
            learning_rate = 0.1
            exploration_rate = 0.2
            auto_tuning_interval = 3600  # 1 hour
            
            if config:
                recovery_config = config.get("recovery", {})
                config_path = recovery_config.get("strategies_config", config_path)
                learning_rate = recovery_config.get("learning_rate", learning_rate)
                exploration_rate = recovery_config.get("exploration_rate", exploration_rate)
                auto_tuning_interval = recovery_config.get("auto_tuning_interval", auto_tuning_interval)
            
            # Create and return the engine
            engine = RecoveryEngine(
                cursor_session=cursor_session,
                metrics_service=metrics_service,
                config_path=config_path,
                learning_rate=learning_rate,
                exploration_rate=exploration_rate
            )
            
            # Start auto-tuning if enabled
            if auto_tuning_interval > 0:
                engine.start_auto_tuning_loop(interval_seconds=auto_tuning_interval)
            
            if logger_obj:
                logger_obj.info("✅ RecoveryEngine created successfully")
                
            return engine
            
        except Exception as e:
            if logger_obj:
                logger_obj.error(f"❌ Failed to create RecoveryEngine: {e}")
            return None 