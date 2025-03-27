import os
import logging
from typing import Dict, Any, Optional

from core.CycleExecutionService import CycleExecutionService
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.TaskOrchestrator import TaskOrchestrator
from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator
from core.TemplateManager import TemplateManager
from interfaces.pyqt.tabs.dreamscape_generation.ContextManager import ContextManager
from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager


class ServiceInitializer:
    """
    ServiceInitializer encapsulates the initialization of all services required by
    the DreamscapeGenerationTab. It handles:
      - Injecting external services (or retrieving them from a ui_logic container).
      - Initializing core services (CycleExecutionService, PromptResponseHandler, DiscordQueueProcessor,
        TaskOrchestrator, DreamscapeEpisodeGenerator).
      - Setting up component managers (TemplateManager, DreamscapeEpisodeGenerator, ContextManager, UIManager).
      - Determining and ensuring the output directory exists.
      
    After initialization, it returns a dictionary of initialized services and component managers.
    """

    def __init__(self, parent: Any, config_manager: Any, logger: Optional[logging.Logger] = None):
        self.parent = parent
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # External services (to be injected)
        self.prompt_manager = None
        self.chat_manager = None
        self.response_handler = None
        self.memory_manager = None
        self.discord_manager = None
        
        # Core services
        self.cycle_service = None
        self.prompt_handler = None
        self.discord_processor = None
        self.task_orchestrator = None
        self.dreamscape_generator = None
        
        # Component managers
        self.template_manager = None
        self.episode_generator = None
        self.context_manager = None
        self.ui_manager = None
        
        # Output directory path
        self.output_dir = None

    def initialize_services(self, prompt_manager: Any, chat_manager: Any, response_handler: Any,
                            memory_manager: Any, discord_manager: Any, ui_logic: Optional[Any] = None) -> Dict[str, Any]:
        """
        Initialize all required services and component managers.

        Args:
            prompt_manager: External prompt management service.
            chat_manager: Service handling chat interactions.
            response_handler: Service processing responses.
            memory_manager: Service managing context or memory.
            discord_manager: Service handling Discord integration.
            ui_logic: Optional UI logic service for service retrieval.

        Returns:
            A dictionary with keys 'core_services', 'component_managers', and 'output_dir'.
        """
        self._inject_services(prompt_manager, chat_manager, response_handler, memory_manager, discord_manager, ui_logic)
        self._initialize_core_services()
        self._initialize_component_managers()
        return self._get_initialized_services()

    def _inject_services(self, prompt_manager: Any, chat_manager: Any, response_handler: Any,
                         memory_manager: Any, discord_manager: Any, ui_logic: Optional[Any]) -> None:
        """
        Inject or retrieve external services.

        Args:
            prompt_manager: External prompt management service.
            chat_manager: Chat service.
            response_handler: Response processing service.
            memory_manager: Memory/context management service.
            discord_manager: Discord integration service.
            ui_logic: Optional UI logic service providing a get_service() method.
        """
        try:
            if ui_logic and hasattr(ui_logic, 'get_service'):
                self.prompt_manager = ui_logic.get_service('prompt_manager') or prompt_manager
                self.chat_manager = ui_logic.get_service('chat_manager') or chat_manager
                self.response_handler = ui_logic.get_service('response_handler') or response_handler
                self.memory_manager = ui_logic.get_service('memory_manager') or memory_manager
                self.discord_manager = ui_logic.get_service('discord_service') or discord_manager
            else:
                self.prompt_manager = prompt_manager
                self.chat_manager = chat_manager
                self.response_handler = response_handler
                self.memory_manager = memory_manager
                self.discord_manager = discord_manager

            if not all([self.chat_manager, self.response_handler]):
                self.logger.warning("⚠️ Warning: Some core services are not initialized.")
        except Exception as e:
            self.logger.error(f"❌ Error injecting services: {str(e)}")
            raise

    def _initialize_core_services(self) -> None:
        """
        Initialize core processing services such as CycleExecutionService, PromptResponseHandler,
        DiscordQueueProcessor, TaskOrchestrator, and DreamscapeEpisodeGenerator.
        Also determines the output directory.
        """
        # Initialize CycleExecutionService
        try:
            self.cycle_service = CycleExecutionService(
                prompt_manager=self.prompt_manager,
                chat_manager=self.chat_manager,
                response_handler=self.response_handler,
                memory_manager=self.memory_manager,
                discord_manager=self.discord_manager,
                config_manager=self.config_manager,
                logger=self.logger
            )
            self.logger.info("✅ CycleExecutionService initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing CycleExecutionService: {str(e)}")
            self.cycle_service = None

        # Initialize PromptResponseHandler
        try:
            self.prompt_handler = PromptResponseHandler(
                config_manager=self.config_manager,
                logger=self.logger
            )
            self.logger.info("✅ PromptResponseHandler initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing PromptResponseHandler: {str(e)}")
            self.prompt_handler = None

        # Initialize DiscordQueueProcessor
        try:
            self.discord_processor = DiscordQueueProcessor(
                config_manager=self.config_manager,
                logger=self.logger
            )
            self.logger.info("✅ DiscordQueueProcessor initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing DiscordQueueProcessor: {str(e)}")
            self.discord_processor = None

        # Initialize TaskOrchestrator
        try:
            self.task_orchestrator = TaskOrchestrator(
                logger=self.logger
            )
            self.logger.info("✅ TaskOrchestrator initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing TaskOrchestrator: {str(e)}")
            self.task_orchestrator = None

        # Determine output directory and ensure it exists
        try:
            self.output_dir = self._get_output_directory()
            os.makedirs(self.output_dir, exist_ok=True)
            self.logger.info(f"✅ Output directory set to: {self.output_dir}")
        except Exception as e:
            self.logger.error(f"❌ Error setting up output directory: {str(e)}")
            self.output_dir = "outputs/dreamscape"

        # Initialize DreamscapeEpisodeGenerator (core service)
        try:
            self.dreamscape_generator = DreamscapeEpisodeGenerator(
                chat_manager=self.chat_manager,
                response_handler=self.response_handler,
                output_dir=self.output_dir,
                discord_manager=self.discord_manager
            )
            self.logger.info("✅ DreamscapeEpisodeGenerator initialized successfully (core service)")
        except Exception as e:
            self.logger.error(f"❌ Error initializing DreamscapeEpisodeGenerator (core service): {str(e)}")
            self.dreamscape_generator = None

    def _initialize_component_managers(self) -> None:
        """
        Initialize component managers responsible for UI and context tasks.
        """
        try:
            # Initialize TemplateManager with the path to dreamscape templates.
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            dreamscape_dir = os.path.join(base_dir, 'templates', 'dreamscape_templates')
            self.template_manager = TemplateManager(template_dir=dreamscape_dir)
            self.logger.info("✅ TemplateManager initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing TemplateManager: {str(e)}")
            self.template_manager = None

        try:
            # Instantiate DreamscapeEpisodeGenerator for component manager use,
            # Note: This is a separate instance with additional UI parameters.
            self.episode_generator = DreamscapeEpisodeGenerator(
                parent_widget=self.parent,
                logger=self.logger,
                chat_manager=self.chat_manager,
                config_manager=self.config_manager
            )
            self.logger.info("✅ EpisodeGenerator (component manager) initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing EpisodeGenerator (component manager): {str(e)}")
            self.episode_generator = None

        try:
            self.context_manager = ContextManager(
                parent_widget=self.parent,
                logger=self.logger,
                chat_manager=self.chat_manager,
                dreamscape_generator=self.dreamscape_generator,
                template_manager=self.template_manager
            )
            self.logger.info("✅ ContextManager initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing ContextManager: {str(e)}")
            self.context_manager = None

        try:
            self.ui_manager = UIManager(
                parent_widget=self.parent,
                logger=self.logger,
                episode_list=getattr(self.parent, 'episode_list', None),
                template_manager=self.template_manager,
                output_dir=self.output_dir
            )
            self.logger.info("✅ UIManager initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing UIManager: {str(e)}")
            self.ui_manager = None

    def _get_output_directory(self) -> str:
        """
        Retrieve the output directory from the config_manager or default to "outputs/dreamscape".
        
        Returns:
            The output directory path as a string.
        """
        try:
            if hasattr(self.config_manager, "get"):
                return self.config_manager.get("dreamscape_output_dir", "outputs/dreamscape")
            return getattr(self.config_manager, "dreamscape_output_dir", "outputs/dreamscape")
        except Exception as e:
            self.logger.warning(f"⚠️ Warning: Using default output directory due to error: {str(e)}")
            return "outputs/dreamscape"

    def _get_initialized_services(self) -> Dict[str, Any]:
        """
        Package and return all initialized core services and component managers.

        Returns:
            Dictionary with keys 'core_services', 'component_managers', and 'output_dir'.
        """
        return {
            'core_services': {
                'cycle_service': self.cycle_service,
                'prompt_handler': self.prompt_handler,
                'discord_processor': self.discord_processor,
                'task_orchestrator': self.task_orchestrator,
                'dreamscape_generator': self.dreamscape_generator
            },
            'component_managers': {
                'template_manager': self.template_manager,
                'episode_generator': self.episode_generator,
                'context_manager': self.context_manager,
                'ui_manager': self.ui_manager
            },
            'output_dir': self.output_dir
        }
