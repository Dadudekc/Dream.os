# ui/feedback_dashboard.py
import os
import json
import time
import threading
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt5.QtCore import QTimer, pyqtSignal
import logging

logger = logging.getLogger("feedback_dashboard")

class FeedbackDashboard(QWidget):
    # Signal to update dashboard text safely
    update_signal = pyqtSignal(str)

    def __init__(self, log_dir="ai_logs", parent=None):
        super().__init__(parent)
        self.log_dir = log_dir
        self.initUI()
        self.update_signal.connect(self.update_display)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_dashboard)
        self.timer.start(5000)  # refresh every 5 seconds

    def initUI(self):
        layout = QVBoxLayout()
        self.title = QLabel("Real-Time Reinforcement Feedback Dashboard")
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.title)
        layout.addWidget(self.log_display)
        self.setLayout(layout)
        self.setWindowTitle("Feedback Dashboard")

    def refresh_dashboard(self):
        # For demo, read the log file for today's date
        file_name = os.path.join(self.log_dir, f"ai_output_log_{datetime.utcnow().strftime('%Y%m%d')}.jsonl")
        if not os.path.exists(file_name):
            self.update_signal.emit("No logs available yet.")
            return

        # Read last few lines (for demo, read entire file)
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # For simplicity, show the last 10 entries
            recent_entries = lines[-10:]
            summary = "\n".join(recent_entries)
            self.update_signal.emit(summary)
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            self.update_signal.emit("Error reading logs.")

    def update_display(self, text):
        self.log_display.setPlainText(text)

if __name__ == "__main__":
    # Standalone testing for the dashboard widget
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    dashboard = FeedbackDashboard()
    dashboard.show()
    sys.exit(app.exec_())
