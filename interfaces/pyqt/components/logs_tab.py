from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

class LogsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        
        # Log Viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        layout.addWidget(QLabel("Application Logs:"))
        layout.addWidget(self.log_viewer)
        
        self.setLayout(layout)

    def append_log(self, message: str):
        """Add a message to the log viewer"""
        self.log_viewer.append(message)

    def clear_logs(self):
        """Clear all logs from the viewer"""
        self.log_viewer.clear()

    def get_logs(self) -> str:
        """Get all logs as text"""
        return self.log_viewer.toPlainText() 