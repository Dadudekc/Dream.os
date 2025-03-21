import os
import json
import time
import logging
import threading
import re
from datetime import datetime
import sys

# Ensure the root folder is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ChatManager import ChatManager
from core.AletheiaPromptManager import AletheiaPromptManager
from core.FileManager import FileManager
from core.UnifiedDiscordService import UnifiedDiscordService
from core.PromptCycleManager import PromptCycleManager
from core.ReinforcementEngine import ReinforcementEngine
from utils.run_summary import sanitize_filename, generate_full_run_json
from core.UnifiedDriverManager import UnifiedDriverManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DreamscapeService:
    """
    Central service class that encapsulates all core business logic.
    This module has zero dependencies on any UI framework.
    """

    def __init__(self, config):
        """
        Initialize DreamscapeService with a configuration object.
        
        :param config: A configuration object that exposes settings (e.g., headless, default_model, excluded_chats, archive_enabled, memory_file).
        """
        self.config = config

        # Initialize core components and managers
        self.prompt_manager = AletheiaPromptManager(
            prompt_file="chat_mate/prompts.json",
            memory_file=self.config.memory_file
        )
        self.chat_manager = None
        self.discord = None
        self.file_manager = FileManager()
        self.cycle_manager = PromptCycleManager(
            prompt_manager=self.prompt_manager,
            append_output=lambda msg: logger.info(msg)  # Logging callback
        )
        self.reinforcement_engine = ReinforcementEngine()

        self.logger = self.config.get_logger("DreamscapeService")
        self.logger.info("DreamscapeService initialized.")

    # --- Chat Manager & Prompt Execution ---

    def create_chat_manager(self, model: str = None, headless: bool = None, excluded_chats: list = None,
                            timeout: int = 180, stable_period: int = 10, poll_interval: int = 5) -> None:
        """
        Create (or re-create) a ChatManager instance using provided or configuration defaults.
        """
        if self.chat_manager:
            self.chat_manager.shutdown_driver()

        model = model or self.config.default_model
        headless = headless if headless is not None else self.config.headless
        excluded_chats = excluded_chats or self.config.excluded_chats

        # Create driver options
        driver_options = {
            "headless": headless,
            "window_size": (1920, 1080),
            "disable_gpu": True,
            "no_sandbox": True,
            "disable_dev_shm": True
        }

        self.chat_manager = ChatManager(
            driver_options=driver_options,
            excluded_chats=excluded_chats,
            model=model,
            timeout=timeout,
            stable_period=stable_period,
            poll_interval=poll_interval,
            headless=headless
        )
        self.logger.info("ChatManager created with model '%s' and headless=%s", model, headless)

    def execute_prompt(self, prompt_text: str) -> list:
        """
        Execute a single prompt using the current ChatManager.
        
        :param prompt_text: The prompt text to execute.
        :return: A list of AI responses.
        """
        if not self.chat_manager:
            raise RuntimeError("ChatManager is not initialized. Call create_chat_manager() first.")

        self.logger.info("Executing single prompt...")
        responses = self.chat_manager.execute_prompts_single_chat([prompt_text], cycle_speed=2)
        self.logger.info("Prompt execution completed. Received %d responses.", len(responses))
        return responses

    def start_prompt_cycle(self, selected_prompt_names: list) -> None:
        """
        Execute a prompt cycle across all available chats.
        
        :param selected_prompt_names: List of prompt names to execute.
        """
        if not self.chat_manager:
            raise RuntimeError("ChatManager is not initialized. Call create_chat_manager() first.")

        all_chats = self.chat_manager.get_all_chat_titles()
        if not all_chats:
            self.logger.info("No chats found. Aborting prompt cycle.")
            return

        filtered_chats = [chat for chat in all_chats if chat.get("title") not in self.config.excluded_chats]
        self.logger.info("Starting prompt cycle for %d chats.", len(filtered_chats))

        for chat in filtered_chats:
            chat_title = chat.get("title", "Unknown Chat")
            chat_link = chat.get("link")
            self.logger.info("Processing chat: %s", chat_title)

            if not chat_link:
                self.logger.warning("Skipping chat '%s' due to missing link.", chat_title)
                continue

            # Navigate to the chat and allow time for it to load
            driver = self.chat_manager.driver_manager.get_driver()
            driver.get(chat_link)
            time.sleep(3)

            chat_responses = []
            for prompt_name in selected_prompt_names:
                # Load prompt text from prompt manager
                prompt_text = self.prompt_manager.get_prompt(prompt_name)
                if not prompt_text:
                    self.logger.warning("Empty prompt for '%s'; skipping.", prompt_name)
                    continue

                self.logger.info("Sending prompt '%s' to chat '%s'", prompt_name, chat_title)
                if not self.chat_manager.prompt_engine.send_prompt(prompt_text):
                    self.logger.error("Failed to send prompt '%s' in chat '%s'", prompt_name, chat_title)
                    continue

                response = self.chat_manager.prompt_engine.wait_for_stable_response()
                if not response:
                    self.logger.warning("No stable response for prompt '%s' in chat '%s'", prompt_name, chat_title)
                    continue

                # Special handling for 'dreamscape' prompt: auto-episode management
                if prompt_name.lower() == "dreamscape":
                    episode_counter = self.prompt_manager.prompts.get("dreamscape", {}).get("episode_counter", 1)
                    chat_filename = f"episode_{episode_counter}_{sanitize_filename(chat_title)}.txt"
                    self.prompt_manager.prompts["dreamscape"]["episode_counter"] = episode_counter + 1
                    self.prompt_manager.save_prompts()
                    if self.discord:
                        self.discord.send_message(
                            f"New Dreamscape Episode from '{chat_title}':\n{response}"
                        )
                        self.logger.info("Posted new Dreamscape episode to Discord for '%s'", chat_title)
                else:
                    chat_filename = f"{sanitize_filename(chat_title)}.txt"

                # Save the response to a file
                prompt_dir = os.path.join("responses", sanitize_filename(chat_title), sanitize_filename(prompt_name))
                os.makedirs(prompt_dir, exist_ok=True)
                chat_file_path = os.path.join(prompt_dir, chat_filename)
                try:
                    with open(chat_file_path, 'w', encoding='utf-8') as f:
                        f.write(response)
                    self.logger.info("Saved response for chat '%s' to %s", chat_title, chat_file_path)
                except Exception as e:
                    self.logger.error("Error saving response for chat '%s': %s", chat_title, e)

                chat_responses.append({
                    "prompt_name": prompt_name,
                    "prompt_text": prompt_text,
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "ai_observations": self.analyze_execution_response(response, prompt_text)
                })
                time.sleep(1)

            run_metadata = {
                "timestamp": datetime.now().isoformat(),
                "model": self.chat_manager.model,
                "chat_count": 1,
                "execution_time": f"{round(time.time(), 2)}s",
                "bottlenecks": []
            }
            output_dir = os.path.join("responses", sanitize_filename(chat_title))
            generate_full_run_json(chat_title, chat_link, chat_responses, run_metadata, output_dir)
            self.logger.info("Saved full_run.json for chat '%s'.", chat_title)

        self.logger.info("Completed full prompt cycle across all chats.")

    # --- Prompt Management ---

    def load_prompt(self, prompt_type: str) -> (str, str):
        """
        Load a prompt and its associated model.
        
        :param prompt_type: The name of the prompt.
        :return: Tuple of (prompt_text, model).
        """
        try:
            prompt_text = self.prompt_manager.get_prompt(prompt_type)
            model = self.prompt_manager.get_model(prompt_type)
            self.logger.info("Loaded prompt '%s' with model '%s'.", prompt_type, model)
            return prompt_text, model
        except Exception as e:
            self.logger.error("Error loading prompt '%s': %s", prompt_type, e)
            raise RuntimeError(e)

    def save_prompt(self, prompt_type: str, prompt_text: str) -> None:
        """
        Save or update a prompt.
        
        :param prompt_type: The prompt identifier.
        :param prompt_text: The prompt content.
        """
        self.prompt_manager.save_prompt(prompt_type, prompt_text)
        self.logger.info("Prompt '%s' saved.", prompt_type)

    def reset_prompts(self) -> None:
        """
        Reset all prompts to their default values.
        """
        self.prompt_manager.reset_to_defaults()
        self.logger.info("Prompts have been reset to defaults.")

    # --- Discord Bot Management ---

    def launch_discord_bot(self, bot_token: str, channel_id: int, log_callback=None) -> None:
        """
        Launch the Discord bot if it's not already running.
        All Discord lifecycle management is handled here.
        
        :param bot_token: Discord bot token.
        :param channel_id: Default channel ID.
        :param log_callback: Optional callback for logging Discord messages.
        """
        if self.discord and self.discord.is_running:
            self.logger.warning("Discord bot is already running.")
            return

        # Initialize UnifiedDiscordService with configuration
        self.discord = UnifiedDiscordService(
            bot_token=bot_token,
            default_channel_id=channel_id,
            template_dir=os.path.join(self.config.template_dir, "discord")
        )
        
        # Set up logging callback
        if log_callback:
            self.discord.set_log_callback(log_callback)
        else:
            self.discord.set_log_callback(lambda msg: self.logger.info("Discord: %s", msg))

        # Start the bot
        self.discord.run()
        self.logger.info("Discord bot launched.")

    def stop_discord_bot(self) -> None:
        """
        Stop the Discord bot if it is running.
        This method ensures that the Discord lifecycle is managed only by DreamscapeService.
        """
        if self.discord and self.discord.is_running:
            self.discord.stop()
            self.logger.info("Discord bot stopped.")
        else:
            self.logger.warning("Discord bot is not running.")

    def send_discord_message(self, message: str, channel_id: int = None) -> None:
        """
        Send a message through Discord.
        
        :param message: The message to send.
        :param channel_id: Optional channel ID (uses default if not specified).
        """
        if not self.discord or not self.discord.is_running:
            self.logger.warning("Discord bot is not running.")
            return

        self.discord.send_message(message, channel_id)

    def send_discord_file(self, file_path: str, content: str = "", channel_id: int = None) -> None:
        """
        Send a file through Discord.
        
        :param file_path: Path to the file to send.
        :param content: Optional message to send with the file.
        :param channel_id: Optional channel ID (uses default if not specified).
        """
        if not self.discord or not self.discord.is_running:
            self.logger.warning("Discord bot is not running.")
            return

        self.discord.send_file(file_path, content, channel_id)

    def send_discord_template(self, template_name: str, context: dict, channel_id: int = None) -> None:
        """
        Send a templated message through Discord.
        
        :param template_name: Name of the template to use.
        :param context: Dictionary of context variables for the template.
        :param channel_id: Optional channel ID (uses default if not specified).
        """
        if not self.discord or not self.discord.is_running:
            self.logger.warning("Discord bot is not running.")
            return

        self.discord.send_template(template_name, context, channel_id)

    def get_discord_status(self) -> dict:
        """Get current Discord bot status."""
        if not self.discord:
            return {
                "is_running": False,
                "message": "Discord bot not initialized"
            }
        return self.discord.get_status()

    # --- Reinforcement Tools ---

    def run_prompt_tuning(self) -> None:
        """
        Execute prompt tuning using the reinforcement engine.
        """
        self.reinforcement_engine.auto_tune_prompts(self.prompt_manager)
        self.logger.info("Prompt tuning completed. Memory updated on %s", 
                         self.reinforcement_engine.memory_data.get('last_updated'))

    # --- Execution Response Analysis ---

    def analyze_execution_response(self, response: str, prompt_text: str) -> dict:
        """
        Analyze an AI execution response to extract performance metrics.
        
        :param response: The AI response text.
        :param prompt_text: The prompt text that was executed.
        :return: A dictionary of analysis results.
        """
        analysis = self.chat_manager.analyze_execution_response(response, prompt_text)
        self.logger.info("Response analysis completed.")
        return analysis
