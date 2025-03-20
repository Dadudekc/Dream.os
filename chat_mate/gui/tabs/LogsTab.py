from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt

class LogsTab(QWidget):
    """
    LogsTab provides a display area for system logs, feedback, and real-time updates.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent  # Typically DreamscapeGUI
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Header label
        label = QLabel("System Logs & Feedback")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # Log display area
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        # Clear logs button
        clear_button_layout = QHBoxLayout()
        clear_button = QPushButton("Clear Logs")
        clear_button.clicked.connect(self.clear_logs)
        clear_button_layout.addStretch()
        clear_button_layout.addWidget(clear_button)

        layout.addLayout(clear_button_layout)

        # Add stretch to balance UI
        layout.addStretch()

        self.setLayout(layout)

    def append_log(self, message: str):
        """
        Appends a log message to the log display.
        """
        self.log_display.append(message)

    def clear_logs(self):
        """
        Clears the log display.
        """
        self.log_display.clear()
        self.append_log("[LOGS CLEARED]")
