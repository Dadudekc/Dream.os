# tabs/SyncOpsTab.py

import os
import json
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QGroupBox, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt

# Import PathManager for unified log paths
from core.path_manager import PathManager
# Get the unified log file path for SyncOps sessions
SYNCOPS_LOG_FILE = str(PathManager().get_path("logs") / "syncops_sessions.json")

# Import the backend SyncOpsService for session and pomodoro management
from sync_ops.services.sync_ops_service import SyncOpsService

class SyncOpsTab(QWidget):
    def __init__(self, user_name="Victor", logger=None):
        super().__init__()
        self.user_name = user_name
        self.logger = logger
        # Delegate session logic to the backend service
        self.service = SyncOpsService(user_name=self.user_name, logger=self.logger)
        
        self.pomodoro_timer = QTimer()
        self.pomodoro_timer.timeout.connect(self.update_pomodoro_timer)
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        # Clock In/Out Group
        clock_box = QGroupBox("⏱ Clock In / Out")
        clock_layout = QHBoxLayout()

        self.clock_btn = QPushButton("Clock In")
        self.clock_btn.clicked.connect(self.toggle_clock)

        self.clock_status = QLabel("Not clocked in")
        self.clock_status.setStyleSheet("color: gray")

        clock_layout.addWidget(self.clock_btn)
        clock_layout.addWidget(self.clock_status)
        clock_box.setLayout(clock_layout)
        layout.addWidget(clock_box)

        # Pomodoro Timer Group
        pomo_box = QGroupBox("🍅 Pomodoro Timer")
        pomo_layout = QHBoxLayout()

        self.pomo_start_btn = QPushButton("Start Pomodoro")
        self.pomo_start_btn.clicked.connect(self.toggle_pomodoro)

        self.pomo_label = QLabel("25:00")
        self.pomo_label.setAlignment(Qt.AlignCenter)
        self.pomo_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        pomo_layout.addWidget(self.pomo_start_btn)
        pomo_layout.addWidget(self.pomo_label)
        pomo_box.setLayout(pomo_layout)
        layout.addWidget(pomo_box)

        # Log Feed Group
        log_box = QGroupBox("📜 Session Log")
        log_layout = QVBoxLayout()

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)

        log_layout.addWidget(self.log_display)
        log_box.setLayout(log_layout)
        layout.addWidget(log_box)

        self.setLayout(layout)

    def toggle_clock(self):
        try:
            if self.service.is_clocked_in:
                msg = self.service.clock_out()
                self.clock_btn.setText("Clock In")
                self.clock_status.setText("Not clocked in")
                self.clock_status.setStyleSheet("color: gray")
            else:
                msg = self.service.clock_in()
                self.clock_btn.setText("Clock Out")
                self.clock_status.setText("Clocked in")
                self.clock_status.setStyleSheet("color: green")
            self._log_event(msg)
        except Exception as e:
            self._log_event(f"Error: {str(e)}")

    def toggle_pomodoro(self):
        try:
            if self.service.pomodoro_running:
                msg = self.service.stop_pomodoro()
                self.pomodoro_timer.stop()
                self.pomo_start_btn.setText("Start Pomodoro")
            else:
                msg = self.service.start_pomodoro()
                self.pomodoro_timer.start(1000)
                self.pomo_start_btn.setText("Stop Pomodoro")
            self._log_event(msg)
        except Exception as e:
            self._log_event(f"Error: {str(e)}")

    def update_pomodoro_timer(self):
        try:
            seconds_left = self.service.update_pomodoro()
            if seconds_left > 0:
                minutes = seconds_left // 60
                seconds = seconds_left % 60
                self.pomo_label.setText(f"{minutes:02d}:{seconds:02d}")
            else:
                # Timer completed: reset display and button
                self.pomo_start_btn.setText("Start Pomodoro")
                self.pomo_label.setText("25:00")
        except Exception as e:
            self._log_event(f"Error: {str(e)}")

    def _log_event(self, message, duration=None):
        now = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{now}] {self.user_name}: {message}"
        if duration:
            log_msg += f" (Duration: {str(duration).split('.')[0]})"
        self.log_display.append(log_msg)
        if self.logger:
            self.logger.info(log_msg)

    def save_session(self, event_type, timestamp, detail=None):
        record = {
            "user": self.user_name,
            "event": event_type,
            "timestamp": timestamp,
            "detail": detail
        }
        existing = []
        if os.path.exists(SYNCOPS_LOG_FILE):
            with open(SYNCOPS_LOG_FILE, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except Exception:
                    existing = []
        existing.append(record)
        with open(SYNCOPS_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)