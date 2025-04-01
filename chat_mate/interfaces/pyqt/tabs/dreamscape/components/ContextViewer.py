# chat_mate/interfaces/pyqt/tabs/dreamscape/components/ContextViewer.py

import logging
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextBrowser, QLabel, QPushButton

class ContextViewer(QWidget):
    """UI component for displaying the current Dreamscape context summary."""
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.logger = logging.getLogger(__name__)
        self.layout = QVBoxLayout(self)
        
        self.title_label = QLabel("Dreamscape Context Summary")
        self.viewer = QTextBrowser() # Use QTextBrowser for rich text display
        self.viewer.setPlaceholderText("Context summary will be loaded here...")
        
        self.refresh_button = QPushButton("Refresh Context")

        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.viewer, 1) # Allow viewer to stretch
        self.layout.addWidget(self.refresh_button)
        self.setLayout(self.layout)
        
        self.refresh_button.clicked.connect(self.refresh)
        
        self.refresh() # Load initial context

    def refresh(self):
        """Fetch and display the latest context summary."""
        self.logger.info("Refreshing Dreamscape context view...")
        try:
            context_summary = self.controller.get_context_summary()
            if context_summary:
                # Format the dictionary nicely for display
                formatted_text = json.dumps(context_summary, indent=2)
                self.viewer.setText(formatted_text)
                self.logger.info("Context view updated.")
            else:
                self.viewer.setText("Could not retrieve context summary.")
                self.logger.warning("Received empty context summary from controller.")
        except Exception as e:
            self.logger.error(f"Failed to refresh context view: {e}", exc_info=True)
            self.viewer.setText(f"Error loading context: {e}") 