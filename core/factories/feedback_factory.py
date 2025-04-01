"""
Factory for creating Feedback Engine instances.
"""
from typing import Optional, Any
from core.services.service_registry import ServiceRegistry

class FeedbackFactory:
    """Factory for creating Feedback Engine instances."""
    
    @staticmethod
    def create(registry: ServiceRegistry) -> Optional[Any]:
        """
        Create and return a configured Feedback Engine instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured Feedback Engine instance
        """
        try:
            # Get dependencies
            logger = registry.get("logger")
            config = registry.get("config_manager")
            prompt_manager = registry.get("prompt_manager")
            recovery_engine = registry.get("recovery_engine")
            failure_hook = registry.get("agent_failure_hook")
            
            # Import here to avoid circular dependencies
            from core.feedback.feedback_engine import FeedbackEngine
            
            # Create and return the feedback engine
            feedback_engine = FeedbackEngine(
                prompt_manager=prompt_manager,
                config=config,
                logger=logger,
                recovery_engine=recovery_engine
            )
            
            # Register failure hooks if available
            if failure_hook:
                feedback_engine.register_failure_hooks(failure_hook)
            
            if logger:
                logger.info("✅ Feedback Engine created successfully")
                
            return feedback_engine
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create Feedback Engine: {e}")
            return None 