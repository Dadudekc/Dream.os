from PyQt5.QtCore import QObject, pyqtSignal
import logging
from typing import List, Dict, Any
from .config_service import ConfigService
from core.PromptCycleOrchestrator import PromptCycleOrchestrator
from core.DiscordBatchDispatcher import DiscordBatchDispatcher
from core.ReinforcementEvaluator import ReinforcementEvaluator
from core.DriverSessionManager import DriverSessionManager

class PromptService(QObject):
    """
    Service for managing and executing prompts.
    Coordinates between different components for prompt execution,
    feedback, and Discord integration.
    """
    
    log_message = pyqtSignal(str)
    
    def __init__(self, config_service: ConfigService):
        """
        Initialize the prompt service.
        
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
        
    def initialize_chat_manager(self, excluded_chats: List[str], model: str, headless: bool = False) -> None:
        """
        Initialize or reinitialize the chat manager.
        
        :param excluded_chats: List of chat titles to exclude
        :param model: The model to use for chat interactions
        :param headless: Whether to run in headless mode
        """
        self.orchestrator.initialize_chat_manager(excluded_chats, model, headless)
        
    def execute_prompt(self, prompt_text: str, new_chat: bool = False) -> List[str]:
        """
        Execute a prompt and return responses.
        
        :param prompt_text: The prompt text to execute
        :param new_chat: Whether to create a new chat
        :return: List of responses
        """
        if not prompt_text:
            self.log_message.emit("No prompt text provided.")
            return []
            
        try:
            # Execute prompt through orchestrator
            responses = self.orchestrator.execute_single_cycle(prompt_text, new_chat)
            
            # Evaluate responses
            for response in responses:
                evaluation = self.evaluator.evaluate_response(response, prompt_text)
                self.log_message.emit(f"Response evaluation: {evaluation['feedback']}")
                
                # Queue feedback for Discord if configured
                if self.config_service.get('DISCORD_FEEDBACK_ENABLED', False):
                    self.discord_dispatcher.queue_message(
                        self.config_service.get('DISCORD_CHANNEL_ID'),
                        f"Feedback for prompt: {evaluation['feedback']}"
                    )
            
            return responses
            
        except Exception as e:
            self.log_message.emit(f"Error executing prompt: {str(e)}")
            return []
            
    def execute_multi_prompt(self, prompts: List[str], reverse_order: bool = False) -> Dict[str, List[str]]:
        """
        Execute multiple prompts across multiple chats.
        
        :param prompts: List of prompts to execute
        :param reverse_order: Whether to execute in reverse order
        :return: Dictionary mapping chat titles to their responses
        """
        try:
            # Execute prompts through orchestrator
            results = self.orchestrator.execute_multi_cycle(prompts, reverse_order)
            
            # Evaluate responses for each chat
            for chat_title, responses in results.items():
                for response in responses:
                    evaluation = self.evaluator.evaluate_response(response, prompts[0])
                    self.log_message.emit(f"Chat {chat_title} response evaluation: {evaluation['feedback']}")
                    
                    # Queue feedback for Discord if configured
                    if self.config_service.get('DISCORD_FEEDBACK_ENABLED', False):
                        self.discord_dispatcher.queue_message(
                            self.config_service.get('DISCORD_CHANNEL_ID'),
                            f"Chat {chat_title} feedback: {evaluation['feedback']}"
                        )
            
            return results
            
        except Exception as e:
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
        return self.orchestrator.save_prompt(prompt_type, prompt_text)
        
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
        return self.orchestrator.get_available_prompts()
        
    def get_prompt(self, prompt_type: str) -> str:
        """
        Get a specific prompt.
        
        :param prompt_type: The type of prompt to retrieve
        :return: The prompt text
        """
        return self.orchestrator.get_prompt(prompt_type)
        
    def shutdown(self) -> None:
        """Clean up resources and shut down components."""
        self.discord_dispatcher.stop()
        self.driver_manager.shutdown_driver()
        self.log_message.emit("Prompt service shutdown complete") 