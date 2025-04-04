# interfaces/pyqt/tabs/LogsTab.py

import os
import logging
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QComboBox, QLineEdit
)
from PyQt5.QtCore import Qt
from core.PathManager import PathManager
from typing import Dict, Any

class LogsTab(QWidget):
    """
    Provides a unified interface for viewing, filtering, and managing logs.
    """

    def __init__(self, services: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.services = services
        self.parent = parent
        
        self.logger = services.get('logger', logging.getLogger(__name__))
        self.path_manager = services.get('path_manager')
        
        if self.path_manager:
            try:
                self.logs_path = self.path_manager.get_path("logs")
            except KeyError:
                self.logger.error("PathManager missing 'logs' key. Falling back to CWD/logs.")
                self.logs_path = Path(os.getcwd()) / "logs"
                self.logs_path.mkdir(parents=True, exist_ok=True)
            except AttributeError:
                self.logger.warning("PathManager is likely mocked. Falling back to CWD/logs.")
                self.logs_path = Path(os.getcwd()) / "logs"
                self.logs_path.mkdir(parents=True, exist_ok=True)
        else:
            self.logger.error("PathManager service not found. Falling back to CWD/logs.")
            self.logs_path = Path(os.getcwd()) / "logs"
            self.logs_path.mkdir(parents=True, exist_ok=True)

        self.initUI()
        self.load_log_files()

    def initUI(self):
        layout = QVBoxLayout()

        # Header Label
        label = QLabel("System Logs & Feedback")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # Log file selector
        file_selector_layout = QHBoxLayout()
        self.log_label = QLabel("🗂 Select Log File:")
        self.log_selector = QComboBox()
        self.log_selector.currentIndexChanged.connect(self.load_selected_log)

        file_selector_layout.addWidget(self.log_label)
        file_selector_layout.addWidget(self.log_selector)
        layout.addLayout(file_selector_layout)

        # Filter input
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("🔍 Filter:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Type keyword to filter logs...")
        self.filter_input.textChanged.connect(self.filter_logs)
        filter_layout.addWidget(self.filter_input)
        layout.addLayout(filter_layout)

        # Log display area
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        # Buttons layout (Refresh, Clear Logs)
        button_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("🔄 Refresh Logs")
        self.refresh_btn.clicked.connect(self.load_log_files)

        self.clear_btn = QPushButton("🧹 Clear Display")
        self.clear_btn.clicked.connect(self.clear_logs)

        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.clear_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_log_files(self):
        """
        Populate the dropdown with available log files from unified log path.
        """
        self.log_selector.clear()
        self.files = sorted([
            f for f in self.logs_path.glob("*.*")
            if f.suffix.lower() in [".log", ".json", ".txt"]
        ])

        if not self.files:
            self.log_display.setPlainText("⚠️ No log files found.")
            return

        for log_file in self.files:
            self.log_selector.addItem(log_file.name)

        self.load_selected_log()

    def load_selected_log(self):
        """
        Load the content of the selected log file.
        """
        idx = self.log_selector.currentIndex()
        if idx < 0 or idx >= len(self.files):
            self.log_display.setPlainText("⚠️ No log file selected.")
            return

        log_file = self.files[idx]
        try:
            with open(log_file, "r", encoding="utf-8") as file:
                content = file.read()
                self.full_log_text = content
                self.log_display.setPlainText(content)
        except Exception as e:
            error_msg = f"❌ Error reading log: {str(e)}"
            self.log_display.setPlainText(error_msg)
            self.logger.error(error_msg)

    def filter_logs(self):
        """
        Filter the displayed logs based on the entered keyword.
        """
        keyword = self.filter_input.text().strip().lower()
        if not keyword:
            self.log_display.setPlainText(self.full_log_text)
            return

        filtered_content = "\n".join(
            line for line in self.full_log_text.splitlines()
            if keyword in line.lower()
        )
        self.log_display.setPlainText(filtered_content)

    def append_log(self, message: str):
        """
        Append a new log message to the display and internal logger.
        """
        self.log_display.append(message)
        self.logger.info(message)

    def append_output(self, message: str):
        """
        Alias for append_log to maintain compatibility.
        """
        self.append_log(message)

    def clear_logs(self):
        """
        Clear the log display.
        """
        self.log_display.clear()
        self.append_log("[LOG DISPLAY CLEARED]")
