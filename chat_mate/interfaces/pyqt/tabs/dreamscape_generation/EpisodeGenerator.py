import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt

from core.PromptCycleOrchestrator import PromptCycleOrchestrator
from core.ConfigManager import ConfigManager
from core.ChatManager import sanitize_filename


class EpisodeGenerator:
    """
    Handles the generation of Dreamscape episodes by interacting with ChatGPT.
    
    This class manages:
    1. Initializing the PromptCycleOrchestrator
    2. Executing prompts on single or multiple chats
    3. Processing and saving the generated results
    """
    
    def __init__(self, parent_widget, logger=None, chat_manager=None, config_manager=None):
        """
        Initialize the EpisodeGenerator.
        
        Args:
            parent_widget: The parent widget for displaying dialogs
            logger: Logger instance for debugging and monitoring
            chat_manager: ChatManager instance for interacting with chats
            config_manager: ConfigManager for accessing configuration
        """
        self.parent = parent_widget
        self.logger = logger or logging.getLogger(__name__)
        self.chat_manager = chat_manager
        self.config_manager = config_manager or ConfigManager()
        self.progress_dialog = None
        
    async def generate_episodes(self, prompt_text: str, chat_url: Optional[str] = None, 
                          model: str = "gpt-4o", process_all: bool = False, 
                          reverse_order: bool = False) -> bool:
        """
        Generate dreamscape episodes from chat history.
        
        Args:
            prompt_text: The prompt text to send to ChatGPT
            chat_url: URL of a specific chat (None if processing all)
            model: The model to use (e.g. "gpt-4o")
            process_all: Whether to process all available chats
            reverse_order: Whether to process chats in reverse order
            
        Returns:
            bool: True if generation was successful, False otherwise
        """
        if not prompt_text:
            QMessageBox.warning(self.parent, "Missing Prompt", "Please enter a prompt.")
            return False
            
        # Initialize progress dialog
        self.progress_dialog = QProgressDialog("Processing chats...", "Cancel", 0, 100, self.parent)
        self.progress_dialog.setWindowTitle("Dreamscape Generation")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()
        
        try:
            # Initialize orchestrator
            orchestrator = PromptCycleOrchestrator(self.config_manager)
            orchestrator.initialize_chat_manager(excluded_chats=[], model=model)
            
            if process_all:
                self.logger.info("Processing ALL chats")
                
                # Execute multi-cycle with the provided prompt
                results = orchestrator.execute_multi_cycle([prompt_text], reverse_order=reverse_order)
                
                # Process the results
                self._process_multi_chat_results(results)
                
            else:
                # Single chat processing
                if not chat_url:
                    QMessageBox.warning(self.parent, "No Chat Selected", "Please select a chat to process.")
                    self.progress_dialog.close()
                    return False
                
                self.logger.info(f"Processing single chat: {chat_url}")
                
                # Navigate to the specific chat URL
                orchestrator.chat_manager.driver_manager.get_driver().get(chat_url)
                
                # Execute the prompt
                response = orchestrator.execute_single_cycle(prompt_text)
                
                # Process the result
                self._process_single_chat_result(response, chat_title=self._get_chat_title(chat_url))
            
            # Clean up
            orchestrator.shutdown()
            self.progress_dialog.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating dreamscape episodes: {str(e)}")
            self.progress_dialog.close()
            QMessageBox.critical(self.parent, "Error", f"An error occurred: {str(e)}")
            return False
            
    def _process_multi_chat_results(self, results: Dict[str, List[str]]) -> bool:
        """
        Process results from multi-chat execution.
        
        Args:
            results: Dictionary mapping chat titles to their responses
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not results:
            self.logger.warning("No results returned from execution")
            return False
        
        try:
            # Count total chats processed
            chat_count = len(results)
            self.logger.info(f"Processing results from {chat_count} chats")
            
            # Create timestamped results directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_dir = os.path.join("outputs", "dreamscape", timestamp)
            os.makedirs(result_dir, exist_ok=True)
            
            # Save each chat result
            for chat_title, responses in results.items():
                safe_title = sanitize_filename(chat_title)
                chat_file = os.path.join(result_dir, f"{safe_title}.txt")
                
                with open(chat_file, "w", encoding="utf-8") as f:
                    f.write(f"# Dreamscape for: {chat_title}\n\n")
                    for idx, response in enumerate(responses, 1):
                        f.write(f"## Response {idx}\n{response}\n\n")
                
                self.logger.info(f"Saved results for '{chat_title}' to {chat_file}")
            
            # Show completion message
            QMessageBox.information(
                self.parent, 
                "Processing Complete", 
                f"Processed {chat_count} chats.\nResults saved to {result_dir}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing results: {str(e)}")
            QMessageBox.critical(self.parent, "Error", f"An error saving results: {str(e)}")
            return False
    
    def _process_single_chat_result(self, response: str, chat_title: str = "Unknown Chat") -> bool:
        """
        Process result from single chat execution.
        
        Args:
            response: The response text from ChatGPT
            chat_title: The title of the chat
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not response:
            self.logger.warning("No response returned from execution")
            return False
        
        try:
            # Create timestamped results directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_dir = os.path.join("outputs", "dreamscape", timestamp)
            os.makedirs(result_dir, exist_ok=True)
            
            # Sanitize filename
            safe_title = sanitize_filename(chat_title)
            
            # Save response
            chat_file = os.path.join(result_dir, f"{safe_title}.txt")
            with open(chat_file, "w", encoding="utf-8") as f:
                f.write(f"# Dreamscape for: {chat_title}\n\n")
                f.write(f"## Response\n{response}\n\n")
            
            self.logger.info(f"Saved result for '{chat_title}' to {chat_file}")
            
            # Show completion message
            QMessageBox.information(
                self.parent, 
                "Processing Complete", 
                f"Processed chat: {chat_title}.\nResult saved to {chat_file}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing result: {str(e)}")
            QMessageBox.critical(self.parent, "Error", f"An error saving result: {str(e)}")
            return False
    
    def _get_chat_title(self, chat_url: str) -> str:
        """
        Extract chat title from URL or get from chat list.
        
        Args:
            chat_url: The URL of the chat
            
        Returns:
            str: The title of the chat
        """
        # This is a simplified version - in a real implementation,
        # you would fetch the actual chat title from the chat manager
        try:
            if self.parent and hasattr(self.parent, 'chat_dropdown'):
                chat_dropdown = getattr(self.parent, 'chat_dropdown')
                for i in range(chat_dropdown.count()):
                    if chat_dropdown.itemData(i) == chat_url:
                        return chat_dropdown.itemText(i)
                        
            # If not found in dropdown or dropdown doesn't exist,
            # extract from URL (simplified approach)
            chat_id = chat_url.split('/')[-1]
            return f"Chat {chat_id[:8]}"
            
        except Exception as e:
            self.logger.error(f"Error getting chat title: {str(e)}")
            return "Unknown Chat" 