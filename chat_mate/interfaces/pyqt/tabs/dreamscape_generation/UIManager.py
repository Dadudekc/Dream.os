import os
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (
    QListWidget, QTreeWidget, QTextEdit, QPlainTextEdit, 
    QComboBox, QCheckBox, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer


class UIManager:
    """
    Manages UI interactions for the Dreamscape Generation Tab.
    
    This class handles:
    1. Loading and displaying episodes
    2. Managing UI controls 
    3. Handling user interactions with UI elements
    4. Setting up template previews
    """
    
    def __init__(self, parent_widget, logger=None, episode_list=None, 
                 template_manager=None, output_dir="outputs/dreamscape"):
        """
        Initialize the UIManager.
        
        Args:
            parent_widget: The parent widget that contains UI elements
            logger: Logger instance for debugging and monitoring
            episode_list: QListWidget for displaying episodes
            template_manager: TemplateManager instance for handling templates
            output_dir: Directory for output files
        """
        self.parent = parent_widget
        self.logger = logger or logging.getLogger(__name__)
        self.episode_list = episode_list
        self.template_manager = template_manager
        self.output_dir = output_dir
        self.timer = QTimer()
        os.makedirs(output_dir, exist_ok=True)
        
    def refresh_episode_list(self, reverse_order: bool = False) -> int:
        """
        Refresh the list of episodes from the output directory.
        
        Args:
            reverse_order: Whether to display episodes in reverse order
            
        Returns:
            int: The number of episodes found
        """
        try:
            if not self.episode_list:
                self.logger.warning("Episode list widget not available.")
                return 0
                
            self.episode_list.clear()
            
            # Check if output directory exists
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir, exist_ok=True)
                self.logger.info(f"Created output directory: {self.output_dir}")
                return 0
            
            episode_files = []
            for filename in os.listdir(self.output_dir):
                if filename.endswith(".txt") and not filename == "dreamscape_context.json":
                    filepath = os.path.join(self.output_dir, filename)
                    if os.path.isfile(filepath):
                        # Extract timestamp and a guess at the episode # or ID from filename
                        parts = filename.split('_', 1)
                        if len(parts) > 1:
                            timestamp = parts[0]
                            title_raw = parts[1].replace('.txt', '')
                            
                            # Attempt to parse out "episode #X" or "ds-XXX"
                            episode_num = None
                            ds_id = None
                            
                            # Example match for: "Episode #10"
                            match_episode_num = re.search(r'episode\s*#(\d+)', title_raw, re.IGNORECASE)
                            if match_episode_num:
                                episode_num = int(match_episode_num.group(1))
                            
                            # Example match for DS-### (like DS-042)
                            match_ds_id = re.search(r'(ds-\d+)', title_raw, re.IGNORECASE)
                            if match_ds_id:
                                ds_id = match_ds_id.group(1).upper()
                            
                            # Reformat title for display
                            display_title = title_raw.replace('_', ' ').title()
                            episode_files.append({
                                'filename': filename,
                                'filepath': filepath,
                                'timestamp': timestamp,
                                'title': display_title,
                                'episode_num': episode_num,
                                'episode_id': ds_id
                            })
            
            # Sort by episode number if available, else by timestamp (descending)
            episode_files.sort(
                key=lambda x: (
                    - (x['episode_num'] or 0),
                    x['timestamp']
                ),
                reverse=reverse_order
            )
            
            for episode in episode_files:
                if episode['episode_id']:
                    label = f"[{episode['episode_id']}] "
                else:
                    label = ""
                
                if episode['episode_num']:
                    label += f"Episode #{episode['episode_num']}: "
                
                label += f"{episode['title']} ({episode['timestamp']})"
                
                item_idx = self.episode_list.count()
                self.episode_list.addItem(label)
                self.episode_list.setItemData(item_idx, episode, Qt.UserRole)
            
            self.logger.info(f"Found {len(episode_files)} episodes in {self.output_dir}")
            return len(episode_files)
            
        except Exception as e:
            self.logger.error(f"Error refreshing episode list: {str(e)}")
            return 0
    
    def update_episode_content(self, episode_content: QTextEdit, current_item) -> bool:
        """
        Update the episode content display with the selected episode.
        
        Args:
            episode_content: QTextEdit to display episode content
            current_item: Currently selected item in the episode list
            
        Returns:
            bool: True if content was updated, False otherwise
        """
        try:
            if not current_item:
                episode_content.clear()
                return False
                
            episode_data = current_item.data(Qt.UserRole)
            if not episode_data:
                return False
                
            filepath = os.path.join(self.output_dir, episode_data.get('filename'))
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                episode_content.setPlainText(content)
                return True
            return False
                
        except Exception as e:
            self.logger.error(f"Error loading episode content: {str(e)}")
            return False
    
    def load_templates(self, template_dropdown: QComboBox) -> List[str]:
        """
        Load available templates into the dropdown.
        
        Args:
            template_dropdown: QComboBox to populate with templates
            
        Returns:
            List[str]: List of loaded template names
        """
        try:
            if not self.template_manager:
                self.logger.warning("Template manager not available.")
                return []
                
            templates = self.template_manager.get_available_templates()
            template_dropdown.clear()
            template_dropdown.addItems(templates)
            
            # Auto-select dreamscape template if available
            dreamscape_template = next((t for t in templates if "dreamscape.j2" in t), None)
            if dreamscape_template:
                template_dropdown.setCurrentText(dreamscape_template)
                
            return templates
                
        except Exception as e:
            self.logger.error(f"Error loading templates: {str(e)}")
            return []
    
    def render_template_preview(self, template_name: str, preview: QPlainTextEdit, 
                               context: Dict[str, Any]) -> bool:
        """
        Render a template with context data and display it in the preview.
        
        Args:
            template_name: Name of the template to render
            preview: QPlainTextEdit to display the preview
            context: Context data for template rendering
            
        Returns:
            bool: True if preview was rendered, False otherwise
        """
        try:
            if not self.template_manager:
                self.logger.warning("Template manager not available.")
                return False
                
            # Set the active template
            self.template_manager.set_active_template(template_name)
            
            # Render the template
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
        Save the currently rendered template to a file.
        
        Args:
            format: Format to save as ('txt' or 'md')
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            if not self.template_manager or not self.template_manager.active_template:
                QMessageBox.warning(self.parent, "No Template", 
                                   "No active template selected.")
                return False
            
            # Get save path from user
            file_filter = "Text files (*.txt)" if format == 'txt' else "Markdown files (*.md)"
            path, _ = QFileDialog.getSaveFileName(
                self.parent,
                "Save Rendered Output",
                "",
                file_filter
            )
            
            if not path:
                return False
            
            # Get context data
            if hasattr(self.parent, 'context_manager') and self.parent.context_manager:
                context = self.parent.context_manager.get_preview_context()
            else:
                # Fallback to sample context
                context = {
                    "raw_response": "Sample response text",
                    "chat_title": "Sample Chat",
                    "CURRENT_MEMORY_STATE": "Sample state",
                }
            
            # Render and save
            rendered = self.template_manager.render_template(context)
            
            if rendered:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(rendered)
                self.logger.info(f"Saved rendered output to: {path}")
                QMessageBox.information(self.parent, "Success", 
                                       f"Saved rendered output to: {path}")
                return True
            else:
                QMessageBox.warning(self.parent, "Rendering Failed", 
                                   "Failed to render the template.")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving rendered output: {str(e)}")
            QMessageBox.critical(self.parent, "Error", 
                               f"Failed to save output: {str(e)}")
            return False
    
    def setup_auto_update_timer(self, auto_update_checkbox: QCheckBox, 
                               update_interval_combo: QComboBox) -> bool:
        """
        Set up a timer for automatic context updates.
        
        Args:
            auto_update_checkbox: Checkbox to enable/disable auto-updates
            update_interval_combo: Combo box with update intervals
            
        Returns:
            bool: True if timer was set up, False otherwise
        """
        try:
            interval_mapping = {
                "1 day": 86400000,  # ms in a day
                "3 days": 3 * 86400000,
                "7 days": 7 * 86400000,
                "14 days": 14 * 86400000,
                "30 days": 30 * 86400000
            }
            
            selected_interval = update_interval_combo.currentText()
            interval_ms = interval_mapping.get(selected_interval, 7 * 86400000)
            
            # Stop existing timer if running
            if self.timer.isActive():
                self.timer.stop()
            
            # Set up timer
            if auto_update_checkbox.isChecked():
                self.timer.setInterval(interval_ms)
                self.timer.timeout.connect(self._on_auto_update_timer)
                self.timer.start()
                self.logger.info(f"Auto-update timer started with interval: {selected_interval}")
                return True
            return False
                
        except Exception as e:
            self.logger.error(f"Error setting up auto-update timer: {str(e)}")
            return False
    
    def _on_auto_update_timer(self):
        """Handle timer event for auto context updates."""
        try:
            if hasattr(self.parent, 'send_context_to_chatgpt'):
                self.parent.send_context_to_chatgpt()
                self.logger.info("Auto-sent context to ChatGPT")
        except Exception as e:
            self.logger.error(f"Error in auto-update timer: {str(e)}")
    
    def log_output(self, output_display: QTextEdit, message: str):
        """
        Log a message to the output display.
        
        Args:
            output_display: QTextEdit to display log messages
            message: The message to log
        """
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            
            if output_display:
                output_display.append(formatted_message)
                
            # Also log to the logger
            self.logger.info(message)
            
        except Exception as e:
            # Fall back to print if logging fails
            print(f"Log error: {e}, Original message: {message}")
    
    def share_to_discord(self, episode_content: QTextEdit, discord_manager) -> bool:
        """
        Share the currently selected episode to Discord.
        
        Args:
            episode_content: QTextEdit containing episode content
            discord_manager: Discord manager service
            
        Returns:
            bool: True if shared successfully, False otherwise
        """
        try:
            content = episode_content.toPlainText()
            
            if not content:
                QMessageBox.warning(self.parent, "No Content", 
                                   "Please select an episode first.")
                return False
                
            if not discord_manager:
                QMessageBox.warning(self.parent, "Discord Not Available", 
                                   "Discord service is not available. Check your Discord configuration.")
                return False
            
            # Truncate if too long for Discord
            if len(content) > 1900:  # Discord has 2000 char limit
                content = content[:1900] + "..."
                
            discord_manager.send_message(content)
            self.logger.info("Episode shared to Discord successfully.")
            QMessageBox.information(self.parent, "Success", 
                                   "Episode shared to Discord successfully.")
            return True
                
        except Exception as e:
            self.logger.error(f"Error sharing to Discord: {str(e)}")
            QMessageBox.critical(self.parent, "Error", 
                               f"Failed to share to Discord: {str(e)}")
            return False 