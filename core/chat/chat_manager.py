"""
Chat Manager module for handling chat interactions.
"""
from typing import Optional, Any, Dict
import logging

class ChatManager:
    """Manager for chat interactions."""
    
    def __init__(
        self,
        prompt_manager: Any,
        config: Any,
        openai_client: Any,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the chat manager.
        
        Args:
            prompt_manager: The prompt manager instance
            config: The configuration manager
            openai_client: The OpenAI client instance
            logger: Optional logger instance
        """
        self.prompt_manager = prompt_manager
        self.config = config
        self.openai_client = openai_client
        self.logger = logger or logging.getLogger(__name__)
        
    def send_message(self, message: str, context: Optional[Dict] = None) -> str:
        """
        Send a message and get a response.
        
        Args:
            message: The message to send
            context: Optional context dictionary
            
        Returns:
            The response message
        """
        try:
            # Get the appropriate prompt template
            prompt = self.prompt_manager.get_prompt("chat")
            if not prompt:
                self.logger.warning("No chat prompt template found")
                return "I'm sorry, I'm having trouble understanding. Could you try rephrasing?"
            
            # Format the prompt with the message and context
            formatted_prompt = prompt.format(
                message=message,
                **(context or {})
            )
            
            # TODO: Implement actual chat logic
            # For now, just return a placeholder response
            # return "I understand your message. This is a placeholder response."

            # Use the injected OpenAI client to get a response
            if not self.openai_client:
                self.logger.error("OpenAI client not available for ChatManager")
                return "I apologize, but the chat service is not properly configured."

            response = self.openai_client.send_prompt(formatted_prompt)

            if response:
                 self.logger.info(f"Received response from OpenAI: {response[:50]}...") # Log first 50 chars
                 return response
            else:
                 self.logger.error("Received empty response from OpenAI")
                 return "I apologize, but I couldn't generate a response."
            
        except Exception as e:
            self.logger.error(f"Error in send_message: {e}", exc_info=True) # Log traceback
            return "I apologize, but I encountered an error processing your message." 