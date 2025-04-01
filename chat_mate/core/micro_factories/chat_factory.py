# core/micro_factories/chat_factory.py
import logging
from typing import Optional
from core.config.config_manager import ConfigManager

def create_chat_manager(config_manager: ConfigManager, logger: Optional[logging.Logger] = None, prompt_manager=None):
    """
    Factory method to create a fully initialized chat manager instance.
    
    Args:
        config_manager: Configuration manager instance
        logger: Optional logger instance
        prompt_manager: Optional prompt manager instance
    
    Returns:
        A ChatEngineManager instance
    """
    try:
        # Import here to avoid circular import
        from core.chat_engine.chat_engine_manager import ChatEngineManager
        
        chat_manager = ChatEngineManager(
            config=config_manager,
            logger=logger,
            prompt_manager=prompt_manager
        )
        if logger:
            logger.info("ChatEngineManager initialized successfully")
        return chat_manager
    except Exception as e:
        if logger:
            logger.error(f"Failed to create ChatEngineManager: {e}")
        raise
