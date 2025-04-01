import logging
from typing import Optional, Dict, Any

from core.openai.OpenAIClient import OpenAIClient
from core.services.service_registry import ServiceRegistry

class OpenAIClientFactory:
    """Factory for creating and configuring OpenAIClient instances."""

    @staticmethod
    def create_openai_client(
        config_manager=None,
        logger: Optional[logging.Logger] = None,
        headless: bool = True,
        service_registry: Optional[ServiceRegistry] = None
    ) -> Optional[OpenAIClient]:
        """
        Create and configure a new OpenAIClient instance.

        Args:
            config_manager: Optional configuration manager
            logger: Optional logger instance
            headless: Whether to run in headless mode
            service_registry: Optional ServiceRegistry for dependency injection

        Returns:
            Configured OpenAIClient instance or None if creation fails
        """
        logger = logger or logging.getLogger("OpenAIClientFactory")
        logger.info(f"🔧 Creating OpenAIClient (headless={headless})...")

        try:
            # Get config from registry if available
            if service_registry and not config_manager:
                config_manager = service_registry.get("config_manager")
                if config_manager:
                    logger.info("Retrieved config_manager from ServiceRegistry")

            # Create the OpenAI client
            client = OpenAIClient(
                config_manager=config_manager,
                logger=logger,
                headless=headless
            )
            logger.info("✅ OpenAIClient created successfully")
            return client

        except Exception as e:
            logger.error(f"❌ Failed to create OpenAIClient: {e}", exc_info=True)
            return None

    @staticmethod
    def create(service_registry: Optional[ServiceRegistry] = None, headless: bool = True) -> Optional[OpenAIClient]:
        """
        Create an OpenAIClient using services from the registry.
        This is a convenience method for use with ServiceRegistry.

        Args:
            service_registry: The service registry to use for dependencies
            headless: Whether to run in headless mode

        Returns:
            Configured OpenAIClient instance or None if creation fails
        """
        logger = logging.getLogger("OpenAIClientFactory")
        
        try:
            if service_registry:
                config_manager = service_registry.get("config_manager")
                logger_instance = service_registry.get("logger") or logger
                
                return OpenAIClientFactory.create_openai_client(
                    config_manager=config_manager,
                    logger=logger_instance,
                    headless=headless,
                    service_registry=service_registry
                )
            else:
                logger.warning("⚠️ No ServiceRegistry provided, creating with defaults")
                return OpenAIClientFactory.create_openai_client(headless=headless)
        except Exception as e:
            logger.error(f"❌ Failed to create OpenAIClient: {e}", exc_info=True)
            return None 
