# core/micro_factories/context_manager_factory.py

# Import location seems different from previous factory
# Assuming this is the correct path based on your snippet
try:
    from core.context.context_manager import ContextManager
except ImportError:
    # Fallback if the path is different
    try:
        from interfaces.pyqt.tabs.dreamscape_generation.ContextManager import ContextManager
    except ImportError as e:
        logging.error(f"Failed to import ContextManager from expected locations: {e}")
        ContextManager = None

import logging

class ContextManagerFactory:
    @staticmethod
    def create_context_manager(
        parent_widget=None, 
        logger_instance=None,
        chat_manager=None,
        dreamscape_service=None,
        template_manager=None,
        memory_manager=None, 
        config=None
    ):
        """
        Factory method to create and configure a ContextManager.
        
        Args:
            parent_widget: The parent tab/widget (DreamscapeGenerationTab).
            logger_instance: Logger instance for the ContextManager.
            chat_manager: The chat manager service.
            dreamscape_service: The DreamscapeGenerationService instance.
            template_manager: The template manager service.
            memory_manager: Optional memory manager reference.
            config: Optional config dict or object.
        
        Returns:
            An instance of ContextManager.
        """
        logger = logger_instance or logging.getLogger("ContextManagerFactory")
        if ContextManager is None:
            logger.error("❌ ContextManager class not available due to import failure.")
            return None
            
        logger.info("🔧 Creating ContextManager via factory")
        try:
            # --- Add print before calling constructor ---
            # print(f"[DEBUG PRINT Factory] About to call ContextManager constructor with: parent={parent_widget}, logger={logger}, chat_manager={chat_manager}, dreamscape_generator(service)={dreamscape_service}, template_manager={template_manager}") # Remove print
            # --- End print ---

            # Match the parameters to the ContextManager constructor
            # The constructor expects 'dreamscape_generator' but our loader passes 'dreamscape_service'
            instance = ContextManager(
                parent_widget=parent_widget, 
                logger=logger,
                chat_manager=chat_manager,
                dreamscape_generator=dreamscape_service,  # Rename to match the constructor
                template_manager=template_manager
            )
            logger.info("✅ ContextManager created successfully.")
            return instance
        except Exception as e:
            logger.error(f"❌ Failed to create ContextManager: {e}", exc_info=True)
            return None 
