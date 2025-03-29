"""
Factory for creating FeedbackEngine instances.
Using a factory pattern to handle the creation of FeedbackEngine implementations
and ensure singleton behavior.
"""
import os
import logging
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class FeedbackEngineFactory:
    """Factory for creating FeedbackEngine instances."""
    
    @staticmethod
    def create(config_manager=None, logger_obj=None) -> Any:
        """
        Create and return a singleton FeedbackEngine instance.
        
        Args:
            config_manager: Configuration manager instance
            logger_obj: Logger instance
            
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
            
            if logger_obj:
                logger_obj.info("✅ FeedbackEngine created successfully via factory")
            else:
                logger.info("✅ FeedbackEngine created successfully via factory")
                
            return engine
            
        except Exception as e:
            if logger_obj:
                logger_obj.error(f"❌ Failed to create FeedbackEngine: {e}")
            else:
                logger.error(f"❌ Failed to create FeedbackEngine: {e}")
            return None 