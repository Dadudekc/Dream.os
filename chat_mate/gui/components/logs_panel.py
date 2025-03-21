from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTextEdit
)
from PyQt5.QtCore import Qt
from datetime import datetime

class LogsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Create header with controls
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Application Logs:"))
        
        # Add control buttons
        btn_clear = QPushButton("Clear Logs")
        btn_clear.clicked.connect(self.clear_logs)
        btn_export = QPushButton("Export Logs")
        btn_export.clicked.connect(self.export_logs)
        
        header_layout.addStretch()
        header_layout.addWidget(btn_clear)
        header_layout.addWidget(btn_export)
        layout.addLayout(header_layout)
        
        # Create log viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setLineWrapMode(QTextEdit.WidgetWidth)
        self.log_viewer.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                font-family: monospace;
                padding: 5px;
            }
        """)
        layout.addWidget(self.log_viewer)
        
        self.setLayout(layout)
        
    def append_log(self, message: str):
        """Add a timestamped message to the log viewer"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        self.log_viewer.append(formatted_message)
        
        # Auto-scroll to bottom
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def clear_logs(self):
        """Clear all logs from the viewer"""
        self.log_viewer.clear()
        self.append_log("Logs cleared")
        
    def export_logs(self):
        """Export logs to a file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"logs_export_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_viewer.toPlainText())
                
            self.append_log(f"Logs exported to {filename}")
        except Exception as e:
            self.append_log(f"Error exporting logs: {str(e)}")
            
    def get_logs(self) -> str:
        """Get all logs as text"""
        return self.log_viewer.toPlainText()
