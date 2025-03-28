import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from .ChatManager import ChatManager
from .AletheiaPromptManager import AletheiaPromptManager
from config.ConfigManager import ConfigManager

class PromptCycleOrchestrator:
    """
    Orchestrates prompt cycles, managing the execution flow and coordination
    between different components of the prompt cycle system.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the orchestrator.
        
        :param config_manager: The configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.prompt_manager = AletheiaPromptManager()
        self.chat_manager = None
        self.rate_limit_delay = self.config_manager.get('RATE_LIMIT_DELAY', 2)
        self.cooldown_period = self.config_manager.get('COOLDOWN_PERIOD', 5)

    def initialize_chat_manager(self, excluded_chats: List[str], model: str, headless: bool = False) -> None:
        """
        Initialize or reinitialize the chat manager.
        
        :param excluded_chats: List of chat titles to exclude
        :param model: The model to use for chat interactions
        :param headless: Whether to run in headless mode
        """
        if self.chat_manager:
            self.chat_manager.shutdown_driver()
            
        self.chat_manager = ChatManager(
            driver_manager=None,
            excluded_chats=excluded_chats,
            model=model,
            timeout=180,
            stable_period=10,
            poll_interval=5,
            headless=headless
        )

    def execute_single_cycle(self, prompt_text: str, new_chat: bool = False) -> List[str]:
        """
        Execute a single prompt cycle.
        
        :param prompt_text: The prompt text to execute
        :param new_chat: Whether to create a new chat
        :return: List of responses
        """
        if not prompt_text:
            self.logger.warning("No prompt text provided.")
            return []
            
        if not self.chat_manager:
            self.logger.error("Chat manager not initialized.")
            return []
            
        try:
            interaction_id = None
            if new_chat:
                interaction_id = f"chat_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
            responses = self.chat_manager.execute_prompts_single_chat(
                [prompt_text], 
                cycle_speed=self.rate_limit_delay,
                interaction_id=interaction_id
            )
            
            self.logger.info(f"Executed prompt cycle with {len(responses)} responses")
            return responses
                
        except Exception as e:
            self.logger.error(f"Error executing prompt cycle: {str(e)}")
            return []

    def execute_multi_cycle(self, prompts: List[str], reverse_order: bool = False) -> Dict[str, List[str]]:
        """
        Execute multiple prompts across multiple chats.
        
        :param prompts: List of prompts to execute
        :param reverse_order: Whether to execute in reverse order
        :return: Dictionary mapping chat titles to their responses
        """
        if not prompts:
            self.logger.warning("No prompts provided for multi-cycle.")
            return {}
            
        if not self.chat_manager:
            self.logger.error("Chat manager not initialized.")
            return {}
            
        try:
            results = {}
            chats = self.chat_manager.get_all_chat_titles()
            if reverse_order:
                chats.reverse()

            if not chats:
                self.logger.warning("No chats found.")
                return {}

            for chat in chats:
                chat_title = chat.get("title", "Untitled")
                self.logger.info(f"Processing chat: {chat_title}")
                chat_responses = []

                for idx, prompt in enumerate(prompts, start=1):
                    self.logger.info(f"Executing prompt {idx}/{len(prompts)}")
                    response = self.chat_manager.execute_prompt_cycle(prompt)
                    chat_responses.append(response)

                results[chat_title] = chat_responses
                self.logger.info(f"Completed processing chat: {chat_title}")

            return results

        except Exception as e:
            self.logger.error(f"Error in multi-cycle execution: {str(e)}")
            return {}

    def get_available_prompts(self) -> List[str]:
        """
        Get list of available prompts.
        
        :return: List of prompt types
        """
        return self.prompt_manager.list_available_prompts()

    def get_prompt(self, prompt_type: str) -> Optional[str]:
        """
        Get a specific prompt by type.
        
        :param prompt_type: The type of prompt to retrieve
        :return: The prompt text or None if not found
        """
        return self.prompt_manager.get_prompt(prompt_type)

    def save_prompt(self, prompt_type: str, prompt_text: str) -> bool:
        """
        Save a prompt.
        
        :param prompt_type: The type of prompt
        :param prompt_text: The prompt text to save
        :return: True if successful, False otherwise
        """
        try:
            self.prompt_manager.save_prompt(prompt_type, prompt_text)
            self.logger.info(f"Saved prompt: {prompt_type}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving prompt: {str(e)}")
            return False

    def reset_prompts(self) -> bool:
        """
        Reset prompts to defaults.
        
        :return: True if successful, False otherwise
        """
        try:
            self.prompt_manager.reset_to_defaults()
            self.logger.info("Prompts reset to defaults")
            return True
        except Exception as e:
            self.logger.error(f"Error resetting prompts: {str(e)}")
            return False

    def shutdown(self) -> None:
        """Clean up resources and shut down components."""
        if self.chat_manager:
            self.chat_manager.shutdown_driver()
        self.logger.info("PromptCycleOrchestrator shutdown complete") 