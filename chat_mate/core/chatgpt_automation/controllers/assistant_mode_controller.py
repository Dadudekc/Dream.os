import threading
import logging
import time
import os

# These imports represent your dedicated services for each input mode.
# They should implement:
# - speech_input_service.listen_and_transcribe() for voice input.
# - log_monitor_service.get_latest_log() for log scraping input.
from .speech_input_service import listen_and_transcribe
from .log_monitor_service import get_latest_log
from .assistant_parser import parse_input
from .assistant_orchestrator import dispatch_action

class AssistantModeController:
    def __init__(self, engine=None):
        self.logger = logging.getLogger(__name__)
        self._active = False
        self._input_source = "log"  # default input mode: "log" or "voice"
        self._thread = None
        self._stop_event = threading.Event()
        self.engine = engine

    def set_input_source(self, source):
        """
        Set the input source for Assistant Mode.
        :param source: 'log' or 'voice'
        """
        if source not in ("log", "voice"):
            self.logger.error("Invalid input source. Must be 'log' or 'voice'.")
            return
        self._input_source = source
        self.logger.info(f"Input source set to: {self._input_source}")

    def start(self):
        if self._active:
            self.logger.info("Assistant Mode is already active.")
            return

        self.logger.info("Starting Assistant Mode...")
        self._active = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._active:
            self.logger.info("Assistant Mode is already inactive.")
            return

        self.logger.info("Stopping Assistant Mode...")
        self._active = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join()
        self.logger.info("Assistant Mode stopped.")

    def is_active(self):
        return self._active

    def _run_loop(self):
        self.logger.info("Assistant Mode loop started using '{}' input.".format(self._input_source))
        while not self._stop_event.is_set():
            try:
                if self._input_source == "voice":
                    # Voice Input Mode: Use the speech_input_service to transcribe
                    transcript = listen_and_transcribe()
                    if transcript:
                        self.logger.info(f"[Voice] Transcript received: {transcript}")
                        intent = parse_input(transcript)
                        dispatch_action(intent)
                elif self._input_source == "log":
                    # Log Scrape Mode: Monitor the log file for new entries
                    transcript = get_latest_log()
                    if transcript:
                        self.logger.info(f"[Log] New log entry: {transcript}")
                        intent = parse_input(transcript)
                        dispatch_action(intent)
                else:
                    self.logger.error("Unknown input source encountered.")
            except Exception as e:
                self.logger.error(f"Error in Assistant Mode loop: {str(e)}")
            # Adjust the sleep interval as needed to balance responsiveness with resource use.
            time.sleep(0.5)
        self.logger.info("Assistant Mode loop exiting.")
