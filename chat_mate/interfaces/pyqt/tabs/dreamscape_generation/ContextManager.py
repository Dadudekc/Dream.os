import logging
import os
from typing import Dict, Any, Optional
import json
from datetime import datetime

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMessageBox

from core.memory import ContextMemoryManager
from core.TemplateManager import TemplateManager
from core.ChatManager import ChatManager


class ContextManager:
    """
    UI adapter for the core ContextMemoryManager.
    Handles UI-specific context operations and display.
    """
    
    def __init__(self, parent_widget, logger=None, chat_manager=None,
                 dreamscape_generator=None, template_manager=None):
        """
        Initialize the UI Context Manager.
        
        Args:
            parent_widget: The parent widget for displaying dialogs
            logger: Logger instance for debugging and monitoring
            chat_manager: ChatManager instance for interacting with chats
            dreamscape_generator: DreamscapeGenerator instance for accessing context
            template_manager: TemplateManager instance for rendering templates
        """
        self.parent = parent_widget
        self.logger = logger or logging.getLogger(__name__)
        self.chat_manager = chat_manager
        self.dreamscape_generator = dreamscape_generator
        self.template_manager = template_manager
        self.output_dir = self._get_output_directory()
        
        # Initialize the core context manager
        self.context_manager = ContextMemoryManager(
            output_dir=self.output_dir,
            logger=self.logger
        )
        
    def _get_output_directory(self) -> str:
        """
        Get the output directory for context files.
        
        Returns:
            str: Path to the output directory
        """
        output_dir = "outputs/dreamscape"
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
        
    def get_context_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current context.
        
        Returns:
            Dict[str, Any]: A dictionary containing context data
        """
        try:
            return self.context_manager.get_context_summary()
        except Exception as e:
            self.logger.error(f"Error getting context summary: {str(e)}")
            return {}
            
    def refresh_context_display(self, context_tree: QTreeWidget, filter_text: str = ""):
        """
        Populate the context tree widget with the current context data.
        
        Args:
            context_tree: The QTreeWidget to populate
            filter_text: Optional text to filter the displayed items
        """
        try:
            context = self.get_context_summary()
            filter_text = filter_text.strip().lower()
            
            context_tree.clear()
            
            # Next Episode # (from context)
            next_episode_num = context.get("episode_count", 0) + 1
            QTreeWidgetItem(context_tree, ["Next Episode", f"Episode #{next_episode_num}"])
            
            # Episode Count
            QTreeWidgetItem(context_tree, ["Episode Count", str(context.get("episode_count", 0))])
            
            # Last Updated
            QTreeWidgetItem(context_tree, ["Last Updated", str(context.get("last_updated", "Never"))])
            
            # Architect Tier
            architect_tier = context.get("architect_tier", {})
            architect_item = QTreeWidgetItem(context_tree, ["Architect Tier", 
                                                           architect_tier.get("current_tier", "Initiate Architect")])
            QTreeWidgetItem(architect_item, ["Progress", architect_tier.get("progress", "0%")])
            
            # Skill Levels
            skills_item = QTreeWidgetItem(context_tree, ["Skill Levels", ""])
            for skill, level in context.get("skill_levels", {}).items():
                QTreeWidgetItem(skills_item, [skill, f"Level {level}"]) 
            
            # Active Quests
            quests = context.get("quests", {"active": [], "completed": []})
            quests_item = QTreeWidgetItem(context_tree, ["Active Quests", ""])
            for quest in quests.get("active", []):
                if filter_text and filter_text not in quest.lower():
                    continue
                QTreeWidgetItem(quests_item, ["", quest])
                
            # Recently Completed Quests
            if quests.get("completed"):
                completed_quests_item = QTreeWidgetItem(context_tree, ["Completed Quests", ""])
                for quest in quests.get("completed", [])[-5:]:  # Show last 5 completed quests
                    if filter_text and filter_text not in quest.lower():
                        continue
                    QTreeWidgetItem(completed_quests_item, ["", quest])
            
            # Protocols
            protocols_item = QTreeWidgetItem(context_tree, ["Protocols", ""])
            for protocol in context.get("protocols", []):
                if filter_text and filter_text not in protocol.lower():
                    continue
                QTreeWidgetItem(protocols_item, ["", protocol])
            
            # Stabilized Domains
            domains_item = QTreeWidgetItem(context_tree, ["Stabilized Domains", ""])
            for domain in context.get("stabilized_domains", []):
                if filter_text and filter_text not in domain.lower():
                    continue
                QTreeWidgetItem(domains_item, ["", domain])
            
            # Active Themes
            themes_item = QTreeWidgetItem(context_tree, ["Active Themes", ""])
            for theme in context.get("active_themes", []):
                if filter_text and filter_text not in theme.lower():
                    continue
                QTreeWidgetItem(themes_item, ["", theme])
            
            # Recent Episodes
            recent_item = QTreeWidgetItem(context_tree, ["Recent Episodes", ""])
            recent_episodes = context.get("recent_episodes", [])
            
            for i, episode in enumerate(recent_episodes):
                ep_title = episode.get("title", "Untitled")
                ep_themes = episode.get("themes", [])
                
                if filter_text:
                    title_match = (filter_text in ep_title.lower())
                    theme_match = any(filter_text in t.lower() for t in ep_themes)
                    if not (title_match or theme_match):
                        continue
                
                ep_num = context.get("episode_count", 0) - i
                ep_item = QTreeWidgetItem(recent_item, [f"Episode #{ep_num}", ep_title])
                
                QTreeWidgetItem(ep_item, ["Date", episode.get("timestamp", "")])
                
                ep_themes_parent = QTreeWidgetItem(ep_item, ["Themes", ""])
                for theme in ep_themes:
                    QTreeWidgetItem(ep_themes_parent, ["", theme])
            
            context_tree.expandAll()
            
        except Exception as e:
            self.logger.error(f"Error refreshing context display: {str(e)}")
            
    def send_context_to_chat(self, chat_url: Optional[str]) -> bool:
        """
        Send the current context to a specific ChatGPT conversation.
        
        Args:
            chat_url: The URL of the chat to send the context to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not chat_url:
                QMessageBox.warning(self.parent, "No Chat Selected", 
                                   "Please select a target chat to send context to.")
                return False
                
            if not self.template_manager:
                QMessageBox.warning(self.parent, "Services Not Available", 
                                   "Template manager is not initialized.")
                return False
            
            # Get context data from core manager
            context = self.context_manager.get_context_summary()
            
            # Render context using template
            if not self.template_manager.active_template:
                QMessageBox.warning(self.parent, "No Template Selected",
                                   "Please select a template for context rendering.")
                return False
                
            rendered_context = self.template_manager.render_template(context)
            if not rendered_context:
                QMessageBox.warning(self.parent, "Rendering Failed",
                                   "Failed to render context with template.")
                return False
                
            # Send to chat
            if not self.chat_manager:
                QMessageBox.warning(self.parent, "Chat Manager Not Available",
                                   "Chat manager is not initialized.")
                return False
                
            success = self.chat_manager.send_message(chat_url, rendered_context)
            if success:
                QMessageBox.information(self.parent, "Context Sent",
                                       "Context was successfully sent to the chat.")
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending context to chat: {str(e)}")
            QMessageBox.critical(self.parent, "Error",
                                f"Failed to send context: {str(e)}")
            return False
    
    def get_preview_context(self) -> Dict[str, Any]:
        """
        Get a sample context for template previews.
        
        Returns:
            Dict[str, Any]: A dictionary with sample context data
        """
        # First try to get real context if available
        if self.dreamscape_generator:
            try:
                return self.dreamscape_generator.get_context_summary()
            except Exception:
                pass
                
        # Fall back to sample data
        return {
            "raw_response": "Sample response text for preview",
            "chat_title": "Template Preview",
            "CURRENT_MEMORY_STATE": "Preview state",
            "skill_level_advancements": {
                "System Convergence": "Lv. 1 → Lv. 2",
                "Execution Velocity": "Lv. 3 → Lv. 4"
            },
            "newly_stabilized_domains": ["Preview Domain", "Test Domain"],
            "newly_unlocked_protocols": ["Preview Protocol", "Test Protocol"],
            "quest_completions": ["Preview Quest"],
            "new_quests_accepted": ["New Test Quest"],
            "architect_tier_progression": {
                "current_tier": "Preview Architect",
                "progress_to_next_tier": "50%"
            }
        }
        
    def save_context_schedule(self, enabled: bool, interval: str) -> bool:
        """
        Save scheduling configuration for auto context updates.
        
        Args:
            enabled: Whether auto-updates are enabled
            interval: The update interval (e.g. "7 days")
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            schedule_file = os.path.join(self.output_dir, "context_schedule.json")
            
            schedule_data = {
                "enabled": enabled,
                "interval": interval,
                "last_update": datetime.now().isoformat(),
                "next_update": None  # To be calculated by the scheduler
            }
            
            with open(schedule_file, 'w', encoding='utf-8') as f:
                json.dump(schedule_data, f, indent=2)
                
            self.logger.info(f"Saved context schedule: enabled={enabled}, interval={interval}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving context schedule: {str(e)}")
            return False
            
    def cleanup(self):
        """
        Clean up resources used by the ContextManager.
        Called during application shutdown.
        """
        try:
            self.logger.info("Cleaning up ContextManager resources...")
            
            # Ensure any pending context changes are saved
            if hasattr(self, 'context_manager') and self.context_manager:
                if hasattr(self.context_manager, 'save_context'):
                    try:
                        self.logger.debug("Saving context memory during cleanup")
                        self.context_manager.save_context()
                    except Exception as e:
                        self.logger.error(f"Error saving context during cleanup: {str(e)}")
            
            self.logger.info("ContextManager cleanup completed")
            return True
        except Exception as e:
            self.logger.error(f"Error during ContextManager cleanup: {str(e)}")
            return False 
