from typing import Dict, Any, Optional
from config.ConfigManager import ConfigManager
from core.AletheiaPromptManager import AletheiaPromptManager
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.logging.CompositeLogger import CompositeLogger

class CycleExecutionService:
    """Handles prompt cycle execution and orchestration in a scalable way using dependency injection."""

    def __init__(
        self,
        prompt_manager: AletheiaPromptManager,
        config_manager: ConfigManager,
        logger: CompositeLogger,
        chat_manager: Optional[Any] = None,
        response_handler: Optional[PromptResponseHandler] = None,
        memory_manager: Optional[Any] = None,
        discord_manager: Optional[Any] = None,
    ):
        self.prompt_manager = prompt_manager
        self.chat_manager = chat_manager
        self.config_manager = config_manager
        self.logger = logger

        # If no response handler is provided, create one with the provided config and logger.
        self.response_handler = response_handler or PromptResponseHandler(config_manager, logger)
        self.memory_manager = memory_manager
        self.discord_manager = discord_manager

        self.discord_queue_processor = DiscordQueueProcessor(config_manager, logger)

    def run_cycle(self, payload: Dict[str, Any], cycle_type: str = "single") -> Dict[str, Any]:
        """
        Execute a single or multi-cycle prompt session.

        Args:
            payload: Dict of cycle parameters.
            cycle_type: 'single' or 'multi'.

        Returns:
            Processed response from PromptResponseHandler.
        """
        if not self.prompt_manager:
            raise ValueError("Prompt manager not initialized")
            
        # Execute the cycle using the prompt manager.
        raw_responses = self.prompt_manager.execute(payload, cycle_type)
        
        # Process the responses using the response handler.
        processed_response = self.response_handler.process_response(raw_responses)
        
        # If a discord manager is present, enqueue the response for dispatch.
        if self.discord_manager:
            self.discord_queue_processor.queue_response(processed_response)

        return processed_response
