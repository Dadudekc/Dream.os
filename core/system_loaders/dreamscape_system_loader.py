# core/system_loaders/dreamscape_system_loader.py

import logging
import os
from typing import Optional, Dict, Any
import time

# Core services and managers
from config.ConfigManager import ConfigManager
from core.PathManager import PathManager
from core.services.service_registry import ServiceRegistry
from core.services.dreamscape_generator_service import DreamscapeGenerationService

# Import factories
from core.factories.prompt_manager_factory import PromptManagerFactory
from core.factories.openai_client_factory import OpenAIClientFactory
from core.factories.chat_manager_factory import ChatManagerFactory
from core.micro_factories.template_manager_factory import TemplateManagerFactory
from core.micro_factories.context_manager_factory import ContextManagerFactory
from core.micro_factories.episode_generator_factory import EpisodeGeneratorFactory
from core.micro_factories.ui_manager_factory import UIManagerFactory

class DreamscapeSystemLoader:
    """
    Handles the initialization and wiring of all components required 
    for the Dreamscape generation subsystem.
    """
    def __init__(self, 
                 config_manager: Optional[ConfigManager] = None,
                 path_manager: Optional[PathManager] = None,
                 service_registry: Optional[ServiceRegistry] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the loader with essential shared services.

        Args:
            config_manager: The application's configuration manager.
            path_manager: The application's path manager.
            service_registry: The application's service registry.
            logger: An optional logger instance.
        """
        self.logger = logger or logging.getLogger("DreamscapeSystemLoader")
        
        # Use provided instances or create defaults
        self.config_manager = config_manager or ConfigManager()
        self.path_manager = path_manager or PathManager()
        self.service_registry = service_registry or ServiceRegistry()
        
        self.logger.info("DreamscapeSystemLoader initialized.")

    def load(self, 
             parent_widget=None,
             prompt_manager=None,
             chat_manager=None,
             headless=False,
             test_mode=False) -> ServiceRegistry:
        """
        Loads all Dreamscape components, wires them, and registers them.

        Args:
            parent_widget: The parent UI widget (e.g., DreamscapeGenerationTab).
            prompt_manager: Optional externally created PromptManager.
            chat_manager: Optional externally created ChatManager.
            headless: Flag for headless operation (passed down).
            test_mode: Flag for test mode (passed down).

        Returns:
            The service registry containing all loaded components.
        """
        self.logger.info(f"🔧 Loading Dreamscape system components... (Headless: {headless}, Test Mode: {test_mode})")

        # --- Initialize Core Services ---
        # Create PromptManager if not provided
        if not prompt_manager:
            self.logger.info("Creating PromptManager via factory...")
            prompt_manager = PromptManagerFactory.create(service_registry=self.service_registry)
            if prompt_manager:
                self.service_registry.register("prompt_manager", prompt_manager)
                self.logger.info("✅ PromptManager created and registered")
            else:
                self.logger.error("❌ Failed to create PromptManager")
                return self.service_registry

        # Create OpenAIClient and ChatManager if not provided
        if not chat_manager:
            self.logger.info("Creating OpenAIClient and ChatManager via factories...")
            openai_client = OpenAIClientFactory.create(
                service_registry=self.service_registry,
                headless=headless
            )
            if not openai_client:
                self.logger.error("❌ Failed to create OpenAIClient")
                return self.service_registry

            self.service_registry.register("openai_client", openai_client)
            
            chat_manager = ChatManagerFactory.create_chat_manager(
                openai_client=openai_client,
                config_manager=self.config_manager,
                logger=self.logger,
                service_registry=self.service_registry,
                headless=headless
            )
            if chat_manager:
                self.service_registry.register("chat_manager", chat_manager)
                self.logger.info("✅ ChatManager created and registered")
            else:
                self.logger.error("❌ Failed to create ChatManager")
                return self.service_registry

        # --- Initialize Template Manager ---
        template_manager = TemplateManagerFactory.create_template_manager(
            logger_instance=self.logger,
            path_manager=self.path_manager
        )
        if not template_manager:
            self.logger.error("❌ Failed to create TemplateManager. Aborting load.")
            return self.service_registry

        self.service_registry.register("template_manager", template_manager)
        self.logger.info("✅ TemplateManager created and registered")

        # --- Initialize Dreamscape Service ---
        dreamscape_service = DreamscapeGenerationService(
            path_manager=self.path_manager,
            template_manager=template_manager,
            logger=self.logger
        )
        self.service_registry.register("dreamscape_service", dreamscape_service)
        self.logger.info("✅ DreamscapeGenerationService created and registered")

        # --- Set Up Output Directory ---
        output_dir = os.path.join(self.path_manager.get_path("outputs"), "dreamscape")
        os.makedirs(output_dir, exist_ok=True)
        self.service_registry.register("output_dir", output_dir)

        # --- ADDED DEBUG --- 
        # --- END DEBUG ---

        # --- Initialize Component Managers ---
        context_manager = None # Initialize to None
        episode_generator = None # Initialize to None
        ui_manager = None # Initialize to None

        # Context Manager
        try:
            self.logger.info("Attempting to create ContextManager...")
            context_manager = ContextManagerFactory.create_context_manager(
                parent_widget=parent_widget,
                logger_instance=self.logger,
                chat_manager=chat_manager,
                dreamscape_service=dreamscape_service,
                template_manager=template_manager
            )
            if context_manager:
                self.service_registry.register("context_manager", context_manager)
                self.logger.info("✅ ContextManager created and registered")
            else:
                self.logger.error("❌ ContextManager creation returned None")
        except Exception as e:
            self.logger.error(f"❌ ContextManagerFactory failed with args: parent_widget={parent_widget}, chat_manager={chat_manager}, dreamscape_service={dreamscape_service}, template_manager={template_manager}")
            self.logger.exception("Full exception trace:")
            # context_manager remains None
        
        self.logger.info(f"ContextManager creation finished. Instance: {context_manager}")

        # Episode Generator
        try:
            self.logger.info("Attempting to create EpisodeGenerator...")
            episode_generator = EpisodeGeneratorFactory.create_episode_generator(
                parent_widget=parent_widget,
                prompt_manager=prompt_manager,
                chat_manager=chat_manager,
                dreamscape_service=dreamscape_service,
                output_dir=output_dir,
                logger_instance=self.logger
            )
            if episode_generator:
                # --- Wrap registration in try...except ---
                try:
                    self.service_registry.register("episode_generator", episode_generator)
                    self.logger.info("✅ EpisodeGenerator created and registered")
                except Exception as reg_e:
                    self.logger.error(f"❌ Failed during EpisodeGenerator REGISTRATION: {reg_e}", exc_info=True)
                    episode_generator = None # Ensure it's None if registration fails
                # --- End wrap ---
            else:
                self.logger.error("❌ EpisodeGenerator creation returned None")
        except Exception as factory_e:
            self.logger.error(f"❌ EpisodeGeneratorFactory failed: {factory_e}", exc_info=True)
            # episode_generator remains None

        self.logger.info(f"EpisodeGenerator processing finished. Instance: {episode_generator}")

        # UI Manager (Optional)
        # --- Remove delay ---
        # import time # No longer needed
        # time.sleep(0.1) 
        
        # Ensure parent has the necessary base attribute before proceeding
        if parent_widget and UIManagerFactory: # Simplified check
            try:
                self.logger.info("Attempting to create UIManager...")
                ui_manager = UIManagerFactory.create_dreamscape_ui_manager(
                    parent_widget=parent_widget,
                    logger=self.logger,
                    template_manager=template_manager,
                    output_dir=output_dir
                )
                if ui_manager:
                    self.service_registry.register("ui_manager", ui_manager)
                    self.logger.info("✅ UIManager created and registered")
                else:
                    self.logger.warning("⚠️ UIManager creation returned None")
            except Exception as e:
                self.logger.error(f"❌ UIManagerFactory failed: {e}", exc_info=True)
        else:
            self.logger.info("Skipping UIManager creation (parent_widget missing)")

        # --- Final Status ---
        service_count = len(self.service_registry.get_all_services())
        self.logger.info(f"✅ Dreamscape system loading complete. {service_count} services registered.")
        return self.service_registry 