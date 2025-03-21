from PyQt5.QtCore import QObject, pyqtSignal
from core.AletheiaPromptManager import AletheiaPromptManager
from core.ChatManager import ChatManager
from core.PromptCycleManager import PromptCycleManager

class PromptService(QObject):
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.prompt_manager = AletheiaPromptManager()
        self.chat_manager = None
        self.cycle_manager = PromptCycleManager(
            prompt_manager=self.prompt_manager,
            append_output=self.log_message.emit
        )
        
    def initialize_chat_manager(self, excluded_chats, model, headless=False):
        """Initialize or reinitialize the chat manager"""
        if self.chat_manager:
            self.chat_manager.shutdown_driver()
            
        self.chat_manager = ChatManager(
            driver_manager=None,
            excluded_chats=excluded_chats,
            model=model,
            timeout=180,
            stable_period=10,
            poll_interval=5,
            headless=headless
        )
        
    def execute_prompt(self, prompt_text, new_chat=False):
        """Execute a single prompt"""
        if not prompt_text:
            self.log_message.emit("No prompt text provided.")
            return
            
        if not self.chat_manager:
            self.log_message.emit("Chat manager not initialized.")
            return
            
        try:
            interaction_id = None
            if new_chat:
                from datetime import datetime
                interaction_id = f"chat_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
            responses = self.chat_manager.execute_prompts_single_chat(
                [prompt_text], 
                cycle_speed=2,
                interaction_id=interaction_id
            )
            
            for i, resp in enumerate(responses, start=1):
                self.log_message.emit(f"Response #{i}: {resp}")
                
        except Exception as e:
            self.log_message.emit(f"Error executing prompt: {str(e)}")
            
    def start_prompt_cycle(self, selected_prompts):
        """Start a prompt cycle with selected prompts"""
        if not selected_prompts:
            self.log_message.emit("No prompts selected for cycle.")
            return
            
        if not self.chat_manager:
            self.log_message.emit("Chat manager not initialized.")
            return
            
        try:
            self.cycle_manager.start_cycle(selected_prompts)
        except Exception as e:
            self.log_message.emit(f"Error in prompt cycle: {str(e)}")
            
    def save_prompt(self, prompt_type, prompt_text):
        """Save a prompt"""
        try:
            self.prompt_manager.save_prompt(prompt_type, prompt_text)
            self.log_message.emit(f"Saved prompt: {prompt_type}")
        except Exception as e:
            self.log_message.emit(f"Error saving prompt: {str(e)}")
            
    def reset_prompts(self):
        """Reset prompts to defaults"""
        try:
            self.prompt_manager.reset_to_defaults()
            self.log_message.emit("Prompts reset to defaults.")
        except Exception as e:
            self.log_message.emit(f"Error resetting prompts: {str(e)}")
            
    def get_available_prompts(self):
        """Get list of available prompts"""
        return self.prompt_manager.list_available_prompts()
        
    def get_prompt(self, prompt_type):
        """Get a specific prompt"""
        return self.prompt_manager.get_prompt(prompt_type) 