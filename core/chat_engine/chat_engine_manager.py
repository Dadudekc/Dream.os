import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import non-circular dependencies first
from core.DriverManager import DriverManager
from core.PathManager import PathManager
from core.config.config_manager import ConfigManager
from core.refactor.CursorSessionManager import CursorSessionManager
from core.chat_engine.chat_scraper_service import ChatScraperService
from core.chat_engine.discord_dispatcher import DiscordDispatcher
from core.chat_engine.feedback_engine import FeedbackEngine
from core.chat_engine.gui_event_handler import GUIEventHandler
from core.services.prompt_execution_service import PromptService
from core.IChatManager import IChatManager
from core.services.discord.DiscordManager import DiscordManager

class ChatEngineManager(IChatManager):
    """
    Facade for managing the chat engine services.
    This class coordinates the various components of the chat engine.
    """

    def __init__(self, config=None, logger=None, prompt_manager=None, discord_manager: Optional[DiscordManager] = None):
        """
        Initializes all the services required for the chat engine.
        
        Args:
            config: Configuration object or dictionary
            logger: Optional logger instance
            prompt_manager: Optional prompt manager instance
            discord_manager: Optional Discord manager instance
        """
        self.config = config or ConfigManager()
        self.logger = logger or logging.getLogger(__name__)
        self.prompt_manager = prompt_manager
        self.discord_manager = discord_manager
        
        # Initialize memory paths
        self.path_manager = PathManager()
        self.memory_path = self.path_manager.get_path("memory") / "chat_memory.json"
        self.feedback_memory_path = self.path_manager.get_path("memory") / "feedback_memory.json"
        
        # Load memory
        self._load_memory()
        
        # Initialize the DriverManager with config options
        headless = getattr(self.config, "headless", True) if not hasattr(self.config, "get") else self.config.get("headless", True)
        profile_dir = getattr(self.config, "profile_dir", None) if not hasattr(self.config, "get") else self.config.get("profile_dir", None)
        cookie_file = getattr(self.config, "cookie_file", None) if not hasattr(self.config, "get") else self.config.get("cookie_file", None)
        chrome_options = getattr(self.config, "chrome_options", []) if not hasattr(self.config, "get") else self.config.get("chrome_options", [])
        
        self.driver_manager = DriverManager(
            headless=headless,
            profile_dir=profile_dir,
            cookie_file=cookie_file,
            undetected_mode=True,
            timeout=30,
            additional_options=chrome_options
        )
        
        # Get model from config (default to gpt-4o)
        self.model = getattr(self.config, "default_model", "gpt-4o") if not hasattr(self.config, "get") else self.config.get("default_model", "gpt-4o")
        
        # Initialize services that don't have circular dependencies
        self.scraper_service = ChatScraperService(self.driver_manager, self.logger)
        self.prompt_executor = PromptService(
            config_manager=self.config,
            path_manager=self.path_manager,
            config_service=self.config,
            prompt_manager=self.prompt_manager,
            driver_manager=self.driver_manager,
            model=self.model,
            discord_manager=self.discord_manager
        )
        self.feedback_engine = FeedbackEngine(memory_file=self.feedback_memory_path)
        
        # Initialize Discord service
        discord_enabled = getattr(self.config, "discord_enabled", False) if not hasattr(self.config, "get") else self.config.get("discord_enabled", False)
        self.discord_dispatcher = DiscordDispatcher(self.config, self.logger)
        self.gui_handler = GUIEventHandler(config=self.config, dispatcher=self.discord_dispatcher)
        
        # Late import and initialize components that could cause circular dependencies
        from core.chat_engine.chat_cycle_controller import ChatCycleController
        self.cycle_controller = ChatCycleController(
            driver_manager=self.driver_manager,
            prompt_executor=self.prompt_executor,
            chat_scraper=self.scraper_service
        )
        
        # Initialize CursorSessionManager for code generation
        cursor_config = {
            "execution_mode": getattr(self.config, "execution_mode", "full_sync") if not hasattr(self.config, "get") else self.config.get("execution_mode", "full_sync"),
            "cursor_window_title": getattr(self.config, "cursor_window_title", "Cursor") if not hasattr(self.config, "get") else self.config.get("cursor_window_title", "Cursor"),
            "prompt_delay": getattr(self.config, "prompt_delay", 5) if not hasattr(self.config, "get") else self.config.get("prompt_delay", 5),
            "hotkeys": getattr(self.config, "hotkeys", CursorSessionManager.DEFAULT_HOTKEYS) if not hasattr(self.config, "get") else self.config.get("hotkeys", CursorSessionManager.DEFAULT_HOTKEYS)
        }
        self.cursor_manager = CursorSessionManager(cursor_config)

        # Optional DreamscapeService
        try:
            from core.services.dreamscape_generator_service import DreamscapeGenerationService
            self.dreamscape_service = DreamscapeGenerationService()
        except ImportError:
            self.logger.warning("DreamscapeGenerationService not available")
            self.dreamscape_service = None
            
        # Initialize internal state for orchestration enhancements
        self._last_response: Optional[str] = None
        self._prompt_queue: List[str] = []
        self._injected_context: Dict[str, Any] = {}
        self.logger.info("ChatEngineManager initialized.")

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
        """
        Starts all the services in the chat engine.
        """
        try:
            self.driver_manager.get_driver()  # Initialize driver
            if hasattr(self.discord_dispatcher, 'run_bot'):
                self.discord_dispatcher.run_bot()
            self.gui_handler.start_dispatcher()
            self.feedback_engine.load_feedback_data()
            self.logger.info("Chat Engine Manager started successfully")
        except Exception as e:
            self.logger.error(f"Error starting Chat Engine Manager: {e}")
    
    def shutdown(self):
        """
        Shuts down all the services in the chat engine.
        """
        try:
            self.gui_handler.stop_dispatcher()
            if hasattr(self.discord_dispatcher, 'shutdown'):
                self.discord_dispatcher.shutdown()
            if hasattr(self.driver_manager, 'quit_driver'):
                self.driver_manager.quit_driver()
            else:
                self.driver_manager.shutdown_driver()
            self.feedback_engine.save_feedback_data()
            self.logger.info("Chat Engine Manager shut down successfully")
        except Exception as e:
            self.logger.error(f"Error shutting down Chat Engine Manager: {e}")
    
    # Alias for IChatManager compatibility
    def shutdown_driver(self) -> None:
        """Shutdown all services and cleanly close the driver."""
        self.shutdown()
    
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
        result = self.prompt_executor.send_prompt(prompt)
        if not result:
            self.logger.error("Failed to send prompt")
            return ""
        response = self.prompt_executor.wait_for_stable_response()
        self.logger.info(f"Received response: {response[:100]}...")
        
        # Store the last response
        self._last_response = response
        
        # Dispatch response to Discord if enabled
        discord_enabled = getattr(self.config, "discord_enabled", False) if not hasattr(self.config, "get") else self.config.get("discord_enabled", False)
        if discord_enabled:
            self.discord_dispatcher.dispatch(response)
        self.feedback_engine.process_response(response)
        return response
    
    def get_all_chat_titles(self) -> List[Dict[str, Any]]:
        """Return a list of all available chat titles."""
        return self.scraper_service.get_all_chats()
    
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
        if not self.prompt_executor:
            self.logger.error("Prompt engine not initialized")
            return []
        self.prompt_executor.cycle_speed = cycle_speed
        return self.prompt_executor.execute_prompts_single_chat(prompts)
    
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
            self.logger.error(f"Error switching mode: {e}")
    
    def generate_dreamscape_episode(self, context: Dict[str, Any]) -> Optional[Any]:
        """
        Generate a dreamscape episode using the dreamscape service.
        
        Args:
            context (Dict[str, Any]): The context data for episode generation.
        
        Returns:
            The generated episode data, or None if generation fails.
        """
        if not self.dreamscape_service:
            self.logger.error("Dreamscape service is not available.")
            return None

        try:
            episode = self.dreamscape_service.generate_episode(
                template_name="dreamscape_template.j2",
                context=context
            )
            self.logger.info("Dreamscape episode generated successfully.")
            return episode
        except Exception as e:
            self.logger.error(f"Error generating dreamscape episodes: {e}")
            return None
    
    # --------------------------
    # Orchestration Enhancements
    # --------------------------
    
    def execute_prompt_cycle(self, prompt: str) -> str:
        """
        Execute a complete prompt cycle, optionally with injected context.
        
        Args:
            prompt (str): The prompt to execute.
            
        Returns:
            str: The response.
        """
        self.logger.info("Starting prompt cycle...")
        
        # Inject external context if present
        if self._injected_context:
            enhanced_prompt = f"{prompt}\nContext: {json.dumps(self._injected_context, indent=2)}"
            self.logger.info(f"Enhanced prompt with context: {enhanced_prompt[:100]}...")
            # Clear injected context after use
            self._injected_context = {}
            response = self.send_prompt(enhanced_prompt)
        else:
            response = self.send_prompt(prompt)
        
        return response
    
    def queue_prompts(self, prompts: List[str]) -> None:
        """
        Queue multiple prompts for sequential execution.
        
        Args:
            prompts (List[str]): List of prompts to execute in sequence.
        """
        self.logger.info(f"Queuing {len(prompts)} prompts for sequential execution")
        self._prompt_queue = prompts.copy()
        
        responses = []
        for i, prompt in enumerate(prompts):
            self.logger.info(f"Processing queued prompt {i+1}/{len(prompts)}")
            response = self.execute_prompt_cycle(prompt)
            responses.append(response)
            self.logger.info(f"Completed prompt {i+1}, response: {response[:100]}...")
        
        self.logger.info(f"Completed all {len(prompts)} queued prompts")
        return responses
    
    def get_last_response(self) -> Optional[str]:
        """
        Get the last received prompt response.
        
        Returns:
            Optional[str]: The last response, or None if not available.
        """
        return self._last_response
    
    def inject_context(self, context: Dict[str, Any]) -> None:
        """
        Inject external context into the next prompt.
        
        Args:
            context (Dict[str, Any]): Context data to inject.
        """
        self.logger.info(f"Injecting context: {list(context.keys())}")
        self._injected_context.update(context)
    
    def run_cycle(self, prompt: str, log_feedback: bool = True) -> str:
        """
        Run a complete prompt cycle with feedback logging.
        
        Args:
            prompt (str): The prompt to execute
            log_feedback (bool): Whether to log feedback
            
        Returns:
            str: The response
        """
        # This is now an alias of execute_prompt_cycle for backward compatibility
        response = self.execute_prompt_cycle(prompt)
        if log_feedback and response:
            self.feedback_engine.process_response(response)
        return response
