# chat_mate/interfaces/pyqt/tabs/dreamscape/components/TemplateEditor.py

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout

class TemplateEditor(QWidget):
    """UI component for viewing and potentially editing Dreamscape templates."""
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.logger = logging.getLogger(__name__)
        self.layout = QVBoxLayout(self)
        
        self.title_label = QLabel("Dreamscape Template Editor")
        self.editor = QTextEdit() # Use QTextEdit for editing capability
        self.editor.setPlaceholderText("Template content will be loaded here...")
        # self.editor.setReadOnly(True) # Make read-only initially

        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Load Template")
        self.save_button = QPushButton("Save Template")
        self.save_button.setEnabled(False) # Disable save initially
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.editor, 1) # Allow editor to stretch
        self.layout.addLayout(button_layout)
        
        self.setLayout(self.layout)

        # Connect signals (add methods later)
        # self.load_button.clicked.connect(self.load_template)
        # self.save_button.clicked.connect(self.save_template)
        # self.editor.textChanged.connect(lambda: self.save_button.setEnabled(True))

        self.logger.info("TemplateEditor initialized.")

    # Add methods like load_template, save_template later
    # def load_template(self):
    #     # Logic to load template file content into self.editor
    #     pass

    # def save_template(self):
    #     # Logic to save content from self.editor back to file
    #     pass 