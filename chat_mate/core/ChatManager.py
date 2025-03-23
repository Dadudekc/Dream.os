from core.chat_engine.driver_manager import DriverManager
from core.chat_engine.chat_scraper_service import ChatScraperService
from core.chat_engine.prompt_execution_service import PromptExecutionService
from core.chat_engine.discord_dispatcher import DiscordDispatcher
from core.chat_engine.feedback_engine import FeedbackEngine

class ChatManager:
    def __init__(self, config, logger):
        self.logger = logger
        self.config = config

        # Initialize core components
        self.driver_manager = DriverManager(config, logger)
        self.chat_scraper = ChatScraperService(self.driver_manager, logger)
        self.prompt_executor = PromptExecutionService(self.driver_manager, logger)
        self.discord_dispatcher = DiscordDispatcher(config, logger)
        self.feedback_engine = FeedbackEngine(config, logger)

    def start(self):
        """Start the chat manager and all services."""
        self.logger.info("🚀 ChatManager starting...")

        self.driver_manager.launch_driver()
        self.logger.info("Driver launched successfully.")

        # Any additional startup routines
        self.feedback_engine.load_feedback_data()

    def send_prompt(self, prompt: str):
        """Send a prompt and handle the response."""
        self.logger.info(f"➡️ Sending prompt: {prompt}")

        self.prompt_executor.send_prompt(prompt)
        response = self.chat_scraper.get_latest_response()

        self.logger.info(f"✅ Received response: {response}")

        # Dispatch response to Discord (if enabled)
        if self.config.discord_enabled:
            self.discord_dispatcher.dispatch(response)

        # Process feedback loop
        self.feedback_engine.process_response(response)

        return response

    def shutdown(self):
        """Cleanly shutdown all services."""
        self.logger.info("🛑 Shutting down ChatManager...")

        self.driver_manager.quit_driver()
        self.feedback_engine.save_feedback_data()

        self.logger.info("✅ Shutdown complete.")
