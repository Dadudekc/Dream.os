from core.chat_engine.chat_cycle_controller import ChatCycleController
from core.chat_engine.chat_scraper_service import ChatScraperService
from core.chat_engine.discord_dispatcher import DiscordDispatcher
from core.chat_engine.driver_manager import DriverManager
from core.chat_engine.feedback_engine import FeedbackEngine
from core.chat_engine.prompt_execution_service import PromptExecutionService
from core.chat_engine.gui_event_handler import GUIEventHandler

class ChatEngineManager:
    """
    Facade for managing the chat engine services.
    This class coordinates the various components of the chat engine.
    """

    def __init__(self):
        """
        Initializes all the services required for the chat engine.
        """
        self.driver_manager = DriverManager()
        self.scraper_service = ChatScraperService(self.driver_manager)
        self.prompt_executor = PromptExecutionService(self.driver_manager)
        self.cycle_controller = ChatCycleController(self.prompt_executor)
        self.feedback_engine = FeedbackEngine()
        self.discord_dispatcher = DiscordDispatcher()
        self.gui_handler = GUIEventHandler(self.discord_dispatcher)

    def start(self):
        """
        Starts all the services in the chat engine.
        """
        try:
            self.driver_manager.initialize_driver()
            self.discord_dispatcher.run_bot()
            self.gui_handler.start_dispatcher()
            print("Chat Engine Manager started successfully.")
        except Exception as e:
            print(f"Error starting Chat Engine Manager: {e}")

    def shutdown(self):
        """
        Shuts down all the services in the chat engine.
        """
        try:
            self.gui_handler.stop_dispatcher()
            self.discord_dispatcher.shutdown()
            self.driver_manager.shutdown_driver()
            print("Chat Engine Manager shut down successfully.")
        except Exception as e:
            print(f"Error shutting down Chat Engine Manager: {e}")
