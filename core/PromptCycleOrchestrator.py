import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.IChatManager import IChatManager
from core.interfaces.IPromptOrchestrator import IPromptOrchestrator
from core.interfaces.IPromptManager import IPromptManager
from core.micro_factories.prompt_factory import PromptFactory

# --- Start: Path Fix ---
import sys
import os
from pathlib import Path

# Get the absolute path to the project root
project_root = str(Path(__file__).resolve().parent.parent)

# Add both the project root and the config directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

config_path = os.path.join(project_root, 'config')
if config_path not in sys.path:
    sys.path.insert(0, config_path)
# --- End: Path Fix ---

from core.config.config_manager import ConfigManager

class PromptCycleOrchestrator(IPromptOrchestrator):
    """Orchestrates prompt cycles and manages interactions with chat services."""
    
    def __init__(self, config_manager: ConfigManager, chat_manager: Optional[IChatManager] = None, prompt_manager: Any = None, driver_manager: Optional[Any] = None):
        """
        Initialize the orchestrator with required dependencies.
        
        Args:
            config_manager: Configuration manager instance
            chat_manager: Chat manager implementation (optional, can be set later)
            prompt_manager: Prompt manager implementation (required)
            driver_manager: DriverManager instance (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.chat_manager = chat_manager
        self.driver_manager = driver_manager
        
        # Ensure prompt_manager is provided
        if prompt_manager:
            self.prompt_manager = prompt_manager
            self.logger.info("Prompt manager initialized successfully.")
        else:
            self.logger.error("Prompt manager is required but was not provided.")
            raise ValueError("Prompt manager is required for PromptCycleOrchestrator")
        
        self.rate_limit_delay = self.config_manager.get('RATE_LIMIT_DELAY', 2)
        self.cooldown_period = self.config_manager.get('COOLDOWN_PERIOD', 5)
        
    def set_chat_manager(self, chat_manager: IChatManager) -> None:
        """
        Set or update the chat manager instance.
        
        Args:
            chat_manager: Chat manager implementation
        """
        self.chat_manager = chat_manager
        self.logger.info("Chat manager has been set/updated.")

    def execute_single_cycle(self, prompt_text: str, new_chat: bool = False) -> List[str]:
        """Execute a single prompt cycle."""
        if not prompt_text:
            self.logger.warning("No prompt text provided.")
            return []
        
        if not self.chat_manager:
            self.logger.error("No chat manager available. Set chat_manager before executing prompts.")
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
        # Try shutting down via chat_manager first if it exists
        if self.chat_manager and hasattr(self.chat_manager, 'shutdown_driver'):
            try:
                self.logger.info("Attempting shutdown via ChatManager...")
                self.chat_manager.shutdown_driver()
            except Exception as e:
                self.logger.warning(f"ChatManager shutdown failed: {e}. Attempting direct driver shutdown.")
                # Fallback to direct driver_manager if chat_manager fails or doesn't have the method
                if self.driver_manager and hasattr(self.driver_manager, 'shutdown_driver'):
                    try:
                        self.driver_manager.shutdown_driver()
                    except Exception as driver_e:
                        self.logger.error(f"Direct DriverManager shutdown also failed: {driver_e}")
        # If no chat_manager, try direct driver_manager shutdown
        elif self.driver_manager and hasattr(self.driver_manager, 'shutdown_driver'):
             try:
                self.logger.info("Attempting direct shutdown via DriverManager...")
                self.driver_manager.shutdown_driver()
             except Exception as driver_e:
                self.logger.error(f"Direct DriverManager shutdown failed: {driver_e}")
        else:
             self.logger.warning("No ChatManager or DriverManager available for shutdown.")
             
        self.logger.info("PromptCycleOrchestrator shutdown sequence complete")
