import json
import logging
from typing import Dict, Any, List, Optional
from template_loader import load_template

# Configure logging
logger = logging.getLogger(__name__)

class ChatHandler:
    """Handles chat interactions and manages conversation state and prompts"""
    
    def __init__(self):
        self.conversation_history = []
        self.system_state = {}
        self.active_template = "dynamic_prompt_template.j2"
    
    def start_new_conversation(self, user_input: str) -> Dict[str, Any]:
        """
        Start a new conversation with the given user input.
        Resets conversation history and generates a new prompt.
        
        Args:
            user_input: The user's initial input
            
        Returns:
            Response object with generated content
        """
        # Reset conversation history
        self.conversation_history = []
        
        # Generate the initial prompt using the template
        context = {
            "conversation": [],
            "system_state": self.system_state,
            "is_new_conversation": True
        }
        
        # Load the dynamic prompt template with context
        prompt = load_template(self.active_template, context)
        
        # Use the prompt to generate a response
        response = self.send_to_chatgpt(prompt, user_input)
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": response["content"]})
        
        return response
    
    def continue_conversation(self, user_input: str) -> Dict[str, Any]:
        """
        Continue an existing conversation with the given user input.
        Updates the prompt based on conversation history.
        
        Args:
            user_input: The user's input
            
        Returns:
            Response object with generated content
        """
        # Update the prompt based on conversation history
        context = {
            "conversation": self.conversation_history,
            "system_state": self.system_state,
            "is_new_conversation": False
        }
        
        # Load the dynamic prompt template with updated context
        prompt = load_template(self.active_template, context)
        
        # Use the updated prompt to generate a response
        response = self.send_to_chatgpt(prompt, user_input)
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": response["content"]})
        
        return response
    
    def send_to_chatgpt(self, prompt: str, user_input: str) -> Dict[str, Any]:
        """
        Send the prompt and user input to ChatGPT or other LLM.
        This is a placeholder that should be implemented with your API integration.
        
        Args:
            prompt: The system prompt to use
            user_input: The user's input
            
        Returns:
            Response object with generated content
        """
        # Placeholder - replace with actual API call
        logger.info(f"Sending prompt to ChatGPT: {prompt[:50]}...")
        
        # Mock response for testing
        return {
            "content": f"This is a response to: {user_input}",
            "model": "gpt-4",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        }
    
    def update_system_state(self, state_updates: Dict[str, Any]) -> None:
        """
        Update the system state with the given updates.
        This affects future prompt generation.
        
        Args:
            state_updates: Dict of state variables to update
        """
        self.system_state.update(state_updates)
        logger.info(f"Updated system state: {list(state_updates.keys())}")
    
    def set_active_template(self, template_name: str) -> bool:
        """
        Set the active template for prompt generation.
        
        Args:
            template_name: Name of the template file
            
        Returns:
            Success status
        """
        # Verify template exists and is valid
        test_render = load_template(template_name, {})
        if test_render is not None:
            self.active_template = template_name
            logger.info(f"Active template set to: {template_name}")
            return True
        return False 