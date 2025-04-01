# core/micro_factories/episode_generator_factory.py

# Import location seems different from previous factory
# Assuming this is the correct path based on your snippet
try:
    from core.episode_generation.dreamscape_episode_generator import DreamscapeEpisodeGenerator
except ImportError:
    # Fallback if the path is different
    try:
        from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator
    except ImportError as e:
        logging.error(f"Failed to import DreamscapeEpisodeGenerator from expected locations: {e}")
        DreamscapeEpisodeGenerator = None

import logging
from typing import Optional
from core.ChatManager import ChatManager
from core.response_handler import PromptResponseHandler
from core.services.discord_service import DiscordManager
from core.services.dreamscape.engine import DreamscapeGenerationService
from core.dependency_manager import DependencyManager

class EpisodeGeneratorFactory:
    @staticmethod
    def create_episode_generator(
        parent_widget=None,
        prompt_manager=None,
        chat_manager=None,
        dreamscape_service=None,
        output_dir=None,
        logger_instance=None,
    ) -> Optional[DreamscapeGenerationService]:
        """
        Factory method to create and configure a DreamscapeEpisodeGenerator.
        
        Args:
            parent_widget: The parent tab/widget (DreamscapeGenerationTab).
            prompt_manager: The prompt manager service.
            chat_manager: The chat manager service.
            dreamscape_service: The DreamscapeGenerationService instance.
            output_dir: The directory for episode outputs.
            logger_instance: Logger instance for the EpisodeGenerator.
        
        Returns:
            An instance of DreamscapeGenerationService.
        """
        logger = logger_instance or logging.getLogger("EpisodeGeneratorFactory")
        if DreamscapeGenerationService is None:
            logger.error("❌ DreamscapeGenerationService class not available due to import failure.")
            return None
            
        logger.info("🔧 Creating DreamscapeGenerationService via factory")
        try:
            # Match the parameters to the DreamscapeGenerationService constructor
            response_handler = PromptResponseHandler(prompt_manager)
            discord_manager = DiscordManager()
            generator = DreamscapeGenerationService(
                chat_manager=chat_manager,
                response_handler=response_handler,
                discord_manager=discord_manager
            )
            logger.info("✅ DreamscapeGenerationService created successfully.")
            return generator
        except Exception as e:
            logger.error(f"❌ Failed to create DreamscapeGenerationService: {e}", exc_info=True)
            return None 
