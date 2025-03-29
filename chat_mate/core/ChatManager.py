import re
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.DriverManager import DriverManager
from core.chat_engine.chat_scraper_service import ChatScraperService
from core.services.prompt_execution_service import UnifiedPromptService
from core.chat_engine.discord_dispatcher import DiscordDispatcher
from core.chat_engine.feedback_engine import FeedbackEngine
from core.refactor.CursorSessionManager import CursorSessionManager
from interfaces.chat_manager import IChatManager
from config.ConfigManager import ConfigManager
from core.PathManager import PathManager

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename (str): The filename to sanitize
        
    Returns:
        str: The sanitized filename.
    """
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

class ChatManager(IChatManager):
    def __init__(self, config: ConfigManager, logger: Optional[logging.Logger] = None):
        """
        Initialize the ChatManager.
        
        Args:
            config: Configuration object or dictionary
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Patch memory path initialization using PathManager.
        memory_path = None
        if hasattr(config, "get"):
            memory_path = config.get("memory_file", None)
        else:
            memory_path = getattr(config, "memory_file", None)

        if memory_path is None or isinstance(memory_path, type):
            self.logger.warning(
                f"Invalid memory_path provided (got {memory_path}). Using default memory path."
            )
            memory_path = PathManager().get_path("memory") / "chat_memory.json"
        elif isinstance(memory_path, str):
            memory_path = Path(memory_path)
        
        self.memory_path = memory_path
        self.logger.info(f"Initializing ChatManager with memory file: {self.memory_path}")

        # Initialize FeedbackEngine with proper memory path
        feedback_memory_path = PathManager().get_path("memory") / "feedback_memory.json"
        self.feedback_engine = FeedbackEngine(memory_file=feedback_memory_path)

        self._load_memory()

        # Initialize CursorSessionManager with proper configuration.
        cursor_config = {
            "execution_mode": (
                config.get("execution_mode", "full_sync") if hasattr(config, "get")
                else getattr(config, "execution_mode", "full_sync")
            ),
            "cursor_window_title": (
                config.get("cursor_window_title", "Cursor") if hasattr(config, "get")
                else getattr(config, "cursor_window_title", "Cursor")
            ),
            "prompt_delay": (
                config.get("prompt_delay", 5) if hasattr(config, "get")
                else getattr(config, "prompt_delay", 5)
            ),
            "hotkeys": (
                config.get("hotkeys", CursorSessionManager.DEFAULT_HOTKEYS) if hasattr(config, "get")
                else getattr(config, "hotkeys", CursorSessionManager.DEFAULT_HOTKEYS)
            )
        }
        self.cursor_manager = CursorSessionManager(cursor_config)

        # Determine the AI model (default to 'gpt-4o')
        self.model = (
            config.get("default_model") if hasattr(config, "get")
            else getattr(config, "default_model", "gpt-4o")
        )

        # Retrieve browser configuration options
        headless = (
            config.get("headless") if hasattr(config, "get")
            else getattr(config, "headless", True)
        )
        profile_dir = (
            config.get("profile_dir") if hasattr(config, "get")
            else getattr(config, "profile_dir", None)
        )
        cookie_file = (
            config.get("cookie_file") if hasattr(config, "get")
            else getattr(config, "cookie_file", None)
        )
        chrome_options = (
            config.get("chrome_options") if hasattr(config, "get")
            else getattr(config, "chrome_options", [])
        )

        # Initialize the DriverManager with given options.
        self.driver_manager = DriverManager(
            headless=headless,
            profile_dir=profile_dir,
            cookie_file=cookie_file,
            undetected_mode=True,
            timeout=30,
            additional_options=chrome_options
        )

        # Initialize core chat services.
        self.chat_scraper = ChatScraperService(self.driver_manager, self.logger)
        self.prompt_engine = UnifiedPromptService(
            config_manager=self.config,
            path_manager=PathManager(),
            config_service=self.config,
            prompt_manager=self.prompt_manager,
            driver_manager=self.driver_manager,
            model=self.model
        )
        self.discord_dispatcher = DiscordDispatcher(self.config, self.logger)

        # (Optional) Initialize dreamscape service if available.
        # This service should be patched so that generate_episodes() is called
        # without passing an unexpected keyword argument.
        try:
            from core.services.dreamscape_generator_service import DreamscapeGenerationService
            self.dreamscape_service = DreamscapeGenerationService()
        except ImportError:
            self.logger.warning("DreamscapeGenerationService not available; using empty implementation.")
            self.dreamscape_service = None

    def _load_memory(self):
        """Load or initialize the chat memory file."""
        try:
            if not self.memory_path.exists():
                self.logger.info(f"Chat memory file not found. Creating new file at: {self.memory_path}")
                self.memory_path.parent.mkdir(parents=True, exist_ok=True)
                self.memory_path.write_text("{}", encoding="utf-8")
            else:
                self.logger.info(f"Chat memory file found: {self.memory_path}")
            
            with self.memory_path.open('r', encoding='utf-8') as f:
                self.memory = json.load(f)
            self.logger.info(f"Chat memory loaded successfully from: {self.memory_path}")
        except Exception as e:
            self.logger.error(f"Error loading chat memory: {e}")
            self.memory = {}

    def start(self):
        """Start the chat manager and all underlying services."""
        self.logger.info("ChatManager starting...")
        self.driver_manager.get_driver()  # Lazy initialization of the driver
        self.logger.info("Driver launched successfully.")
        self.feedback_engine.load_feedback_data()

    def send_prompt(self, prompt: str) -> str:
        """
        Send a prompt using the prompt engine, wait for a stable response,
        dispatch it to Discord if enabled, and process feedback.
        
        Args:
            prompt (str): The prompt text.
            
        Returns:
            str: The response received.
        """
        self.logger.info(f"Sending prompt: {prompt}")
        result = self.prompt_engine.send_prompt(prompt)
        if not result:
            self.logger.error("Failed to send prompt")
            return ""
        response = self.prompt_engine.wait_for_stable_response()
        self.logger.info(f"Received response: {response[:100]}...")
        
        # Dispatch response to Discord if enabled.
        discord_enabled = (
            self.config.get("discord_enabled", False) if hasattr(self.config, "get")
            else getattr(self.config, "discord_enabled", False)
        )
        if discord_enabled:
            self.discord_dispatcher.dispatch(response)
        self.feedback_engine.process_response(response)
        return response

    def get_all_chat_titles(self) -> List[Dict[str, Any]]:
        """Return a list of all available chat titles."""
        return self.chat_scraper.get_all_chats()

    def execute_prompts_single_chat(self, prompts: List[str], cycle_speed: int, interaction_id: Optional[str] = None) -> List[str]:
        """
        Execute multiple prompts in a single chat session.
        
        Args:
            prompts (List[str]): List of prompt texts.
            cycle_speed (int): Speed for cycling through prompts.
            interaction_id (Optional[str]): Optional interaction ID.
            
        Returns:
            List[str]: List of responses.
        """
        if not self.prompt_engine:
            self.logger.error("Prompt engine not initialized")
            return []
        self.prompt_engine.cycle_speed = cycle_speed
        return self.prompt_engine.execute_prompts_single_chat(prompts)

    def analyze_execution_response(self, response: str, prompt_text: str) -> Dict[str, Any]:
        """
        Analyze the response from a prompt execution.
        
        Args:
            response (str): The response text.
            prompt_text (str): The original prompt.
            
        Returns:
            Dict[str, Any]: Analysis summary.
        """
        return {
            "length": len(response),
            "has_code": "```" in response,
            "sentiment": "neutral"  # Placeholder for sentiment analysis
        }

    def shutdown_driver(self) -> None:
        """Shutdown all services and cleanly close the driver."""
        self.logger.info("Shutting down ChatManager...")
        if hasattr(self.driver_manager, 'quit_driver'):
            self.driver_manager.quit_driver()
        else:
            self.driver_manager.shutdown_driver()
        self.feedback_engine.save_feedback_data()
        self.logger.info("Shutdown complete.")

    def send_chat_prompt(self, task: str, context: Optional[Dict] = None) -> Optional[str]:
        """
        Generate and send a prompt via the Cursor session manager.
        
        Args:
            task (str): Task description.
            context (Optional[Dict]): Additional context.
            
        Returns:
            Optional[str]: Generated code or None on error.
        """
        prompt = self.cursor_manager.generate_prompt(task, context)
        try:
            generated_code = self.cursor_manager.execute_prompt(prompt)
            return generated_code
        except RuntimeError as e:
            self.logger.error(f"Failed to execute prompt: {e}")
            return None

    def switch_execution_mode(self, mode: str):
        """
        Switch the execution mode of the Cursor manager.
        
        Args:
            mode (str): New execution mode.
        """
        try:
            self.cursor_manager.switch_mode(mode)
            self.logger.info(f"Switched execution mode to {mode}")
        except ValueError as e:
            self.logger.error(e)

    def generate_dreamscape_episode(self, context: Dict[str, Any]) -> Optional[Any]:
        """
        Generate a dreamscape episode using the dreamscape service.
        This method calls the underlying generate_episode method without an
        unexpected 'prompt_text' keyword.
        
        Args:
            context (Dict[str, Any]): The context data for episode generation.
        
        Returns:
            The generated episode data, or None if generation fails.
        """
        if not self.dreamscape_service:
            self.logger.error("Dreamscape service is not available.")
            return None

        try:
            # Call generate_episode using the template name and context.
            # (Do not pass a 'prompt_text' argument.)
            episode = self.dreamscape_service.generate_episode(
                template_name="dreamscape_template.j2",
                context=context
            )
            self.logger.info("Dreamscape episode generated successfully.")
            return episode
        except Exception as e:
            self.logger.error(f"Error generating dreamscape episodes: {e}")
            return None

    def execute_prompt_cycle(self, prompt: str) -> str:
        # Implementation remains the same
        pass
