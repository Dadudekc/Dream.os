# sync_ops/services/sync_ops_service.py

import os
import json
from datetime import datetime, timedelta

class SyncOpsService:
    SYNCOPS_LOG_FILE = "syncops_sessions.json"
    POMODORO_DURATION = 25 * 60  # 25 minutes in seconds

    def __init__(self, user_name="Victor", logger=None):
        """
        Initialize the SyncOpsService.
        
        :param user_name: The name of the user.
        :param logger: Optional logger to handle log output.
        """
        self.user_name = user_name
        self.logger = logger
        self.is_clocked_in = False
        self.current_session_start = None
        self.pomodoro_running = False
        self.pomodoro_time_left = self.POMODORO_DURATION

    def clock_in(self):
        """
        Clock in the user. Records the start time and logs the event.
        """
        if self.is_clocked_in:
            raise Exception("Already clocked in.")
        self.current_session_start = datetime.now()
        self.is_clocked_in = True
        self.log_event("Clocked in")
        self.save_session("clock_in", self.current_session_start.isoformat())
        return "Clocked in successfully."

    def clock_out(self):
        """
        Clock out the user. Calculates the session duration and logs the event.
        """
        if not self.is_clocked_in:
            raise Exception("Not clocked in.")
        end_time = datetime.now()
        duration = end_time - self.current_session_start
        self.is_clocked_in = False
        self.log_event("Clocked out", duration)
        self.save_session("clock_out", end_time.isoformat(), str(duration))
        return f"Clocked out. Session Duration: {str(duration).split('.')[0]}"

    def start_pomodoro(self):
        """
        Start a Pomodoro session. Resets the timer and logs the event.
        """
        if self.pomodoro_running:
            raise Exception("Pomodoro already running.")
        self.pomodoro_time_left = self.POMODORO_DURATION
        self.pomodoro_running = True
        self.log_event("Pomodoro started")
        self.save_session("pomodoro_started", datetime.now().isoformat())
        return "Pomodoro started."

    def stop_pomodoro(self):
        """
        Stop the Pomodoro session and log the event.
        """
        if not self.pomodoro_running:
            raise Exception("Pomodoro is not running.")
        self.pomodoro_running = False
        self.log_event("Pomodoro stopped")
        self.save_session("pomodoro_stopped", datetime.now().isoformat())
        return "Pomodoro stopped."

    def update_pomodoro(self):
        """
        Update the Pomodoro timer. Decrements the time left by 1 second.
        When the timer reaches zero, it stops the session and logs completion.
        
        :return: The remaining time in seconds, or 0 if completed.
        """
        if not self.pomodoro_running:
            raise Exception("Pomodoro is not running.")
        if self.pomodoro_time_left > 0:
            self.pomodoro_time_left -= 1
            return self.pomodoro_time_left
        else:
            self.pomodoro_running = False
            self.log_event("Pomodoro complete ✅")
            self.save_session("pomodoro_complete", datetime.now().isoformat())
            return 0

    def log_event(self, message, duration=None):
        """
        Format and log an event message.
        
        :param message: The event message.
        :param duration: Optional duration for events like clock out.
        """
        now_str = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{now_str}] {self.user_name}: {message}"
        if duration:
            log_msg += f" (Duration: {str(duration).split('.')[0]})"
        if self.logger:
            self.logger.info(log_msg)
        else:
            print(log_msg)

    def save_session(self, event_type, timestamp, detail=None):
        """
        Save a session event to the syncops_sessions.json file.
        
        :param event_type: Type of the event (e.g., clock_in, clock_out).
        :param timestamp: ISO timestamp of the event.
        :param detail: Optional detail about the event (like duration).
        """
        record = {
            "user": self.user_name,
            "event": event_type,
            "timestamp": timestamp,
            "detail": detail
        }
        existing = []
        if os.path.exists(self.SYNCOPS_LOG_FILE):
            with open(self.SYNCOPS_LOG_FILE, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except Exception:
                    existing = []
        existing.append(record)
        with open(self.SYNCOPS_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)