import logging
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout
from core.chatgpt_automation.controllers.assistant_mode_controller import AssistantModeController

# Set up basic logging
logging.basicConfig(level=logging.INFO)

class AssistantModeToggleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant_controller = AssistantModeController()
        self.init_ui()

    def init_ui(self):
        self.toggle_button = QPushButton("Start Assistant Mode")
        self.toggle_button.clicked.connect(self.toggle_assistant)

        layout = QVBoxLayout()
        layout.addWidget(self.toggle_button)
        self.setLayout(layout)

    def toggle_assistant(self):
        if self.assistant_controller.is_active():
            self.assistant_controller.stop()
            self.toggle_button.setText("Start Assistant Mode")
        else:
            self.assistant_controller.start()
            self.toggle_button.setText("Stop Assistant Mode")
