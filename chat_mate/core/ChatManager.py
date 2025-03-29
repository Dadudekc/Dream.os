import re
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.DriverManager import DriverManager
from core.chat_engine.chat_scraper_service import ChatScraperService
from core.services.prompt_execution_service import UnifiedPromptService
from core.chat_engine.discord_dispatcher import DiscordDispatcher
from core.chat_engine.feedback_engine import FeedbackEngine
from core.refactor.CursorSessionManager import CursorSessionManager
from core.IChatManager import IChatManager  # Import the interface directly
from config.ConfigManager import ConfigManager
from core.PathManager import PathManager

# Import the WebChatScraper
try:
    from core.scraping.web_chat_scraper import WebChatScraper
    WEB_SCRAPER_AVAILABLE = True
except ImportError:
    WEB_SCRAPER_AVAILABLE = False

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
    def __init__(self, config: ConfigManager, logger: Optional[logging.Logger] = None, prompt_manager=None):
        """
        Initialize the ChatManager.
        
        Args:
            config: Configuration object or dictionary
            logger: Optional logger instance
            prompt_manager: Optional prompt manager instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.prompt_manager = prompt_manager

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

        # Initialize WebChatScraper if available
        if WEB_SCRAPER_AVAILABLE:
            # Get excluded chats from config
            excluded_chats = []
            if hasattr(config, "get"):
                excluded_chats = config.get("excluded_chats", [])
            else:
                excluded_chats = getattr(config, "excluded_chats", [])
                
            self.web_scraper = WebChatScraper(
                driver_manager=self.driver_manager,
                logger=self.logger,
                excluded_chats=excluded_chats
            )
            self.logger.info("WebChatScraper initialized successfully")
        else:
            self.web_scraper = None
            self.logger.warning("WebChatScraper not available; web scraping of chats will be disabled")

        # (Optional) Initialize dreamscape service if available.
        try:
            from core.services.dreamscape_generator_service import DreamscapeGenerationService
            self.dreamscape_service = DreamscapeGenerationService()
        except ImportError:
            self.logger.warning("DreamscapeGenerationService not available; using empty implementation.")
            self.dreamscape_service = None

        # Initialize internal state for orchestration enhancements.
        self._last_response: Optional[str] = None
        self._prompt_queue: List[str] = []
        self._injected_context: Dict[str, Any] = {}

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
        """
        Return a list of all available chat titles.
        
        If the WebChatScraper is available, this will scrape the titles from the web interface.
        Otherwise, it falls back to the existing scraper or memory file.
        """
        if self.web_scraper:
            self.logger.info("Getting chat titles from web interface")
            return self.web_scraper.scrape_chat_list()
        else:
            self.logger.info("Getting chat titles from existing scraper")
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
        Send a prompt specifically structured for chat-oriented API.
        Support for context injection.
        
        Args:
            task: The core prompt/task.
            context: Optional dict of context.
            
        Returns:
            Optional[str]: The response.
        """
        try:
            if context:
                self.inject_context(context)
            return self.execute_prompt_cycle(task)
        except Exception as e:
            self.logger.error(f"Error sending chat prompt: {e}")
            return None

    def switch_execution_mode(self, mode: str):
        """
        Switch the execution mode for this ChatManager instance.
        
        Args:
            mode (str): The new execution mode.
        """
        if not hasattr(self.cursor_manager, "set_execution_mode"):
            self.logger.error("CursorSessionManager does not support mode switching")
            return
        
        self.logger.info(f"Switching execution mode to: {mode}")
        self.cursor_manager.set_execution_mode(mode)

    def generate_dreamscape_episode(self, chat_title: str, source: str = "memory") -> Optional[Any]:
        """
        Generate a dreamscape episode from a specific chat's history.
        
        Args:
            chat_title: The title of the chat to generate an episode from
            source: Source of chat history - "memory" (local file) or "web" (live scraping)
            
        Returns:
            The generated episode data, or None if generation fails
        """
        if not self.dreamscape_service:
            self.logger.error("Dreamscape service is not available.")
            return None
            
        try:
            # Retrieve chat history for the specified chat title
            chat_history = self.get_chat_history(chat_title, source=source)
            if not chat_history:
                self.logger.warning(f"No chat history found for '{chat_title}'")
                return None
                
            # Extract messages from the chat history
            messages = []
            for entry in chat_history:
                if 'content' in entry:
                    messages.append(entry['content'])
                    
            if not messages:
                self.logger.warning(f"No message content found in chat history for '{chat_title}'")
                return None
                
            # Generate episode from chat history
            episode = self.dreamscape_service.generate_dreamscape_episode(
                chat_title=chat_title,
                chat_history=messages
            )
            
            self.logger.info(f"Dreamscape episode generated successfully for chat '{chat_title}'")
            return episode
            
        except Exception as e:
            self.logger.error(f"Error generating dreamscape episode: {e}")
            return None

    # -----------------------------
    # Orchestration Enhancements
    # -----------------------------

    def execute_prompt_cycle(self, prompt: str) -> str:
        """
        Execute a complete prompt cycle: 
        Optionally inject context, send the prompt, and return the final response.
        
        Args:
            prompt (str): The prompt to execute.
            
        Returns:
            str: The final response.
        """
        self.logger.info("Starting prompt cycle...")
        # Inject external context if present
        if self._injected_context:
            prompt = f"{prompt}\nContext: {json.dumps(self._injected_context, indent=2)}"
            self.logger.info(f"Prompt after context injection: {prompt}")
            self._injected_context = {}  # Clear injected context after use
        response = self.send_prompt(prompt)
        self._last_response = response
        return response

    def queue_prompts(self, prompts: List[str]) -> None:
        """
        Queue multiple prompts for sequential execution.
        Each prompt is processed via execute_prompt_cycle.
        
        Args:
            prompts (List[str]): List of prompts to queue.
        """
        self.logger.info("Queuing prompts for sequential execution...")
        self._prompt_queue = prompts
        for prompt in prompts:
            self.logger.info(f"Processing queued prompt: {prompt}")
            cycle_response = self.execute_prompt_cycle(prompt)
            self.logger.info(f"Cycle response: {cycle_response[:100]}...")

    def get_last_response(self) -> Optional[str]:
        """
        Get the last received prompt response (post-analysis).
        
        Returns:
            Optional[str]: The last response, or None if not available.
        """
        return self._last_response

    def inject_context(self, context: Dict[str, Any]) -> None:
        """
        Inject external context (e.g. dreamscape metadata, memory snapshots)
        into the next prompt.
        
        Args:
            context (Dict[str, Any]): Context to inject.
        """
        self._injected_context.update(context)
        self.logger.info(f"Injected context: {context}")

    def get_chat_history(self, chat_title: str, source: str = "memory") -> List[Dict[str, Any]]:
        """
        Get the chat history for a specific chat by title.
        
        Args:
            chat_title: The title of the chat to retrieve history for
            source: Source of chat history - "memory" (local file) or "web" (live scraping)
            
        Returns:
            List of chat message objects or empty list if not found
        """
        try:
            # Determine the source of chat history
            if source == "web" and self.web_scraper:
                self.logger.info(f"Retrieving chat history for '{chat_title}' from web interface")
                # Get chat history from web interface
                messages = self.web_scraper.scrape_chat_by_title(chat_title)
                
                # Convert web scraper format to common format if necessary
                standardized_messages = []
                for msg in messages:
                    standardized_messages.append({
                        "role": msg.get("role", "unknown"),
                        "content": msg.get("content", ""),
                        "timestamp": msg.get("timestamp")
                    })
                
                return standardized_messages
            else:
                # Fall back to memory file
                self.logger.info(f"Retrieving chat history for '{chat_title}' from memory file")
                
                # Load chat history from memory file
                if not self.memory_path.exists():
                    self.logger.warning(f"Chat memory file not found: {self.memory_path}")
                    return []
                    
                with self.memory_path.open('r', encoding='utf-8') as f:
                    memory = json.load(f)
                    
                # Find the chat with the specified title
                for chat in memory.get('chats', []):
                    if chat.get('title') == chat_title:
                        return chat.get('messages', [])
                        
                self.logger.warning(f"No chat found with title: {chat_title}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error retrieving chat history: {e}")
            return []
