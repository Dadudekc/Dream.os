# core/factories/prompt_manager_factory.py

import logging
from typing import Optional, Dict, Any
from core.AletheiaPromptManager import AletheiaPromptManager
from core.services.service_registry import ServiceRegistry


class PromptManagerFactory:
    """
    Factory for constructing a PromptManager (AletheiaPromptManager).
    Supports injection via service registry or manual parameters.
    """

    @staticmethod
    def create_prompt_manager(
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
        service_registry: Optional[ServiceRegistry] = None
    ) -> Optional[AletheiaPromptManager]:
        """
        Create and configure a new AletheiaPromptManager instance.

        Args:
            logger: Optional logger instance.
            config: Optional configuration dictionary (overrides config manager).
            service_registry: Optional ServiceRegistry to fetch logger/config_manager.

        Returns:
            Configured AletheiaPromptManager instance, or None on failure.
        """
        logger = logger or logging.getLogger("PromptManagerFactory")
        logger.info("🔧 Creating AletheiaPromptManager...")

        try:
            # Pull from registry if available and missing manually
            if service_registry:
                if not logger:
                    logger = service_registry.get("logger") or logger

                if not config:
                    config_manager = service_registry.get("config_manager")
                    if config_manager:
                        config = config_manager.get_prompt_config()
                        logger.info("Retrieved prompt config from ConfigManager in registry.")

            # Construct prompt manager
            prompt_manager = AletheiaPromptManager(config=config, logger=logger)
            logger.info("✅ AletheiaPromptManager created successfully.")
            return prompt_manager

        except Exception as e:
            logger.error(f"❌ Failed to create AletheiaPromptManager: {e}", exc_info=True)
            return None

    @staticmethod
    def create(service_registry: Optional[ServiceRegistry] = None) -> Optional[AletheiaPromptManager]:
        """
        Simplified factory method that only takes a service registry.

        Args:
            service_registry: Registry containing config_manager and logger.

        Returns:
            AletheiaPromptManager instance.
        """
        logger = logging.getLogger("PromptManagerFactory")

        try:
            config = None
            logger_instance = logger

            if service_registry:
                config_manager = service_registry.get("config_manager")
                if config_manager:
                    config = config_manager.get_prompt_config()
                logger_instance = service_registry.get("logger") or logger

            return PromptManagerFactory.create_prompt_manager(
                logger=logger_instance,
                config=config,
                service_registry=service_registry
            )

        except Exception as e:
            logger.error(f"❌ Error during PromptManagerFactory.create(): {e}", exc_info=True)
            return None
