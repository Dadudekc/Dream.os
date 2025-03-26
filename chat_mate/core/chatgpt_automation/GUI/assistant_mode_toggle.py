import sys
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from core.chatgpt_automation.controllers.assistant_mode_controller import AssistantModeController

# Set up basic logging
logging.basicConfig(level=logging.INFO)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Assistant Mode Toggle")
        self.assistant_controller = AssistantModeController()
        self.init_ui()

    def init_ui(self):
        # Create a toggle button for Assistant Mode
        self.toggle_button = QPushButton("Start Assistant Mode")
        self.toggle_button.clicked.connect(self.toggle_assistant)

        layout = QVBoxLayout()
        layout.addWidget(self.toggle_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def toggle_assistant(self):
        if self.assistant_controller.is_active():
            self.assistant_controller.stop()
            self.toggle_button.setText("Start Assistant Mode")
        else:
            self.assistant_controller.start()
            self.toggle_button.setText("Stop Assistant Mode")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
