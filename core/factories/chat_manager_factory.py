# core/factories/chat_manager_factory.py

import logging
from typing import Optional
from core.ChatManager import ChatManager
from core.factories.openai_client_factory import OpenAIClientFactory
from core.services.service_registry import ServiceRegistry
from core.PathManager import PathManager

class ChatManagerFactory:
    """
    Factory for constructing a ChatManager with OpenAIClient bootstrapping.
    Used when ChatManager must be created standalone or early in the pipeline.
    """

    @staticmethod
    def create_chat_manager(
        openai_client=None,
        config_manager=None,
        logger: Optional[logging.Logger] = None,
        service_registry: Optional[ServiceRegistry] = None,
        headless: bool = True
    ) -> Optional[ChatManager]:
        """
        Constructs a ChatManager with optional auto-created OpenAIClient.

        Args:
            openai_client: Optional prebuilt OpenAIClient
            config_manager: Optional config manager
            logger: Optional logger instance
            service_registry: Optional service registry for dependency injection
            headless: Whether to boot OpenAIClient in headless mode

        Returns:
            ChatManager or None on failure
        """
        logger = logger or logging.getLogger("ChatManagerFactory")
        logger.info("🔧 Creating ChatManager (standalone factory)...")

        try:
            # Use service registry for shared dependencies if available
            if service_registry:
                config_manager = config_manager or service_registry.get("config_manager")
                openai_client = openai_client or service_registry.get("openai_client")
                logger = service_registry.get("logger") or logger

            # Bootstrap OpenAIClient if not provided
            if not openai_client:
                logger.info("No OpenAIClient provided. Creating via factory...")
                openai_client = OpenAIClientFactory.create_openai_client(
                    config_manager=config_manager,
                    logger=logger,
                    headless=headless,
                    service_registry=service_registry,
                )
                if not openai_client:
                    logger.error("❌ Failed to create OpenAIClient.")
                    return None

            # Resolve memory path
            try:
                path_manager = service_registry.get("path_manager") if service_registry else PathManager()
                memory_path = path_manager.get_memory_path("chat_memory.json")
            except Exception as e:
                logger.warning(f"⚠️ Failed to resolve memory path: {e}")
                memory_path = None

            # Construct ChatManager
            chat_manager = ChatManager(
                openai_client=openai_client,
                config_manager=config_manager,
                memory_path=memory_path,
                logger=logger
            )

            logger.info("✅ ChatManager created successfully.")
            return chat_manager

        except Exception as e:
            logger.error(f"❌ Failed to construct ChatManager: {e}", exc_info=True)
            return None

    @staticmethod
    def create(service_registry: Optional[ServiceRegistry] = None, headless: bool = True) -> Optional[ChatManager]:
        """
        Shorthand for creating a ChatManager using a ServiceRegistry.

        Args:
            service_registry: Central service registry
            headless: Whether to boot OpenAIClient in headless mode

        Returns:
            ChatManager instance or None
        """
        logger = logging.getLogger("ChatManagerFactory")

        try:
            config_manager = service_registry.get("config_manager") if service_registry else None
            openai_client = service_registry.get("openai_client") if service_registry else None
            logger_instance = service_registry.get("logger") or logger if service_registry else logger

            return ChatManagerFactory.create_chat_manager(
                openai_client=openai_client,
                config_manager=config_manager,
                logger=logger_instance,
                service_registry=service_registry,
                headless=headless
            )

        except Exception as e:
            logger.error(f"❌ Failed to create ChatManager via shorthand: {e}", exc_info=True)
            return None
