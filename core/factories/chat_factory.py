from core.chat_engine.ChatManager import ChatManager
from core.PathManager import PathManager
 
class ChatFactory:
    @staticmethod
    def create(registry) -> ChatManager:
        """
        Build and return a ChatManager instance with all dependencies injected.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            ChatManager: A fully initialized ChatManager with dependencies
        """
        # Extract all required services from the registry
        config_manager = registry.get('config_manager')
        prompt_manager = registry.get('prompt_manager')
        driver_manager = registry.get('driver_manager')
        feedback_engine = registry.get('feedback_engine')
        cursor_manager = registry.get('cursor_manager')
        discord_dispatcher = registry.get('discord_dispatcher')
        logger = registry.get('logger')

        # Get memory path from PathManager
        try:
            path_manager = PathManager()
            memory_path = path_manager.get_memory_path("chat_memory.json")
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ Error getting memory path: {e}")
            memory_path = None

        # Create and return ChatManager with all dependencies injected
        return ChatManager(
            config_manager=config_manager,
            prompt_manager=prompt_manager,
            driver_manager=driver_manager,
            feedback_engine=feedback_engine,
            cursor_manager=cursor_manager,
            discord_dispatcher=discord_dispatcher,
            memory_path=memory_path,
            logger=logger,
        ) 