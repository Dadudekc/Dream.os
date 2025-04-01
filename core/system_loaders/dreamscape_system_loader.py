# core/system_loaders/dreamscape_system_loader.py

import logging
import os
from typing import Optional, Dict, Any
import time

# Core services and managers
from core.config.config_manager import ConfigManager
from core.PathManager import PathManager
from core.services.service_registry import ServiceRegistry
from core.services.dreamscape_generator_service import DreamscapeGenerationService

# Import unified factory system
from core.factories import FactoryRegistry

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
            prompt_manager = FactoryRegistry.create_service("prompt_manager", self.service_registry)
            if prompt_manager:
                self.service_registry.register("prompt_manager", prompt_manager)
                self.logger.info("✅ PromptManager created and registered")
            else:
                self.logger.error("❌ Failed to create PromptManager")
                return self.service_registry

        # Create OpenAIClient and ChatManager if not provided
        if not chat_manager:
            self.logger.info("Creating OpenAIClient and ChatManager via factories...")
            openai_client = FactoryRegistry.create_service("openai_client", self.service_registry)
            if not openai_client:
                self.logger.error("❌ Failed to create OpenAIClient")
                return self.service_registry

            self.service_registry.register("openai_client", openai_client)
            
            chat_manager = FactoryRegistry.create_service("chat_manager", self.service_registry)
            if chat_manager:
                self.service_registry.register("chat_manager", chat_manager)
                self.logger.info("✅ ChatManager created and registered")
            else:
                self.logger.error("❌ Failed to create ChatManager")
                return self.service_registry

        # --- Initialize Template Manager ---
        template_manager = FactoryRegistry.create_service("template_manager", self.service_registry)
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

        # --- Initialize Component Managers ---
        context_manager = None # Initialize to None
        episode_generator = None # Initialize to None
        ui_manager = None # Initialize to None

        # Context Manager
        try:
            self.logger.info("Attempting to create ContextManager...")
            context_manager = FactoryRegistry.create_service("context_manager", self.service_registry)
            if context_manager:
                self.service_registry.register("context_manager", context_manager)
                self.logger.info("✅ ContextManager created and registered")
            else:
                self.logger.error("❌ ContextManager creation returned None")
        except Exception as e:
            self.logger.error(f"❌ ContextManager creation failed: {e}")
            self.logger.exception("Full exception trace:")
        
        self.logger.info(f"ContextManager creation finished. Instance: {context_manager}")

        # Episode Generator
        try:
            self.logger.info("Attempting to create EpisodeGenerator...")
            episode_generator = FactoryRegistry.create_service("episode_generator", self.service_registry)
            if episode_generator:
                try:
                    self.service_registry.register("episode_generator", episode_generator)
                    self.logger.info("✅ EpisodeGenerator created and registered")
                except Exception as reg_e:
                    self.logger.error(f"❌ Failed during EpisodeGenerator REGISTRATION: {reg_e}", exc_info=True)
                    episode_generator = None
            else:
                self.logger.error("❌ EpisodeGenerator creation returned None")
        except Exception as factory_e:
            self.logger.error(f"❌ EpisodeGeneratorFactory failed: {factory_e}", exc_info=True)

        self.logger.info(f"EpisodeGenerator processing finished. Instance: {episode_generator}")

        # UI Manager (Optional)
        if parent_widget:
            try:
                self.logger.info("Attempting to create UIManager...")
                ui_manager = FactoryRegistry.create_service("ui_manager", self.service_registry)
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
