"""
Handler for assistant-related functionality in Dream.OS.
"""

import logging
from typing import Optional

from PyQt5.QtWidgets import QMessageBox

from ..ui.window_ui import WindowUI


class AssistantHandler:
    """
    Handles assistant-related functionality including OpenAI login,
    assistant mode control, and message handling.
    """
    
    def __init__(self, window_ui: WindowUI, logger: logging.Logger):
        """
        Initialize the assistant handler.
        
        Args:
            window_ui: Window UI instance
            logger: Logger instance
        """
        self.ui = window_ui
        self.logger = logger
        self.openai_client = None
        self.assistant_controller = None
        self.engine = None
        
    def set_services(self, openai_client, assistant_controller, engine) -> None:
        """
        Set required services.
        
        Args:
            openai_client: OpenAI client instance
            assistant_controller: Assistant controller instance
            engine: Automation engine instance
        """
        self.openai_client = openai_client
        self.assistant_controller = assistant_controller
        self.engine = engine
        
    def handle_openai_login(self) -> None:
        """Handle OpenAI login process."""
        try:
            if not self.openai_client:
                self.logger.error("OpenAI client not initialized")
                self.ui.parent.statusBar().showMessage("OpenAI client not initialized", 5000)
                return
                
            if not self.openai_client.is_ready():
                self.logger.info("Booting OpenAI client...")
                self.openai_client.boot()
                
            if self.openai_client.login_openai():
                self.logger.info("✅ OpenAI login successful")
                self.ui.parent.statusBar().showMessage("OpenAI login successful", 5000)
            else:
                self.logger.error("❌ OpenAI login failed")
                self.ui.parent.statusBar().showMessage("OpenAI login failed", 5000)
        except Exception as e:
            self.logger.error(f"OpenAI login error: {e}")
            try:
                if self.openai_client:
                    self.openai_client.shutdown()
            except Exception as shutdown_error:
                self.logger.error(f"OpenAI shutdown error: {shutdown_error}")
            self.ui.parent.statusBar().showMessage(f"OpenAI error: {str(e)}", 5000)
            
    def handle_scan(self) -> None:
        """Handle project scanning."""
        if not self.engine:
            self.logger.error("Automation engine not initialized")
            QMessageBox.warning(self.ui.parent, "Error", "Automation engine not initialized")
            return
            
        success, message = self.engine.scan_project_gui()
        QMessageBox.information(self.ui.parent, "Project Scan", message)
        
    def start_assistant(self) -> None:
        """Start the assistant mode."""
        if not self.assistant_controller:
            self.logger.error("Cannot start assistant: AssistantModeController not initialized")
            QMessageBox.warning(self.ui.parent, "Error", "Assistant controller not initialized. Please check logs.")
            return
            
        self.assistant_controller.start()
        self.ui.start_button.setEnabled(False)
        self.ui.stop_button.setEnabled(True)
        
        try:
            if self.engine and hasattr(self.engine, 'chat_manager'):
                chat_manager = self.engine.chat_manager
                if hasattr(chat_manager, 'is_logged_in') and chat_manager.is_logged_in():
                    self.logger.info("Browser login verified. Enabling voice mode...")
                    if hasattr(self.engine, 'enable_voice_mode'):
                        self.engine.enable_voice_mode()
                else:
                    self.logger.warning("Browser login not verified. Voice mode not enabled.")
        except Exception as e:
            self.logger.error(f"Error monitoring browser login: {str(e)}")
            
    def stop_assistant(self) -> None:
        """Stop the assistant mode."""
        if not self.assistant_controller:
            self.logger.error("Cannot stop assistant: AssistantModeController not initialized")
            return
            
        self.assistant_controller.stop()
        self.ui.start_button.setEnabled(True)
        self.ui.stop_button.setEnabled(False)
        
    def send_message(self) -> None:
        """Send a message to the assistant."""
        if not self.engine:
            self.logger.error("Cannot send message: Automation engine not initialized")
            return
            
        message = self.ui.input_field.toPlainText()
        if message:
            self.ui.chat_display.append(f"You: {message}")
            response = self.engine.get_chatgpt_response(message)
            self.ui.chat_display.append(f"Assistant: {response}")
            self.ui.input_field.clear() 