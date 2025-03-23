from typing import Dict, Any, Optional
from core.ConfigManager import ConfigManager
from core.AletheiaPromptManager import AletheiaPromptManager
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.logging.CompositeLogger import CompositeLogger

class CycleExecutionService:
    """Handles prompt cycle execution and orchestration."""

    def __init__(self, prompt_manager=None, chat_manager=None, response_handler=None, memory_manager=None, discord_manager=None):
        self.prompt_manager = prompt_manager
        self.chat_manager = chat_manager
        self.response_handler = response_handler or PromptResponseHandler()
        self.memory_manager = memory_manager
        self.discord_manager = discord_manager
        self.discord_queue_processor = DiscordQueueProcessor()

    def run_cycle(self, payload: Dict[str, Any], cycle_type: str = "single") -> Dict[str, Any]:
        """
        Execute a single or multi-cycle prompt session.

        Args:
            payload: Dict of cycle parameters.
            cycle_type: 'single' or 'multi'.

        Returns:
            Response from PromptResponseHandler.
        """
        if not self.prompt_manager:
            raise ValueError("Prompt manager not initialized")
            
        raw_responses = self.prompt_manager.execute(payload, cycle_type)
        processed_response = self.response_handler.process_response(raw_responses)
        
        if self.discord_manager:
            self.discord_queue_processor.queue_response(processed_response)

        return processed_response
