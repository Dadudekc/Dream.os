# File: interfaces/pyqt/tabs/dreamscape_generation/UIManager.py

import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

from PyQt5.QtWidgets import (
    QListWidget, QPlainTextEdit, QComboBox, QCheckBox, QTextEdit, QMessageBox, QFileDialog, QListWidgetItem
)
from PyQt5.QtCore import Qt, QTimer
from core.PathManager import PathManager


class UIManager:
    """
    UIManager handles all UI-specific tasks for the Dreamscape Generation Tab.
    
    Responsibilities:
      - Refresh and update the episode list.
      - Update episode content when an episode is selected.
      - Load and render templates.
      - Set up auto-update timers for context updates.
      - Log messages to the UI and to the central logger.
      - Share generated episode content to Discord.
    """

    # Interval constants for timers (in milliseconds)
    UPDATE_INTERVAL = 5000  # 5 seconds
    VALIDATION_INTERVAL = 2000 # 2 seconds

    def __init__(self, parent_widget, logger=None, template_manager=None, output_dir=None):
        """
        Initialize the UIManager.
        
        Args:
            parent_widget: The parent widget (DreamscapeGenerationTab)
            logger: Logger instance.
            template_manager: TemplateManager instance.
            output_dir: Directory for output files.
        """
        self.parent_widget = parent_widget
        self.logger = logger or logging.getLogger(__name__)
        self.template_manager = template_manager
        self.output_dir = output_dir
             
        # Internal state
        self._current_episode_data = None
        self._update_timer = QTimer()
        self._validation_timer = QTimer()
        self._validation_queue = []
        
        self.connect_signals()
        self.logger.info("UIManager initialized")

    # Restore properties to access parent widgets
    @property
    def episode_list(self):
        """Helper property to safely access the episode list from the parent."""
        if hasattr(self.parent_widget, 'episode_list'):
            widget = self.parent_widget.episode_list
            # Add a check to see if the widget is valid
            if widget:
                 return widget
            else:
                 self.logger.error("UIManager: Parent widget's episode_list attribute exists but evaluates to False!")
                 return None
        self.logger.warning("UIManager: Parent widget does not have 'episode_list' attribute.")
        return None

    @property
    def template_dropdown(self):
        """Helper property to safely access the template dropdown from the parent."""
        if hasattr(self.parent_widget, 'template_dropdown'):
            widget = self.parent_widget.template_dropdown
            if widget:
                 return widget
            else:
                 self.logger.error("UIManager: Parent widget's template_dropdown attribute exists but evaluates to False!")
                 return None
        self.logger.warning("UIManager: Parent widget does not have 'template_dropdown' attribute.")
        return None

    def connect_signals(self):
        """Connect UI signals to their handler methods."""
        # Example: Assuming parent_widget has buttons or signals
        # if hasattr(self.parent_widget, 'some_button'):
        #     self.parent_widget.some_button.clicked.connect(self.some_handler)
        pass # Implement actual signal connections

    def refresh_episode_list(self, reverse_order: bool = False) -> int:
        """
        Refreshes the episode list widget with files from the output directory.
        Returns the number of episodes found.
        """
        episode_list_widget = self.episode_list # Use the property
        if not episode_list_widget:
            self.logger.error("❌ Episode list widget not available via property, cannot refresh.") # Updated log
            return 0

        try:
            episode_list_widget.clear()
            episodes = []
            if os.path.isdir(self.output_dir):
                for filename in os.listdir(self.output_dir):
                    if filename.lower().endswith('.json') and filename != "dreamscape_context.json":
                        try:
                            path = os.path.join(self.output_dir, filename)
                            with open(path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            title = data.get("title", "Unknown Title")
                            timestamp = data.get("timestamp", "")
                            episodes.append({
                                "title": title,
                                "timestamp": timestamp,
                                "filename": filename
                            })
                        except Exception as file_e:
                            self.logger.warning(f"⚠️ Failed to load episode data from {filename}: {file_e}")
            else:
                self.logger.warning(f"⚠️ Output directory '{self.output_dir}' does not exist or is not a directory.")

            # Sort episodes by timestamp (most recent first by default)
            episodes.sort(key=lambda x: x.get("timestamp", ""), reverse=not reverse_order)

            # Add to QListWidget
            for episode in episodes:
                # Store filename in item data (Qt.UserRole) for retrieval later
                item = QListWidgetItem(f"{episode['title']} ({episode['timestamp']})")
                item.setData(Qt.UserRole, episode['filename'])
                episode_list_widget.addItem(item)

            self.logger.info(f"✅ Refreshed episode list with {len(episodes)} episodes.")
            return len(episodes)
        except Exception as e:
            self.logger.error(f"❌ Error refreshing episode list: {e}")
            return 0

    def display_episode_content(self, item: Optional[QListWidgetItem]):
        """
        Loads and displays the content of the selected episode.
        """
        if not item:
            return
            
        episode_filename = item.data(Qt.UserRole)
        if not episode_filename:
            self.logger.warning("Selected item has no filename data.")
            return
            
        episode_path = os.path.join(self.output_dir, episode_filename)

        try:
            with open(episode_path, 'r', encoding='utf-8') as f:
                episode_data = json.load(f)
                self._current_episode_data = episode_data # Store for potential sharing
                content = episode_data.get("content", "No content found.")
                
                # Find the target QTextEdit on the parent
                content_widget = getattr(self.parent_widget, 'episode_content', None)
                if content_widget and isinstance(content_widget, QTextEdit):
                    content_widget.setPlainText(content)
                    self.logger.info(f"Displayed content for: {episode_filename}")
                else:
                    self.logger.error("Could not find 'episode_content' QTextEdit on parent widget.")

        except FileNotFoundError:
            self.logger.error(f"Episode file not found: {episode_path}")
            QMessageBox.warning(self.parent_widget, "File Not Found", f"Could not find episode file:\n{episode_path}")
            self._current_episode_data = None
        except Exception as e:
            self.logger.error(f"Error loading episode content from {episode_path}: {e}")
            QMessageBox.critical(self.parent_widget, "Load Error", f"Failed to load episode content:\n{e}")
            self._current_episode_data = None

    def load_templates(self) -> List[str]: # Removed template_dropdown arg
        """
        Loads available template files into the template dropdown.
        Returns a list of template names found.
        """
        template_dropdown_widget = self.template_dropdown # Use the property
        if not template_dropdown_widget:
            self.logger.error("❌ Template dropdown widget not available via property, cannot load templates.") # Updated log
            return []
            
        template_dropdown_widget.clear()
        template_files = self.template_manager.list_templates() # Assuming TemplateManager has this method
        if template_files:
            template_dropdown_widget.addItems(template_files)
            # Try to select the active one if manager provides it
            active_template = self.template_manager.get_active_template_name()
            if active_template in template_files:
                template_dropdown_widget.setCurrentText(active_template)
            self.logger.info(f"✅ Loaded {len(template_files)} templates into dropdown.")
        else:
            self.logger.warning("⚠️ No templates found to load.")
            template_dropdown_widget.addItem("No templates found")
            template_dropdown_widget.setEnabled(False)
            
        return template_files

    def update_template_preview(self):
        """
        Updates the template preview text edit based on the selected template.
        """
        template_dropdown_widget = self.template_dropdown # Use property
        preview_widget = getattr(self.parent_widget, 'template_preview', None)
        
        if not template_dropdown_widget or not preview_widget:
            self.logger.warning("Cannot update template preview: dropdown or preview widget missing.")
            return

        selected_template = template_dropdown_widget.currentText()
        if selected_template and selected_template != "No templates found":
            try:
                content = self.template_manager.get_template_content(selected_template)
                preview_widget.setPlainText(content or "")
            except Exception as e:
                self.logger.error(f"Error loading template content for preview: {e}")
                preview_widget.setPlainText(f"Error loading template: {e}")
        else:
            preview_widget.clear()

    def render_template_preview(self, template_name: str, preview: QPlainTextEdit, context: Dict[str, Any]) -> bool:
        """
        Render the selected template with context data and display the result.
        
        Args:
            template_name: Name of the active template.
            preview: QPlainTextEdit to show the rendered template.
            context: Data context for template rendering.
            
        Returns:
            True if rendering is successful; False otherwise.
        """
        try:
            if not self.template_manager:
                self.logger.warning("Template manager not available.")
                return False

            self.template_manager.set_active_template(template_name)
            rendered = self.template_manager.render_template(context)
            if rendered:
                preview.setPlainText(rendered)
                return True
            else:
                preview.setPlainText("Template rendering failed.")
                return False

        except Exception as e:
            self.logger.error(f"Error rendering template preview: {str(e)}")
            preview.setPlainText(f"Error: {str(e)}")
            return False

    def save_rendered_output(self, format: str = 'txt') -> bool:
        """
        Save the rendered template output to a file.
        
        Args:
            format: File format to save as ('txt' or 'md').
            
        Returns:
            True if saved successfully; False otherwise.
        """
        try:
            if not self.template_manager or not self.template_manager.active_template:
                QMessageBox.warning(self.parent_widget, "No Template", "No active template selected.")
                return False

            file_filter = "Text files (*.txt)" if format == 'txt' else "Markdown files (*.md)"
            path, _ = QFileDialog.getSaveFileName(self.parent_widget, "Save Rendered Output", "", file_filter)
            if not path:
                return False

            # Retrieve context data from parent if available; otherwise use defaults
            if hasattr(self.parent_widget, 'context_manager') and self.parent_widget.context_manager:
                context = self.parent_widget.context_manager.get_preview_context()
            else:
                context = {"raw_response": "Sample response", "chat_title": "Sample Chat", "CURRENT_MEMORY_STATE": "Sample state"}

            rendered = self.template_manager.render_template(context)
            if rendered:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(rendered)
                self.logger.info(f"Saved rendered output to: {path}")
                QMessageBox.information(self.parent_widget, "Success", f"Saved rendered output to: {path}")
                return True
            else:
                QMessageBox.warning(self.parent_widget, "Rendering Failed", "Failed to render the template.")
                return False

        except Exception as e:
            self.logger.error(f"Error saving rendered output: {str(e)}")
            QMessageBox.critical(self.parent_widget, "Error", f"Failed to save output: {str(e)}")
            return False

    def setup_auto_update_timer(self, auto_update_checkbox: QCheckBox, update_interval_combo: QComboBox) -> bool:
        """
        Set up an auto-update timer for sending context updates.
        
        Args:
            auto_update_checkbox: QCheckBox to enable/disable auto-updates.
            update_interval_combo: QComboBox providing update intervals.
            
        Returns:
            True if timer is set up; False otherwise.
        """
        try:
            interval_mapping = {
                "1 day": 86400000,
                "3 days": 3 * 86400000,
                "7 days": 7 * 86400000,
                "14 days": 14 * 86400000,
                "30 days": 30 * 86400000
            }
            selected_interval = update_interval_combo.currentText()
            interval_ms = interval_mapping.get(selected_interval, 7 * 86400000)

            if self._update_timer.isActive():
                self._update_timer.stop()

            if auto_update_checkbox.isChecked():
                self._update_timer.setInterval(interval_ms)
                self._update_timer.timeout.connect(self._on_auto_update_timer)
                self._update_timer.start()
                self.logger.info(f"Auto-update timer started with interval: {selected_interval}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error setting up auto-update timer: {str(e)}")
            return False

    def _on_auto_update_timer(self):
        """Handler for auto-update timer timeout events."""
        try:
            if hasattr(self.parent_widget, 'send_context_to_chatgpt'):
                self.parent_widget.send_context_to_chatgpt()
                self.logger.info("Auto-sent context to ChatGPT")
        except Exception as e:
            self.logger.error(f"Error in auto-update timer: {str(e)}")

    def log_output(self, output_display: QTextEdit, message: str):
        """
        Log a message to the UI display and the central logger.
        
        Args:
            output_display: QTextEdit where messages are shown.
            message: The message to log.
        """
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            if output_display:
                output_display.append(formatted_message)
            self.logger.info(message)
        except Exception as e:
            print(f"Log error: {e}, Original message: {message}")

    def stop_timers(self):
        """
        Stop all timers managed by the UIManager.
        Called during cleanup to ensure timers don't fire after shutdown.
        """
        try:
            if hasattr(self, '_update_timer') and self._update_timer and self._update_timer.isActive():
                self.logger.info("Stopping UIManager auto-update timer")
                self._update_timer.stop()
                
            # Disconnect any timer connections to prevent callbacks after shutdown
            if hasattr(self, '_update_timer') and self._update_timer:
                try:
                    self._update_timer.timeout.disconnect()
                except (TypeError, RuntimeError):
                    # Already disconnected or no connections
                    pass
                    
            return True
        except Exception as e:
            self.logger.error(f"Error stopping timers: {str(e)}")
            return False

    def get_generation_parameters(self) -> Dict[str, Any]:
        """
        Retrieves episode generation parameters from the UI controls 
        via the parent widget reference.
        
        Returns:
            A dictionary containing the parameters:
            {'process_all', 'prompt_text', 'chat_url', 'model', 'reverse_order'}
        """
        # Default values
        parameters = {
            "process_all": False,
            "prompt_text": "",
            "chat_url": None,
            "model": "gpt-4o",  # Sensible default
            "reverse_order": False,
        }
        
        try:
            if not self.parent_widget:
                self.logger.error("❌ Parent widget reference is missing in UIManager. Cannot get parameters.")
                return parameters # Return defaults

            # Safely access controls using hasattr
            if hasattr(self.parent_widget, 'process_all_chats_checkbox') and self.parent_widget.process_all_chats_checkbox:
                parameters["process_all"] = self.parent_widget.process_all_chats_checkbox.isChecked()

            if hasattr(self.parent_widget, 'prompt_text_edit') and self.parent_widget.prompt_text_edit:
                parameters["prompt_text"] = self.parent_widget.prompt_text_edit.toPlainText()

            # Only get chat_url if process_all is False
            if not parameters["process_all"] and hasattr(self.parent_widget, 'target_chat_input') and self.parent_widget.target_chat_input:
                current_index = self.parent_widget.target_chat_input.currentIndex()
                if current_index >= 0:
                    # Prefer URL stored in item data if available
                    chat_url_data = self.parent_widget.target_chat_input.itemData(current_index)
                    parameters["chat_url"] = chat_url_data if chat_url_data else self.parent_widget.target_chat_input.currentText()
                else:
                    # Fallback to current text if no item is selected or data is missing
                    parameters["chat_url"] = self.parent_widget.target_chat_input.currentText()

            if hasattr(self.parent_widget, 'model_dropdown') and self.parent_widget.model_dropdown:
                parameters["model"] = self.parent_widget.model_dropdown.currentText()

            if hasattr(self.parent_widget, 'reverse_order_checkbox') and self.parent_widget.reverse_order_checkbox:
                parameters["reverse_order"] = self.parent_widget.reverse_order_checkbox.isChecked()

            self.logger.info(f"✅ Retrieved generation parameters from UI: {parameters}")
            return parameters

        except Exception as e:
            self.logger.error(f"❌ Error getting generation parameters from UI: {e}", exc_info=True)
            # Return defaults on error to prevent crashes, but log the failure
            return parameters
        
    def populate_chat_dropdown(self, chat_manager) -> int:
        """
        Populates the target chat dropdown UI element with available chats 
        obtained from the chat_manager.
        
        Args:
            chat_manager: The instance of the ChatManager to use.
            
        Returns:
            The number of chats added to the dropdown.
        """
        target_chat_input = None
        if hasattr(self.parent_widget, 'target_chat_input'):
            target_chat_input = self.parent_widget.target_chat_input
            
        if not target_chat_input:
            self.logger.warning("⚠️ Target chat dropdown (target_chat_input) not found on parent widget.")
            return 0
            
        if not chat_manager:
            self.logger.error("❌ Chat Manager is None, cannot populate chat list.")
            target_chat_input.clear()
            return 0
            
        try:
            target_chat_input.clear()
            # Assuming get_all_chat_titles might be blocking, consider running in thread if needed
            # For now, calling directly as the async wrapper is in the caller
            chat_list = chat_manager.get_all_chat_titles()
            self.logger.info(f"Found {len(chat_list)} chats via chat_manager")
            
            if not chat_list:
                self.logger.info("No chats found to populate dropdown.")
                return 0
                
            for chat in chat_list:
                title = chat.get("title", "Untitled Chat")
                url = chat.get("link", "") # Store the URL as user data
                # Add item with title, store URL in UserRole
                target_chat_input.addItem(title, userData=url)
                
            self.logger.info(f"✅ Populated target chat dropdown with {len(chat_list)} items.")
            return len(chat_list)
            
        except Exception as e:
            self.logger.error(f"❌ Error populating chat list dropdown: {e}", exc_info=True)
            target_chat_input.clear() # Clear on error
            return 0
        
    def validate_and_display_template_status(self, context_manager):
        """
        Validates the currently selected template against the preview context 
        and updates the UI label accordingly.
        
        Args:
            context_manager: The instance of the ContextManager to use.
        """
        label_widget = None
        if hasattr(self.parent_widget, 'missing_vars_label'):
            label_widget = self.parent_widget.missing_vars_label
            
        if not label_widget:
            self.logger.warning("⚠️ Missing variables label (missing_vars_label) not found on parent widget.")
            return

        # Ensure template_manager is available
        if not self.template_manager:
            self.logger.warning("Template Manager not available in UIManager.")
            label_widget.setText('Template Mgr Unavailable')
            label_widget.setStyleSheet('color: red')
            return
            
        if not context_manager:
            self.logger.warning("Context Manager not provided to validation method.")
            label_widget.setText('Context Mgr Unavailable')
            label_widget.setStyleSheet('color: red')
            return

        try:
            # Get active template directly from the manager if it stores it
            # Assuming template_manager keeps track of the active template
            active_template = self.template_manager.get_active_template_name() # Needs implementation in TemplateManager
            # Fallback: get from dropdown if method above doesn't exist
            if not active_template and hasattr(self.parent_widget, 'template_dropdown') and self.parent_widget.template_dropdown:
                 active_template = self.parent_widget.template_dropdown.currentText()

            if not active_template:
                label_widget.setText("No active template selected")
                label_widget.setStyleSheet("color: orange") # Use orange for non-error states
                return

            context = context_manager.get_preview_context()
            missing = self.template_manager.validate_context(active_template, context)
            
            if missing:
                missing_str = ", ".join(missing)
                label_widget.setText(f"Missing: {missing_str}")
                label_widget.setStyleSheet("color: red")
                self.logger.warning(f"Template validation failed for '{active_template}': Missing {missing_str}")
            else:
                label_widget.setText("✓ Context OK")
                label_widget.setStyleSheet("color: green")
                self.logger.info(f"Template validation successful for '{active_template}'.")

        except Exception as e:
            self.logger.error(f"❌ Error validating template context: {e}", exc_info=True)
            label_widget.setText("Validation Error")
            label_widget.setStyleSheet("color: red")

    def cleanup(self):
        """Clean up resources like timers."""
        self.stop_timers()
