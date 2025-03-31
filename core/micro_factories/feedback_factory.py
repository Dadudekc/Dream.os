"""
Factory for creating FeedbackEngine instances.
Using a micro-factory pattern with service registry integration.
"""
import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class FeedbackFactory:
    """Micro-factory for creating FeedbackEngine instances."""
    
    @staticmethod
    def create() -> Any:
        """
        Create and return a singleton FeedbackEngine instance with
        dependencies injected from the service registry.
        
        Returns:
            A FeedbackEngine instance
        """
        try:
            # Import here to avoid circular dependencies
            from core.services.service_registry import ServiceRegistry
            from core.chat_engine.feedback_engine import FeedbackEngine
            
            # Get dependencies from registry
            config_manager = ServiceRegistry.get("config_manager")
            
            # Get memory file path from config if available
            memory_file = "memory/persistent_memory.json"
            feedback_log_file = "memory/feedback_log.json"
            
            if config_manager:
                memory_file = config_manager.get("memory_file", memory_file)
                feedback_log_file = config_manager.get("feedback_log_file", feedback_log_file)
                
            # Ensure paths are strings
            if not isinstance(memory_file, (str, os.PathLike)):
                memory_file = str(memory_file)
            if not isinstance(feedback_log_file, (str, os.PathLike)):
                feedback_log_file = str(feedback_log_file)
                
            # Ensure directories exist
            os.makedirs(os.path.dirname(memory_file), exist_ok=True)
            os.makedirs(os.path.dirname(feedback_log_file), exist_ok=True)
            
            # Create the instance (singleton pattern in FeedbackEngine ensures only one exists)
            engine = FeedbackEngine(
                memory_file=memory_file,
                feedback_log_file=feedback_log_file
            )
            
            logger.info("✅ FeedbackEngine created successfully via factory")
            return engine
            
        except Exception as e:
            logger.error(f"❌ Failed to create FeedbackEngine: {e}")
            return None
            
    @staticmethod
    def create_with_explicit_deps(config_manager=None) -> Any:
        """
        Create and return a FeedbackEngine instance with explicitly provided dependencies.
        
        Args:
            config_manager: Configuration manager instance
            
        Returns:
            A FeedbackEngine instance
        """
        try:
            # Import here to avoid circular dependencies
            from core.chat_engine.feedback_engine import FeedbackEngine
            
            # Get memory file path from config if available
            memory_file = "memory/persistent_memory.json"
            feedback_log_file = "memory/feedback_log.json"
            
            if config_manager:
                memory_file = config_manager.get("memory_file", memory_file)
                feedback_log_file = config_manager.get("feedback_log_file", feedback_log_file)
                
            # Create the instance
            engine = FeedbackEngine(
                memory_file=memory_file,
                feedback_log_file=feedback_log_file
            )
            
            logger.info("✅ FeedbackEngine created successfully with explicit dependencies")
            return engine
            
        except Exception as e:
            logger.error(f"❌ Failed to create FeedbackEngine with explicit dependencies: {e}")
            return None 