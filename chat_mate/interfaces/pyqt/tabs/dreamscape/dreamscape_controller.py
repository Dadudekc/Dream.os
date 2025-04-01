# chat_mate/interfaces/pyqt/tabs/dreamscape/dreamscape_controller.py

import logging

class DreamscapeController:
    """
    Mediator between the DreamscapeTab UI and the DreamscapeGenerationService.
    Exposes high-level methods for episode generation, context retrieval, and chat metadata access.
    """

    def __init__(self, generation_service, chat_manager):
        """
        Args:
            generation_service: Instance of DreamscapeGenerationService
            chat_manager: Instance of ChatManager (used for chat title discovery)
        """
        self.logger = logging.getLogger(__name__)
        self.generation_service = generation_service
        self.chat_manager = chat_manager

    def get_all_chats(self):
        """Return a list of available chat metadata."""
        try:
            # Ensure chat_manager is available
            if not self.chat_manager:
                self.logger.warning("ChatManager is not available in DreamscapeController")
                return []
            return self.chat_manager.get_all_chat_titles() or []
        except Exception as e:
            self.logger.error(f"Failed to retrieve chat titles: {e}", exc_info=True)
            return []

    def generate_episode_for_chat(self, chat_title):
        """Trigger episode generation for a given chat title."""
        try:
            # Ensure generation_service is available
            if not self.generation_service:
                self.logger.warning("DreamscapeGenerationService is not available in DreamscapeController")
                return None
            
            # Need to get messages for the specific chat title
            chat_history = self.chat_manager.get_chat_history(chat_title)
            if not chat_history:
                self.logger.warning(f"No chat history found for title: {chat_title}")
                return None
            messages = [entry.get('content') for entry in chat_history if entry.get('content')]
            if not messages:
                self.logger.warning(f"No message content extracted for title: {chat_title}")
                return None
                
            return self.generation_service.generate_episode_from_history(chat_title, messages)
        except Exception as e:
            self.logger.error(f"Failed to generate episode for '{chat_title}': {e}", exc_info=True)
            return None

    def get_context_summary(self):
        """Return the current Dreamscape context (e.g., active themes, episode count)."""
        try:
            # Ensure generation_service is available
            if not self.generation_service:
                self.logger.warning("DreamscapeGenerationService is not available in DreamscapeController")
                return {}
            # Assume service has this method or adapt as needed
            if hasattr(self.generation_service, 'get_context_summary'):
                 return self.generation_service.get_context_summary()
            else:
                 # Fallback or fetch from chain/memory if method doesn't exist on service
                 # This might require directly interacting with chain.py functions
                 self.logger.warning("'get_context_summary' not found on service, attempting fallback.")
                 # Example fallback (needs chain path): 
                 # from core.services.dreamscape.chain import get_context_from_chain
                 # return get_context_from_chain(self.generation_service.chain_path)
                 return {}

        except Exception as e:
            self.logger.error(f"Failed to retrieve Dreamscape context: {e}", exc_info=True)
            return {}

    def get_context_prompt(self):
        """Return the full context prompt ready for ChatGPT."""
        try:
             # Ensure generation_service is available
            if not self.generation_service:
                self.logger.warning("DreamscapeGenerationService is not available in DreamscapeController")
                return ""
            # Assume service has this method or adapt as needed
            if hasattr(self.generation_service, 'get_chatgpt_context_prompt'):
                 return self.generation_service.get_chatgpt_context_prompt()
            else:
                 self.logger.warning("'get_chatgpt_context_prompt' not found on service.")
                 return ""
        except Exception as e:
            self.logger.error(f"Failed to retrieve Dreamscape context prompt: {e}", exc_info=True)
            return ""

    # Add render_template if needed for preview functionality
    # def render_template(self, template_name, data, category='dreamscape'):
    #     try:
    #         if not self.generation_service:
    #             self.logger.warning("Generation service unavailable for rendering.")
    #             return "Error: Service unavailable"
    #         return self.generation_service.render_episode(template_name, data, category)
    #     except Exception as e:
    #         self.logger.error(f"Failed to render template '{template_name}': {e}", exc_info=True)
    #         return f"Error rendering template: {e}" 