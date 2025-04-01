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

class EpisodeGeneratorFactory:
    @staticmethod
    def create_episode_generator(
        parent_widget=None,
        prompt_manager=None,
        chat_manager=None,
        dreamscape_service=None,
        output_dir=None,
        logger_instance=None,
    ) -> Optional[DreamscapeEpisodeGenerator]:
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
            An instance of DreamscapeEpisodeGenerator.
        """
        logger = logger_instance or logging.getLogger("EpisodeGeneratorFactory")
        if DreamscapeEpisodeGenerator is None:
            logger.error("❌ DreamscapeEpisodeGenerator class not available due to import failure.")
            return None
            
        logger.info("🔧 Creating DreamscapeEpisodeGenerator via factory")
        try:
            # Match the parameters to the DreamscapeEpisodeGenerator constructor
            instance = DreamscapeEpisodeGenerator(
                parent_widget=parent_widget,
                prompt_manager=prompt_manager,
                chat_manager=chat_manager,
                dreamscape_generator=dreamscape_service,  # Rename to match constructor
                output_dir=output_dir,
                logger=logger
            )
            logger.info("✅ DreamscapeEpisodeGenerator created successfully.")
            return instance
        except Exception as e:
            logger.error(f"❌ Failed to create DreamscapeEpisodeGenerator: {e}", exc_info=True)
            return None 
