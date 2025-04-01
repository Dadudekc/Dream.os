import re
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.DriverManager import DriverManager
from core.chat_engine.chat_scraper_service import ChatScraperService
from core.services.prompt_execution_service import PromptService
from core.chat_engine.discord_dispatcher import DiscordDispatcher
from core.chat_engine.feedback_engine import FeedbackEngine
from core.refactor.CursorSessionManager import CursorSessionManager
from core.IChatManager import IChatManager  # Import the interface directly
from core.config.config_manager import ConfigManager
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
    def __init__(
        self,
        config_manager=None,
        memory_path=None,
        prompt_manager=None,
        driver_manager=None,
        feedback_engine=None,
        cursor_manager=None,
        discord_dispatcher=None,
        logger=None,
        path_manager: Optional[PathManager] = None,
        **kwargs
    ):
        """
        Initialize the ChatManager with dependency injection support.
        
        Args:
            config_manager: Configuration manager for application settings
            memory_path: Path to the chat memory file
            prompt_manager: Service for prompt management
            driver_manager: Service for browser driver management
            feedback_engine: Service for handling feedback loops
            cursor_manager: Service for cursor control
            discord_dispatcher: Service for Discord integration
            logger: Logger instance
            path_manager: Optional pre-initialized PathManager instance
            **kwargs: Additional parameters for backward compatibility
        """
        self.config_manager = config_manager
        self.prompt_manager = prompt_manager
        self.driver_manager = driver_manager
        self.feedback_engine = feedback_engine
        self.cursor_manager = cursor_manager
        self.discord_dispatcher = discord_dispatcher
        self.logger = logger or logging.getLogger(__name__)

        self.logger.info("🚀 ChatManager initializing...")

        # Use provided PathManager or initialize one
        self.path_manager = path_manager
        if self.path_manager is None:
            try:
                self.path_manager = PathManager()
                self.logger.info("✨ PathManager initialized internally.")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize internal PathManager: {e}", exc_info=True)
                # Cannot proceed without path manager? Or raise?
                raise RuntimeError("PathManager is required for ChatManager") from e

        # Handle memory_path initialization using the instance path_manager
        if memory_path is None:
            try:
                # Use the instance self.path_manager
                self.memory_path = Path(self.path_manager.get_path("memory")) / "chat_memory.json"
            except Exception as e:
                self.logger.warning(f"⚠️ Error getting path from PathManager: {e}")
                # Fallback might still fail if PathManager is broken
                self.memory_path = Path("memory/chat_memory.json")
        else:
            # Ensure passed memory_path is Path object
            self.memory_path = memory_path if isinstance(memory_path, Path) else Path(memory_path)
        
        self.logger.info(f"📂 Chat memory path: {self.memory_path}")

        # Load chat memory
        self.chat_memory = self._load_chat_memory()

        # Optionally bind prompt service
        if self.prompt_manager:
            self.logger.info("✅ PromptManager injected successfully.")

        if self.driver_manager:
            self.logger.info("✅ DriverManager injected successfully.")

        if self.cursor_manager:
            self.logger.info("✅ CursorManager injected successfully.")

        if self.feedback_engine:
            self.logger.info("✅ FeedbackEngine injected successfully.")
        else:
            # Initialize FeedbackEngine with proper memory path using instance path_manager
            try:
                # Use the instance self.path_manager
                feedback_memory_path = Path(self.path_manager.get_path("memory")) / "feedback_memory.json"
                self.feedback_engine = FeedbackEngine(memory_file=feedback_memory_path)
                self.logger.info("✅ FeedbackEngine created internally.")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not initialize FeedbackEngine: {e}")

        if self.discord_dispatcher:
            self.logger.info("✅ DiscordDispatcher injected successfully.")

        self.logger.info("🚀 ChatManager initialized.")

    def _load_chat_memory(self):
        """
        Load the chat memory from disk, or create an empty one if not found.
        
        Returns:
            dict: The loaded chat memory
        """
        try:
            if not self.memory_path.exists():
                self.logger.info(f"Chat memory file not found. Creating new file at: {self.memory_path}")
                self.memory_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.memory_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                return {}
            
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                memory = json.load(f)
            self.logger.info(f"Chat memory loaded successfully from: {self.memory_path}")
            return memory
        except Exception as e:
            self.logger.error(f"❌ Failed to load chat memory: {e}")
            return {}

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
            self.config_manager.get("discord_enabled", False) if hasattr(self.config_manager, "get")
            else getattr(self.config_manager, "discord_enabled", False)
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

    def generate_dreamscape_episode(self, chat_title: str, source: str = "memory", model: str = "gpt-4o") -> Optional[Any]:
        """
        Generate a dreamscape episode from a specific chat's history.
        
        Args:
            chat_title: The title of the chat to generate an episode from
            source: Source of chat history - "memory" (local file) or "web" (live scraping)
            model: The AI model to use for generation (e.g., 'gpt-4o')
            
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
                
            # Generate episode from chat history with model parameter
            episode = self.dreamscape_service.generate_episode_from_history(
                chat_title=chat_title,
                chat_history=messages,
                model=model  # Pass the model parameter to the dreamscape service
            )
            
            self.logger.info(f"Dreamscape episode generated successfully for chat '{chat_title}' using model {model}")
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
