import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import QWidget

from core.CycleExecutionService import CycleExecutionService
from core.PromptResponseHandler import PromptResponseHandler
from core.services.discord.DiscordQueueProcessor import DiscordQueueProcessor
from core.TaskOrchestrator import TaskOrchestrator
from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator
from core.TemplateManager import TemplateManager
from interfaces.pyqt.tabs.dreamscape_generation.ContextManager import ContextManager
from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager
from core.PathManager import PathManager
from core.services.dreamscape_generator_service import DreamscapeGenerationService


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

    def __init__(self, parent_widget: Optional[QWidget] = None, config_manager = None, logger: Optional[logging.Logger] = None):
        self.parent_widget = parent_widget
        self.config_service = config_manager
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

        # Service registry instance for accessing global services
        try:
            from core.services.service_registry import ServiceRegistry
            self.service_registry = ServiceRegistry()
        except ImportError:
            self.logger.warning("❌ ServiceRegistry not available")
            self.service_registry = None

    def initialize_services(self, prompt_manager=None, chat_manager=None, response_handler=None,
                            memory_manager=None, discord_manager=None, ui_logic=None):
        """
        Initialize services with externally provided instances.
        This method is called from DreamscapeGenerationTab to inject dependencies.
        """
        try:
            # Store injected services
            self.prompt_manager = prompt_manager
            self.chat_manager = chat_manager
            self.response_handler = response_handler
            self.memory_manager = memory_manager
            self.discord_manager = discord_manager
            
            # Now initialize the rest of services
            self.initialize_all()
            
            # Return initialized services for the tab to use
            return self._get_initialized_services()
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing services: {str(e)}")
            return {
                'core_services': {},
                'component_managers': {},
                'output_dir': None
            }

    def initialize_all(self):
        """Initialize all required services and component managers."""
        try:
            # Core services via service registry
            self.initialize_core_services()
            
            # Component managers
            self.initialize_component_managers()
            
            # Set up dependencies
            self.wire_dependencies()
            
            self.logger.info("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing services: {str(e)}")
            return False

    def initialize_core_services(self):
        """Initialize core services using service registry if available."""
        try:
            # Try to get services from registry
            if self.service_registry:
                self.logger.info("Initializing core services from service registry...")
                if not self.config_service:
                    self.config_service = self.service_registry.get("config_manager")
                if not self.chat_manager:
                    self.chat_manager = self.service_registry.get("chat_manager")
                if not self.task_orchestrator:
                    self.task_orchestrator = self.service_registry.get("task_orchestrator")
                if not self.prompt_manager:
                    self.prompt_manager = self.service_registry.get("prompt_manager")
                if not self.discord_manager:
                    self.discord_manager = self.service_registry.get("discord_manager")
                
            # Fall back to direct initialization if registry not available
            else:
                self.logger.info("Service registry not available, initializing services directly...")
                self.initialize_config_service()
                self.initialize_chat_manager()
                
            self.logger.info("✅ Core services initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing core services: {str(e)}")
            raise
    
    def initialize_config_service(self):
        """Initialize ConfigManager if needed."""
        if not self.config_service:
            try:
                from config.ConfigManager import ConfigManager
                self.config_service = ConfigManager()
                self.logger.info("✅ ConfigManager initialized directly")
            except ImportError:
                self.logger.error("❌ Cannot import ConfigManager")
                
    def initialize_chat_manager(self):
        """Initialize ChatManager if needed."""
        if not self.chat_manager:
            try:
                from core.ChatManager import ChatManager
                
                # Default headless mode for UI usage
                self.chat_manager = ChatManager(
                    driver_options={
                        "headless": True,
                        "window_size": (1920, 1080)
                    },
                    model="gpt-4o",
                    headless=True
                )
                self.logger.info("✅ ChatManager initialized directly")
            except ImportError:
                self.logger.error("❌ Cannot import ChatManager")
    
    def initialize_component_managers(self):
        """Initialize component-specific managers."""
        self.output_dir = "outputs/dreamscape"
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize DreamscapeGenerationService
        try:
            path_manager = PathManager()
            template_manager = self.initialize_template_manager()
            
            self.dreamscape_generator = DreamscapeGenerationService(
                path_manager=path_manager,
                template_manager=template_manager,
                logger=self.logger
            )
            self.logger.info("✅ DreamscapeGenerationService initialized successfully")
            
            # Set the dreamscape service on the chat manager if available
            if self.chat_manager:
                self.chat_manager.dreamscape_service = self.dreamscape_generator
                self.logger.info("✅ Dreamscape service set on chat manager")
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing DreamscapeGenerationService: {str(e)}")
            self.dreamscape_generator = None
    
    def initialize_template_manager(self):
        """Initialize TemplateManager with the path to dreamscape templates."""
        try:
            base_dir = os.getcwd()
            dreamscape_dir = os.path.join(base_dir, 'templates', 'dreamscape_templates')
            template_manager = TemplateManager(template_dir=dreamscape_dir)
            template_manager.load_templates()
            self.template_manager = template_manager
            self.logger.info("✅ TemplateManager initialized successfully")
            return template_manager
        except Exception as e:
            self.logger.error(f"❌ Error initializing TemplateManager: {str(e)}")
            self.template_manager = None
            return None
    
    def wire_dependencies(self):
        """Wire dependencies between services."""
        try:
            # Set dreamscape service on chat manager if needed
            if self.chat_manager and self.dreamscape_generator and not self.chat_manager.dreamscape_service:
                self.chat_manager.dreamscape_service = self.dreamscape_generator
                self.logger.info("✅ Wired dreamscape service to chat manager")
        except Exception as e:
            self.logger.error(f"❌ Error wiring dependencies: {str(e)}")
    
    def get_chat_manager(self):
        """Get the initialized chat manager instance."""
        return self.chat_manager
    
    def get_template_manager(self):
        """Get the initialized template manager instance."""
        return self.template_manager
    
    def get_dreamscape_generator(self):
        """Get the initialized dreamscape generator service."""
        return self.dreamscape_generator

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
                config_manager=self.config_service,
                logger=self.logger
            )
            self.logger.info("✅ CycleExecutionService initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing CycleExecutionService: {str(e)}")
            self.cycle_service = None

        # Initialize PromptResponseHandler
        try:
            self.prompt_handler = PromptResponseHandler(
                config_manager=self.config_service,
                logger=self.logger
            )
            self.logger.info("✅ PromptResponseHandler initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing PromptResponseHandler: {str(e)}")
            self.prompt_handler = None

        # Initialize DiscordQueueProcessor
        try:
            self.discord_processor = DiscordQueueProcessor(
                config_manager=self.config_service,
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

        # Initialize DreamscapeEpisodeGenerator
        try:
            self.episode_generator = DreamscapeEpisodeGenerator(
                parent_widget=self.parent_widget,
                template_manager=self.template_manager,
                output_dir=self.output_dir,
                logger=self.logger
            )
            self.logger.info("✅ DreamscapeEpisodeGenerator initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing DreamscapeEpisodeGenerator: {str(e)}")
            self.episode_generator = None

    def _initialize_component_managers(self) -> None:
        """
        Initialize component-specific managers like ContextManager and UIManager.
        """
        # Initialize ContextManager
        try:
            self.context_manager = ContextManager(
                parent_widget=self.parent_widget,
                logger=self.logger
            )
            self.logger.info("✅ ContextManager initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing ContextManager: {str(e)}")
            self.context_manager = None

        # Initialize UIManager
        try:
            self.ui_manager = UIManager(
                parent_widget=self.parent_widget,
                logger=self.logger
            )
            self.logger.info("✅ UIManager initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Error initializing UIManager: {str(e)}")
            self.ui_manager = None

    def _get_output_directory(self) -> str:
        """
        Determine and ensure the output directory exists.
        """
        output_dir = os.path.join(os.getcwd(), "outputs", "dreamscape")
        os.makedirs(output_dir, exist_ok=True)
        self.logger.info(f"✅ Output directory ensured: {output_dir}")
        return output_dir

    def _get_initialized_services(self) -> Dict[str, Any]:
        """
        Returns a dictionary of all initialized services and component managers.
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
