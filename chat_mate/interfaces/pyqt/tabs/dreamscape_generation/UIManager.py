# File: interfaces/pyqt/tabs/dreamscape_generation/UIManager.py

import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Any

from PyQt5.QtWidgets import (
    QListWidget, QPlainTextEdit, QComboBox, QCheckBox, QTextEdit, QMessageBox, QFileDialog
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

    def __init__(self, parent_widget, logger, episode_list: QListWidget, template_manager, output_dir: str):
        """
        Initialize the UIManager.
        
        Args:
            parent_widget: The parent QWidget containing the UI elements.
            logger: Logger instance for debugging.
            episode_list: QListWidget used for displaying episodes.
            template_manager: TemplateManager instance for handling templates.
            output_dir: Directory path where episode files are stored.
        """
        self.parent = parent_widget
        self.logger = logger or logging.getLogger(__name__)
        self.episode_list = episode_list
        self.template_manager = template_manager
        self.output_dir = output_dir
        self.timer = QTimer()
        
        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def refresh_episode_list(self, reverse_order: bool = False) -> int:
        """
        Refresh the episode list by scanning the output directory.
        
        Args:
            reverse_order: If True, display episodes in reverse order.
            
        Returns:
            The number of episodes found.
        """
        try:
            if not self.episode_list:
                self.logger.warning("Episode list widget not available.")
                return 0

            self.episode_list.clear()

            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir, exist_ok=True)
                self.logger.info(f"Created output directory: {self.output_dir}")
                return 0

            episode_files = []
            for filename in os.listdir(self.output_dir):
                if filename.endswith(".txt") and filename != "dreamscape_context.json":
                    filepath = os.path.join(self.output_dir, filename)
                    if os.path.isfile(filepath):
                        parts = filename.split('_', 1)
                        if len(parts) > 1:
                            timestamp = parts[0]
                            title_raw = parts[1].replace('.txt', '')
                            # Extract episode number and ID
                            episode_num = None
                            ds_id = None
                            match_episode_num = re.search(r'episode\s*#(\d+)', title_raw, re.IGNORECASE)
                            if match_episode_num:
                                episode_num = int(match_episode_num.group(1))
                            match_ds_id = re.search(r'(ds-\d+)', title_raw, re.IGNORECASE)
                            if match_ds_id:
                                ds_id = match_ds_id.group(1).upper()

                            display_title = title_raw.replace('_', ' ').title()
                            episode_files.append({
                                'filename': filename,
                                'filepath': filepath,
                                'timestamp': timestamp,
                                'title': display_title,
                                'episode_num': episode_num,
                                'episode_id': ds_id
                            })

            episode_files.sort(key=lambda x: (-(x['episode_num'] or 0), x['timestamp']), reverse=reverse_order)
            for episode in episode_files:
                label = f"[{episode['episode_id']}] " if episode.get('episode_id') else ""
                if episode.get('episode_num'):
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
        Update the episode content display with the content of the selected episode.
        
        Args:
            episode_content: QTextEdit where episode content will be displayed.
            current_item: Currently selected item in the episode list.
            
        Returns:
            True if content was updated; False otherwise.
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
        Load available templates into the dropdown from the dreamscape template directory.
        
        Args:
            template_dropdown: QComboBox to populate with template names.
            
        Returns:
            List of template names.
        """
        try:
            if not self.template_manager:
                self.logger.warning("Template manager not available.")
                return []

            # ✅ Import and use PathManager
            template_dir = PathManager.get_template_path("dreamscape")
            self.logger.info(f"Loading templates from: {template_dir}")

            # ✅ Load templates from this directory
            self.template_manager.load_templates(template_dir)
            templates = self.template_manager.get_available_templates()

            # Populate dropdown
            template_dropdown.clear()
            template_dropdown.addItems(templates)

            # Auto-select a dreamscape template if found
            dreamscape_template = next((t for t in templates if "dreamscape.j2" in t), None)
            if dreamscape_template:
                template_dropdown.setCurrentText(dreamscape_template)

            return templates

        except Exception as e:
            self.logger.error(f"Error loading templates: {str(e)}")
            return []


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
                QMessageBox.warning(self.parent, "No Template", "No active template selected.")
                return False

            file_filter = "Text files (*.txt)" if format == 'txt' else "Markdown files (*.md)"
            path, _ = QFileDialog.getSaveFileName(self.parent, "Save Rendered Output", "", file_filter)
            if not path:
                return False

            # Retrieve context data from parent if available; otherwise use defaults
            if hasattr(self.parent, 'context_manager') and self.parent.context_manager:
                context = self.parent.context_manager.get_preview_context()
            else:
                context = {"raw_response": "Sample response", "chat_title": "Sample Chat", "CURRENT_MEMORY_STATE": "Sample state"}

            rendered = self.template_manager.render_template(context)
            if rendered:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(rendered)
                self.logger.info(f"Saved rendered output to: {path}")
                QMessageBox.information(self.parent, "Success", f"Saved rendered output to: {path}")
                return True
            else:
                QMessageBox.warning(self.parent, "Rendering Failed", "Failed to render the template.")
                return False

        except Exception as e:
            self.logger.error(f"Error saving rendered output: {str(e)}")
            QMessageBox.critical(self.parent, "Error", f"Failed to save output: {str(e)}")
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

            if self.timer.isActive():
                self.timer.stop()

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
        """Handler for auto-update timer timeout events."""
        try:
            if hasattr(self.parent, 'send_context_to_chatgpt'):
                self.parent.send_context_to_chatgpt()
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
