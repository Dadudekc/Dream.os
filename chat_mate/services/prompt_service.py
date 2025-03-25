from PyQt5.QtCore import QObject, pyqtSignal
import logging
import asyncio
from typing import List, Dict, Any
from core.PromptCycleOrchestrator import PromptCycleOrchestrator
from core.DiscordBatchDispatcher import DiscordBatchDispatcher
from core.ReinforcementEvaluator import ReinforcementEvaluator
from core.DriverSessionManager import DriverSessionManager
from services.config_service import ConfigService

class PromptService(QObject):
    """
    Service for managing and executing prompts.
    Coordinates between different components for prompt execution,
    reinforcement learning, and Discord integration.
    """
    
    log_message = pyqtSignal(str)
    
    def __init__(self, config_service: ConfigService):
        """
        Initialize the PromptService.
        
        :param config_service: The configuration service instance
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_service = config_service
        
        # Initialize components
        self.orchestrator = PromptCycleOrchestrator(config_service)
        self.discord_dispatcher = DiscordBatchDispatcher(config_service)
        self.evaluator = ReinforcementEvaluator(config_service)
        self.driver_manager = DriverSessionManager(config_service)
        
        # Start Discord dispatcher
        self.discord_dispatcher.start()

        # Caching available prompts for optimization
        self.prompt_cache = {}

        self.logger.info("PromptService initialized successfully.")

    def initialize_chat_manager(self, excluded_chats: List[str], model: str, headless: bool = False) -> None:
        """
        Initialize or reinitialize the chat manager.
        
        :param excluded_chats: List of chat titles to exclude
        :param model: The model to use for chat interactions
        :param headless: Whether to run in headless mode
        """
        self.orchestrator.initialize_chat_manager(excluded_chats, model, headless)

    async def execute_prompt_async(self, prompt_text: str, new_chat: bool = False) -> List[str]:
        """
        Execute a prompt asynchronously and return responses.
        
        :param prompt_text: The prompt text to execute
        :param new_chat: Whether to create a new chat session
        :return: List of responses
        """
        if not prompt_text:
            self.log_message.emit("No prompt text provided.")
            return []

        try:
            # Execute prompt through orchestrator
            responses = await self.orchestrator.execute_single_cycle_async(prompt_text, new_chat)
            
            # Evaluate and log responses
            for response in responses:
                evaluation = self.evaluator.evaluate_response(response, prompt_text)
                self.log_message.emit(f"Response evaluation: {evaluation['feedback']}")

                # Queue feedback for Discord
                if self.config_service.get('DISCORD_FEEDBACK_ENABLED', False):
                    await self.discord_dispatcher.queue_message_async(
                        self.config_service.get('DISCORD_CHANNEL_ID'),
                        f"Feedback for prompt: {evaluation['feedback']}"
                    )

            return responses
        
        except Exception as e:
            self.logger.error(f"Error executing prompt: {str(e)}", exc_info=True)
            self.log_message.emit(f"Error executing prompt: {str(e)}")
            return []

    async def execute_multi_prompt_async(self, prompts: List[str], reverse_order: bool = False) -> Dict[str, List[str]]:
        """
        Execute multiple prompts asynchronously across multiple chats.
        
        :param prompts: List of prompts to execute
        :param reverse_order: Whether to execute in reverse order
        :return: Dictionary mapping chat titles to their responses
        """
        if not prompts:
            self.log_message.emit("No prompts provided.")
            return {}

        try:
            # Execute prompts through orchestrator
            results = await self.orchestrator.execute_multi_cycle_async(prompts, reverse_order)
            
            # Evaluate responses for each chat
            for chat_title, responses in results.items():
                for response in responses:
                    evaluation = self.evaluator.evaluate_response(response, prompts[0])
                    self.log_message.emit(f"Chat {chat_title} response evaluation: {evaluation['feedback']}")

                    # Queue feedback for Discord
                    if self.config_service.get('DISCORD_FEEDBACK_ENABLED', False):
                        await self.discord_dispatcher.queue_message_async(
                            self.config_service.get('DISCORD_CHANNEL_ID'),
                            f"Chat {chat_title} feedback: {evaluation['feedback']}"
                        )

            return results

        except Exception as e:
            self.logger.error(f"Error executing multi-prompt: {str(e)}", exc_info=True)
            self.log_message.emit(f"Error executing multi-prompt: {str(e)}")
            return {}

    def get_prompt_insights(self, prompt_text: str) -> Dict[str, Any]:
        """
        Get insights for a specific prompt.
        
        :param prompt_text: The prompt to get insights for
        :return: Dictionary containing prompt insights
        """
        return self.evaluator.get_prompt_insights(prompt_text)

    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the memory data.
        
        :return: Dictionary containing memory summary
        """
        return self.evaluator.get_memory_summary()

    def save_prompt(self, prompt_type: str, prompt_text: str) -> bool:
        """
        Save a prompt.
        
        :param prompt_type: The type of prompt
        :param prompt_text: The prompt text to save
        :return: True if successful, False otherwise
        """
        success = self.orchestrator.save_prompt(prompt_type, prompt_text)
        if success:
            self.prompt_cache[prompt_type] = prompt_text  # Cache update
        return success

    def reset_prompts(self) -> bool:
        """
        Reset prompts to defaults.
        
        :return: True if successful, False otherwise
        """
        return self.orchestrator.reset_prompts()

    def get_available_prompts(self) -> List[str]:
        """
        Get list of available prompts.
        
        :return: List of prompt types
        """
        if not self.prompt_cache:
            self.prompt_cache = self.orchestrator.get_available_prompts()
        return self.prompt_cache

    def get_prompt(self, prompt_type: str) -> str:
        """
        Get a specific prompt.
        
        :param prompt_type: The type of prompt to retrieve
        :return: The prompt text
        """
        if prompt_type in self.prompt_cache:
            return self.prompt_cache[prompt_type]

        prompt_text = self.orchestrator.get_prompt(prompt_type)
        self.prompt_cache[prompt_type] = prompt_text  # Cache for future calls
        return prompt_text

    def shutdown(self) -> None:
        """Clean up resources and shut down components."""
        self.discord_dispatcher.stop()
        self.driver_manager.shutdown_driver()
        self.log_message.emit("PromptService shutdown complete.")
        self.logger.info("PromptService successfully shut down.")
