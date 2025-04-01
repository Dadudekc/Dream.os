# chat_mate/interfaces/pyqt/tabs/dreamscape/components/EpisodeList.py

import logging
from PyQt5.QtWidgets import QListWidget, QPushButton, QVBoxLayout, QWidget, QMessageBox

class EpisodeList(QWidget):
    """UI component for listing chats and triggering episode generation."""
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.logger = logging.getLogger(__name__)
        self.layout = QVBoxLayout(self)
        
        self.chat_list = QListWidget()
        self.generate_btn = QPushButton("Generate Episode from Selected Chat")

        self.layout.addWidget(self.chat_list)
        self.layout.addWidget(self.generate_btn)
        self.setLayout(self.layout)
        
        self.generate_btn.clicked.connect(self.generate_selected_episode)
        
        self.refresh()

    def refresh(self):
        """Reload the list of available chats."""
        self.chat_list.clear()
        try:
            chats = self.controller.get_all_chats()
            if chats:
                self.chat_list.addItems([c.get("title", "Untitled Chat") for c in chats])
                self.logger.info(f"Loaded {len(chats)} chats into list.")
            else:
                self.logger.info("No chats found to display.")
        except Exception as e:
            self.logger.error(f"Failed to refresh chat list: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to load chat list: {e}")

    def generate_selected_episode(self):
        """Trigger episode generation for the currently selected chat."""
        selected_item = self.chat_list.currentItem()
        if not selected_item:
            QMessageBox.information(self, "Selection Needed", "Please select a chat to generate an episode for.")
            return
            
        chat_title = selected_item.text()
        self.logger.info(f"Requesting episode generation for: {chat_title}")
        try:
            # This might be a long-running task, consider async/threading later
            episode_path = self.controller.generate_episode_for_chat(chat_title)
            if episode_path:
                QMessageBox.information(self, "Success", f"Episode generated successfully at:\n{episode_path}")
                # TODO: Signal to parent tab to refresh episode view/memory view
            else:
                QMessageBox.warning(self, "Generation Failed", f"Could not generate episode for {chat_title}.")
        except Exception as e:
            self.logger.error(f"Error during episode generation trigger: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An unexpected error occurred during generation: {e}") 