# core/micro_factories/chat_factory.py
import logging
from typing import Optional
from config.ConfigManager import ConfigManager
from interfaces.chat_manager import IChatManager

def create_chat_manager(config_manager: ConfigManager, logger: Optional[logging.Logger] = None, prompt_manager=None) -> IChatManager:
    """
    Factory method to create a fully initialized ChatManager instance.
    
    Args:
        config_manager: Configuration manager instance
        logger: Optional logger instance
        prompt_manager: Optional prompt manager instance
    
    Returns:
        An instance implementing IChatManager
    """
    try:
        from core.ChatManager import ChatManager  # Late import to break circular dependency
        chat_manager = ChatManager(config=config_manager, logger=logger, prompt_manager=prompt_manager)
        if logger:
            logger.info("ChatManager initialized successfully")
        return chat_manager
    except Exception as e:
        if logger:
            logger.error(f"Failed to create ChatManager: {e}")
        raise
