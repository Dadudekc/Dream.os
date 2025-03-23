from typing import Dict, Any, Optional
from core.ConfigManager import ConfigManager
from core.AletheiaPromptManager import AletheiaPromptManager
from core.cycle.PromptResponseHandler import PromptResponseHandler
from core.cycle.DiscordQueueProcessor import DiscordQueueProcessor
from core.logging.CompositeLogger import CompositeLogger

class CycleExecutionService:
    """Handles prompt cycle execution and orchestration."""

    def __init__(self, config_manager: ConfigManager, logger: CompositeLogger):
        self.config_manager = config_manager
        self.logger = logger
        self.prompt_manager = AletheiaPromptManager(config_manager, logger)
        self.response_handler = PromptResponseHandler(config_manager, logger)
        self.discord_queue_processor = DiscordQueueProcessor(config_manager, logger)

    def run_cycle(self, payload: Dict[str, Any], cycle_type: str = "single") -> Dict[str, Any]:
        """
        Execute a single or multi-cycle prompt session.

        Args:
            payload: Dict of cycle parameters.
            cycle_type: 'single' or 'multi'.

        Returns:
            Response from PromptResponseHandler.
        """
        self.logger.log(f"Starting {cycle_type} cycle...", domain="CycleExecutionService")
        raw_responses = self.prompt_manager.execute(payload, cycle_type)

        processed_response = self.response_handler.process_response(raw_responses)
        self.discord_queue_processor.queue_response(processed_response)

        return processed_response
