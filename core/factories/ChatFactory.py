# core/factories/chat_factory.py

import logging
from typing import Optional
from core.ChatManager import ChatManager
from core.PathManager import PathManager
from core.services.service_registry import ServiceRegistry

class ChatFactory:
    """
    Factory for constructing a fully-wired ChatManager from the ServiceRegistry.
    This is used internally within Dream.OS, where all services are orchestrated.
    """

    @staticmethod
    def create(service_registry: ServiceRegistry) -> Optional[ChatManager]:
        """
        Constructs and returns a fully-injected ChatManager instance.

        Args:
            service_registry (ServiceRegistry): The central service registry.

        Returns:
            ChatManager: A ChatManager instance with all dependencies injected.
        """
        logger = service_registry.get("logger") or logging.getLogger("ChatFactory")
        logger.info("🔧 Creating ChatManager using internal Dream.OS service wiring...")

        try:
            # --- Core Dependencies ---
            config_manager     = service_registry.get("config_manager")
            prompt_manager     = service_registry.get("prompt_manager")
            driver_manager     = service_registry.get("driver_manager")
            feedback_engine    = service_registry.get("feedback_engine")
            cursor_manager     = service_registry.get("cursor_manager")
            discord_dispatcher = service_registry.get("discord_dispatcher")

            # --- Optional: Validate presence or warn ---
            missing = [k for k, v in {
                "config_manager": config_manager,
                "prompt_manager": prompt_manager,
                "driver_manager": driver_manager,
                "feedback_engine": feedback_engine,
                "cursor_manager": cursor_manager,
                "discord_dispatcher": discord_dispatcher,
            }.items() if v is None]

            if missing:
                logger.warning(f"⚠️ Missing dependencies for ChatManager: {', '.join(missing)}")

            # --- Memory Path Resolution ---
            memory_path = None
            try:
                path_manager = service_registry.get("path_manager") or PathManager()
                memory_path = path_manager.get_memory_path("chat_memory.json")
            except Exception as e:
                logger.warning(f"⚠️ Failed to resolve chat memory path: {e}")

            # --- Construct ChatManager ---
            chat_manager = ChatManager(
                config_manager=config_manager,
                prompt_manager=prompt_manager,
                driver_manager=driver_manager,
                feedback_engine=feedback_engine,
                cursor_manager=cursor_manager,
                discord_dispatcher=discord_dispatcher,
                memory_path=memory_path,
                logger=logger,
            )

            logger.info("✅ ChatManager created and wired successfully.")
            return chat_manager

        except Exception as e:
            logger.error(f"❌ Failed to construct ChatManager: {e}", exc_info=True)
            return None
