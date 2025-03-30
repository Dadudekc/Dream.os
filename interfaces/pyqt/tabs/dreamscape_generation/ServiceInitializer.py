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
from config.ConfigManager import ConfigManager
from core.services.prompt_context_synthesizer import PromptContextSynthesizer
from core.ChatManager import ChatManager


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
        self.config_manager = config_manager or ConfigManager()
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
            
            # If prompt_manager is not provided, try to create it using our PromptFactory
            if self.prompt_manager is None:
                try:
                    from core.factories.prompt_factory import PromptFactory
                    # Try to create using the service registry if available
                    if self.service_registry:
                        self.logger.info("Creating PromptManager using PromptFactory with registry...")
                        self.prompt_manager = PromptFactory.create(self.service_registry)
                        if self.prompt_manager:
                            self.logger.info("PromptManager created successfully via factory with registry")
                    
                    # If still None, try the standalone factory method
                    if self.prompt_manager is None:
                        self.logger.info("Creating PromptManager using standalone factory method...")
                        self.prompt_manager = PromptFactory.create_prompt_manager(logger=self.logger)
                        if self.prompt_manager:
                            self.logger.info("PromptManager created successfully via standalone factory")
                    
                    # If still None, create with defaults as last resort
                    if self.prompt_manager is None:
                        self.logger.warning("All factory methods failed, creating AletheiaPromptManager directly")
                        from core.AletheiaPromptManager import AletheiaPromptManager
                        self.prompt_manager = AletheiaPromptManager()
                except Exception as e:
                    self.logger.error(f"Failed to create PromptManager: {e}")
            
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
        """
        Initialize all required services and component managers.
        
        Returns:
            A dictionary of initialized services
        """
        self.logger.info("Initializing all services and component managers...")
        
        try:
            # Initialize core services
            core_services = self.initialize_core_services()
            
            # Initialize component managers
            component_managers = self.initialize_component_managers(core_services)
            
            # Wire up dependencies
            self._wire_dependencies(core_services, component_managers)
            
            # Store all services
            self.services = {**core_services, **component_managers}
            
            self.logger.info("All services and component managers initialized successfully.")
            return self.services
            
        except Exception as e:
            self.logger.error(f"Error initializing services: {e}")
            raise

    def initialize_core_services(self, service_registry=None):
        """
        Initialize core services.
        
        Args:
            service_registry: Existing service registry to use, if available
            
        Returns:
            A dictionary of initialized core services
        """
        self.logger.info("Initializing core services...")
        
        # Use existing services from registry if available
        if service_registry:
            self.logger.info("Using existing services from registry...")
            config_manager = service_registry.get("config_manager") or self.config_manager
            chat_manager = service_registry.get("chat_manager")
            
            services = {}
            if config_manager:
                services["config_manager"] = config_manager
            if chat_manager:
                services["chat_manager"] = chat_manager
                
            # Don't reinitialize existing services
            if services:
                self.logger.info(f"Reusing {len(services)} services from registry")
                return services
        
        # Initialize config manager if not already created
        config_manager = self.config_manager
        
        # Initialize path manager
        path_manager = PathManager()
        
        # Initialize template manager
        template_dir = os.path.join(os.getcwd(), "templates", "dreamscape_templates")
        template_manager = TemplateManager(template_dir=template_dir)
        
        # Initialize context synthesizer
        memory_path = path_manager.get_path("memory") / "dreamscape_memory.json"
        chain_path = path_manager.get_path("memory") / "episode_chain.json"
        conversation_memory_path = path_manager.get_path("memory") / "conversation_memory.json"
        
        context_synthesizer = PromptContextSynthesizer(
            memory_path=memory_path,
            chain_path=chain_path, 
            conversation_memory_path=conversation_memory_path,
            logger=self.logger
        )
        
        # Initialize dreamscape generation service
        dreamscape_service = DreamscapeGenerationService(
            path_manager=path_manager,
            template_manager=template_manager,
            logger=self.logger
        )
        
        # Combine all core services
        core_services = {
            "config_manager": config_manager,
            "path_manager": path_manager,
            "template_manager": template_manager,
            "context_synthesizer": context_synthesizer,
            "dreamscape_service": dreamscape_service
        }
        
        self.logger.info(f"Initialized {len(core_services)} core services.")
        return core_services
    
    def initialize_component_managers(self, core_services):
        """
        Initialize component managers.
        
        Args:
            core_services: Dictionary of core services to use for initialization
            
        Returns:
            A dictionary of initialized component managers
        """
        self.logger.info("Initializing component managers...")
        
        # Get required core services
        config_manager = core_services.get("config_manager")
        path_manager = core_services.get("path_manager")
        template_manager = core_services.get("template_manager")
        dreamscape_service = core_services.get("dreamscape_service")
        
        # Get output directory
        output_dir = self._get_output_directory()
        
        # Create a component_managers dictionary to store all managers
        component_managers = {}
        
        try:
            # Initialize template manager to use in UI
            if not template_manager:
                # If not provided in core_services, create a new one
                template_dir = path_manager.get_template_path("dreamscape_templates") if path_manager else "templates/dreamscape_templates"
                template_manager = TemplateManager(template_dir=template_dir, logger=self.logger)
                self.logger.info(f"Created template manager for directory: {template_dir}")
            
            component_managers["template_manager"] = template_manager
            
            # Initialize episode generator
            from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator
            
            episode_generator = DreamscapeEpisodeGenerator(
                parent_widget=self.parent_widget,
                prompt_manager=self.prompt_manager,
                chat_manager=self.chat_manager,
                dreamscape_service=dreamscape_service,
                output_dir=output_dir,
                logger=self.logger
            )
            component_managers["episode_generator"] = episode_generator
            
            # Initialize context manager
            from interfaces.pyqt.tabs.dreamscape_generation.ContextManager import ContextManager
            
            context_manager = ContextManager(
                parent_widget=self.parent_widget,
                prompt_manager=self.prompt_manager,
                chat_manager=self.chat_manager,
                template_manager=template_manager,
                dreamscape_service=dreamscape_service,
                output_dir=output_dir,
                logger=self.logger
            )
            component_managers["context_manager"] = context_manager
            
            # Initialize UI manager using the micro-factory pattern
            try:
                from core.micro_factories.ui_manager_factory import create as create_ui_manager
                
                # Get the episode list widget from the parent if available
                episode_list = None
                if hasattr(self.parent_widget, 'episode_list'):
                    episode_list = self.parent_widget.episode_list
                
                ui_manager = create_ui_manager(
                    parent_widget=self.parent_widget,
                    logger=self.logger,
                    episode_list=episode_list,
                    template_manager=template_manager,
                    output_dir=output_dir
                )
                
                if ui_manager:
                    self.logger.info("✅ UIManager created successfully via factory")
                    component_managers["ui_manager"] = ui_manager
                else:
                    self.logger.warning("⚠️ UIManager factory returned None")
            except Exception as e:
                self.logger.error(f"❌ Failed to create UIManager using factory: {e}")
                # Fallback to direct instantiation
                try:
                    from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager
                    episode_list = None
                    if hasattr(self.parent_widget, 'episode_list'):
                        episode_list = self.parent_widget.episode_list
                        
                    ui_manager = UIManager(
                        parent_widget=self.parent_widget,
                        logger=self.logger,
                        episode_list=episode_list,
                        template_manager=template_manager,
                        output_dir=output_dir
                    )
                    component_managers["ui_manager"] = ui_manager
                    self.logger.info("✅ UIManager created using direct instantiation")
                except Exception as e2:
                    self.logger.error(f"❌ Failed to create UIManager directly: {e2}")
            
            # Store output directory in component_managers
            component_managers["output_dir"] = output_dir
            
            self.logger.info(f"Initialized {len(component_managers)} component managers.")
            return component_managers
            
        except Exception as e:
            self.logger.error(f"Error initializing component managers: {e}")
            # Return whatever was initialized
            return component_managers
    
    def _wire_dependencies(self, core_services, component_managers):
        """
        Wire up dependencies between services.
        
        Args:
            core_services: Dictionary of core services
            component_managers: Dictionary of component managers
        """
        self.logger.info("Wiring dependencies between services...")
        
        # Connect dreamscape service to chat manager
        dreamscape_service = core_services.get("dreamscape_service")
        context_synthesizer = core_services.get("context_synthesizer")
        chat_manager = component_managers.get("chat_manager")
        
        if dreamscape_service and chat_manager:
            chat_manager.dreamscape_service = dreamscape_service
            self.logger.info("Connected DreamscapeGenerationService to ChatManager.")
        
        # Connect context synthesizer to dreamscape service
        if dreamscape_service and context_synthesizer:
            dreamscape_service.context_synthesizer = context_synthesizer
            self.logger.info("Connected PromptContextSynthesizer to DreamscapeGenerationService.")
        
        # Add additional wiring as needed

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
        Initialize all component managers.
        
        This method is called during initialization and sets up:
        - TemplateManager
        - EpisodeGenerator
        - ContextManager
        - UIManager
        """
        try:
            # Get output directory
            self.output_dir = self._get_output_directory()
            
            # Initialize template manager
            template_dir = os.path.join(os.getcwd(), "templates", "dreamscape_templates")
            self.template_manager = TemplateManager(template_dir=template_dir, logger=self.logger)
            
            # Initialize episode generator
            self.episode_generator = DreamscapeEpisodeGenerator(
                parent_widget=self.parent_widget,
                prompt_manager=self.prompt_manager,
                chat_manager=self.chat_manager,
                dreamscape_service=self.dreamscape_generator,
                output_dir=self.output_dir,
                logger=self.logger
            )
            
            # Initialize context manager
            self.context_manager = ContextManager(
                parent_widget=self.parent_widget,
                prompt_manager=self.prompt_manager,
                chat_manager=self.chat_manager,
                template_manager=self.template_manager,
                dreamscape_service=self.dreamscape_generator,
                output_dir=self.output_dir,
                logger=self.logger
            )
            
            # Initialize UI manager using the micro-factory pattern
            try:
                from core.micro_factories.ui_manager_factory import create as create_ui_manager
                
                # Get the episode list widget from the parent if available
                episode_list = None
                if hasattr(self.parent_widget, 'episode_list'):
                    episode_list = self.parent_widget.episode_list
                
                self.ui_manager = create_ui_manager(
                    parent_widget=self.parent_widget,
                    logger=self.logger,
                    episode_list=episode_list,
                    template_manager=self.template_manager,
                    output_dir=self.output_dir
                )
                
                if self.ui_manager:
                    self.logger.info("✅ UIManager created successfully via factory")
                else:
                    self.logger.warning("⚠️ UIManager factory returned None")
            except Exception as e:
                self.logger.error(f"❌ Failed to create UIManager using factory: {e}")
                # Fallback to direct instantiation
                try:
                    from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager
                    episode_list = None
                    if hasattr(self.parent_widget, 'episode_list'):
                        episode_list = self.parent_widget.episode_list
                        
                    self.ui_manager = UIManager(
                        parent_widget=self.parent_widget,
                        logger=self.logger,
                        episode_list=episode_list,
                        template_manager=self.template_manager,
                        output_dir=self.output_dir
                    )
                    self.logger.info("✅ UIManager created using direct instantiation")
                except Exception as e2:
                    self.logger.error(f"❌ Failed to create UIManager directly: {e2}")
                    self.ui_manager = None
            
            self.logger.info("Component managers initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing component managers: {e}")
            # Ensure we have at least empty managers to avoid NoneType errors
            self.template_manager = self.template_manager or TemplateManager()
            self.episode_generator = self.episode_generator or None
            self.context_manager = self.context_manager or None
            self.ui_manager = self.ui_manager or None

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
