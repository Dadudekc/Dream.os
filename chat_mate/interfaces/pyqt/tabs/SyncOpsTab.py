# /tabs/SyncOpsTab.py

import os
import json
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QLineEdit, QGroupBox, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt

SYNCOPS_LOG_FILE = "syncops_sessions.json"

class SyncOpsTab(QWidget):
    def __init__(self, user_name="Victor", logger=None):
        super().__init__()
        self.user_name = user_name
        self.logger = logger
        self.is_clocked_in = False
        self.current_session_start = None
        self.pomodoro_running = False
        self.pomodoro_timer = QTimer()
        self.pomodoro_time_left = 25 * 60  # 25 minutes

        self._init_ui()
        self.pomodoro_timer.timeout.connect(self.update_pomodoro_timer)

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

        # Pomodoro Group
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

        # Log Feed
        log_box = QGroupBox("📜 Session Log")
        log_layout = QVBoxLayout()

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)

        log_layout.addWidget(self.log_display)
        log_box.setLayout(log_layout)
        layout.addWidget(log_box)

        self.setLayout(layout)

    def toggle_clock(self):
        if self.is_clocked_in:
            end_time = datetime.now()
            duration = end_time - self.current_session_start
            self.is_clocked_in = False
            self.clock_btn.setText("Clock In")
            self.clock_status.setText("Not clocked in")
            self.clock_status.setStyleSheet("color: gray")
            self._log_event("Clocked out", duration)
            self.save_session("clock_out", end_time.isoformat(), str(duration))
        else:
            self.current_session_start = datetime.now()
            self.is_clocked_in = True
            self.clock_btn.setText("Clock Out")
            self.clock_status.setText("Clocked in")
            self.clock_status.setStyleSheet("color: green")
            self._log_event("Clocked in")
            self.save_session("clock_in", self.current_session_start.isoformat())

    def toggle_pomodoro(self):
        if self.pomodoro_running:
            self.pomodoro_timer.stop()
            self.pomodoro_running = False
            self.pomo_start_btn.setText("Start Pomodoro")
            self._log_event("Pomodoro stopped")
        else:
            self.pomodoro_time_left = 25 * 60
            self.pomodoro_timer.start(1000)
            self.pomodoro_running = True
            self.pomo_start_btn.setText("Stop Pomodoro")
            self._log_event("Pomodoro started")

    def update_pomodoro_timer(self):
        if self.pomodoro_time_left > 0:
            self.pomodoro_time_left -= 1
            minutes = self.pomodoro_time_left // 60
            seconds = self.pomodoro_time_left % 60
            self.pomo_label.setText(f"{minutes:02d}:{seconds:02d}")
        else:
            self.pomodoro_timer.stop()
            self.pomodoro_running = False
            self.pomo_start_btn.setText("Start Pomodoro")
            self._log_event("Pomodoro complete ✅")
            self.save_session("pomodoro_complete", datetime.now().isoformat())

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
                existing = json.load(f)
        existing.append(record)
        with open(SYNCOPS_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
