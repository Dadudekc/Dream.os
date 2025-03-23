from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
import logging

class LogsTab(QWidget):
    """
    LogsTab provides a display area for system logs, feedback, and real-time updates.
    """
    def __init__(self, parent=None, logger=None):
        """
        Initialize the logs tab.
        
        Args:
            parent: Parent widget
            logger: Logger instance
        """
        super().__init__(parent)
        self.parent = parent
        self.logger = logger or logging.getLogger(__name__)
        self.initUI()

    def initUI(self):
        """Initialize the user interface components."""
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
        
        Args:
            message: The message to append
        """
        self.log_display.append(message)
        self.logger.info(message)
        
    def append_output(self, message: str):
        """
        Alternative method name for append_log to maintain compatibility.
        
        Args:
            message: The message to append
        """
        self.append_log(message)

    def clear_logs(self):
        """
        Clears the log display.
        """
        self.log_display.clear()
        self.append_log("[LOGS CLEARED]")
