# File: D:\overnight_scripts\chat_mate\interfaces\pyqt\tabs\dreamscape_generation\EpisodeGenerator.py

import logging
from typing import Any, Optional
from core.dreamscape.ContextMemoryManager import ContextMemoryManager
from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator
import asyncio

class EpisodeGenerator:
    """
    UI adapter for the DreamscapeEpisodeGenerator.
    Handles UI-specific episode generation operations and state management.
    """

    def __init__(self, parent_widget: Any, logger: Optional[logging.Logger] = None,
                 chat_manager: Any = None, config_manager: Any = None):
        """
        Initialize the UI Episode Generator adapter.
        
        Args:
            parent_widget: The parent widget (for UI context)
            logger: Logger instance for logging events
            chat_manager: Chat manager service
            config_manager: Configuration manager to retrieve settings
        """
        self.parent = parent_widget
        self.logger = logger or logging.getLogger(__name__)
        self.chat_manager = chat_manager
        self.config_manager = config_manager
        
        # Get output directory from config
        self.output_dir = self.config_manager.get("dreamscape_output_dir", "outputs/dreamscape")
        
        # Initialize core components
        self.context_manager = ContextMemoryManager(
            output_dir=self.output_dir,
            logger=self.logger
        )
        
        # Initialize core generator with async support
        self.core_generator = DreamscapeEpisodeGenerator(
            chat_manager=self.chat_manager,
            context_manager=self.context_manager,
            output_dir=self.output_dir,
            logger=self.logger,
            parent_widget=parent_widget
        )

    async def generate_episodes(self, prompt_text: str, chat_url: str, model: str,
                              process_all: bool = False, reverse_order: bool = False) -> bool:
        """
        Generate dreamscape episodes using the core generator.
        
        Args:
            prompt_text: The prompt provided by the user
            chat_url: The URL of the chat to process (or None if processing all)
            model: Selected model identifier
            process_all: Whether to process all chats
            reverse_order: Whether to reverse the order of processing
        
        Returns:
            True if episodes are generated successfully; False otherwise
        """
        try:
            # Execute the core generator's method
            result = await self.core_generator.generate_dreamscape_episodes(
                prompt_text=prompt_text,
                chat_url=chat_url,
                model=model,
                process_all=process_all,
                reverse_order=reverse_order
            )
            
            return result

        except Exception as e:
            self.logger.error(f"Error generating episodes: {str(e)}")
            return False
            
    def get_generation_status(self) -> dict:
        """Get the current status of episode generation."""
        return self.core_generator.get_status()
        
    def cancel_generation(self) -> bool:
        """Cancel the current episode generation process."""
        return self.core_generator.cancel_generation()
