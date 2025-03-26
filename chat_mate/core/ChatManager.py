from core.chat_engine.driver_manager import DriverManager
from core.chat_engine.chat_scraper_service import ChatScraperService
from core.chat_engine.prompt_execution_service import PromptExecutionService
from core.chat_engine.discord_dispatcher import DiscordDispatcher
from core.chat_engine.feedback_engine import FeedbackEngine
from core.CursorSessionManager import CursorSessionManager
import re

def sanitize_filename(filename):
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename (str): The filename to sanitize
        
    Returns:
        str: The sanitized filename
    """
    # Remove invalid characters for filenames across operating systems
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

class ChatManager:
    def __init__(self, config, logger):
        self.logger = logger
        self.config = config
        self.model = config.get("default_model", "gpt-4o") if hasattr(config, "get") else getattr(config, "default_model", "gpt-4o")

        # Get configuration options
        headless = config.get("headless", True) if hasattr(config, "get") else getattr(config, "headless", True)
        profile_dir = config.get("profile_dir", None) if hasattr(config, "get") else getattr(config, "profile_dir", None)
        cookie_file = config.get("cookie_file", None) if hasattr(config, "get") else getattr(config, "cookie_file", None)
        
        # Get additional Chrome options from config if available
        chrome_options = config.get("chrome_options", []) if hasattr(config, "get") else getattr(config, "chrome_options", [])
        
        # Initialize core components with enhanced DriverManager
        self.driver_manager = DriverManager(
            headless=headless,
            profile_dir=profile_dir,
            cookie_file=cookie_file,
            undetected_mode=True,
            timeout=30,
            additional_options=chrome_options
        )
        
        # Initialize services
        self.chat_scraper = ChatScraperService(self.driver_manager, logger)
        self.prompt_engine = PromptExecutionService(
            self.driver_manager, 
            self.config,  # TODO: Replace with actual prompt manager
            model=self.model
        )
        self.discord_dispatcher = DiscordDispatcher(config, logger)
        self.feedback_engine = FeedbackEngine(config, logger)

        # Initialize CursorSessionManager with enhanced configuration
        cursor_config = {
            "execution_mode": config.get("execution_mode", "full_sync"),
            "cursor_window_title": config.get("cursor_window_title", "Cursor"),
            "prompt_delay": config.get("prompt_delay", 5),
            "hotkeys": config.get("hotkeys", CursorSessionManager.DEFAULT_HOTKEYS)
        }
        self.cursor_manager = CursorSessionManager(cursor_config)

    def start(self):
        """Start the chat manager and all services."""
        self.logger.info("ChatManager starting...")

        self.driver_manager.get_driver()  # Lazy initialize the driver
        self.logger.info("Driver launched successfully.")

        # Any additional startup routines
        self.feedback_engine.load_feedback_data()

    def send_prompt(self, prompt: str):
        """Send a prompt and handle the response."""
        self.logger.info(f"Sending prompt: {prompt}")

        result = self.prompt_engine.send_prompt(prompt)
        if not result:
            self.logger.error("Failed to send prompt")
            return None
            
        response = self.prompt_engine.wait_for_stable_response()
        self.logger.info(f"Received response: {response[:100]}...")

        # Dispatch response to Discord (if enabled)
        discord_enabled = self.config.get("discord_enabled", False) if hasattr(self.config, "get") else getattr(self.config, "discord_enabled", False)
        if discord_enabled:
            self.discord_dispatcher.dispatch(response)

        # Process feedback loop
        self.feedback_engine.process_response(response)

        return response
        
    def get_all_chat_titles(self):
        """Get all available chat titles."""
        return self.chat_scraper.get_all_chats()
        
    def execute_prompts_single_chat(self, prompt_list, cycle_speed=2):
        """Execute multiple prompts in a single chat."""
        if not self.prompt_engine:
            self.logger.error("Prompt engine not initialized")
            return []
            
        self.prompt_engine.cycle_speed = cycle_speed
        return self.prompt_engine.execute_prompts_single_chat(prompt_list)
        
    def analyze_execution_response(self, response, prompt_text):
        """Analyze the execution response."""
        # Simple analysis for now
        return {
            "length": len(response),
            "has_code": "```" in response,
            "sentiment": "neutral"
        }

    def shutdown_driver(self):
        """Cleanly shutdown all services."""
        self.logger.info("Shutting down ChatManager...")

        if hasattr(self.driver_manager, 'quit_driver'):
            self.driver_manager.quit_driver()
        else:
            self.driver_manager.shutdown_driver()
            
        self.feedback_engine.save_feedback_data()

        self.logger.info("Shutdown complete.")

    def send_chat_prompt(self, task, context=None):
        prompt = self.cursor_manager.generate_prompt(task, context)
        try:
            generated_code = self.cursor_manager.execute_prompt(prompt)
            return generated_code
        except RuntimeError as e:
            self.logger.error(f"Failed to execute prompt: {e}")
            # Handle error (e.g., retry, notify user)
            return None

    def switch_execution_mode(self, mode):
        try:
            self.cursor_manager.switch_mode(mode)
            self.logger.info(f"Switched execution mode to {mode}")
        except ValueError as e:
            self.logger.error(e)
            # Handle invalid mode (e.g., notify user)
