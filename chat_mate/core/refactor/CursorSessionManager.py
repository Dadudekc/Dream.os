#!/usr/bin/env python3
"""
CursorSessionManager with Task Queue, History, Auto-Accept, and Prompt Batch Builder
 
This class merges features:
  - UI calibration for Cursor
  - Task queueing (auto or manual accept)
  - Building batch prompts from tasks
  - Dynamic 'Accept' button detection
  - Execution history
  - Optional dry-run mode for safe testing
"""

import time
import sys
import json
import os
import logging
import threading
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from queue import Queue, Empty

DRY_RUN = "--dry-run" in sys.argv
if not DRY_RUN:
    import pyautogui
    import pygetwindow as gw
else:
    print("Running in DRY-RUN mode: UI actions will be simulated.")

# ------------------
# GLOBAL CONFIG
# ------------------
WINDOW_TITLE = "Cursor"
TYPING_SPEED = 0.03
MAX_WAIT_TIME = 600
POLL_INTERVAL = 2
ACCEPT_IMAGE = "accept_button.png"
CALIBRATION_FILE = "calibration.json"
LOG_FILE = "cursor_manager.log"

DEFAULT_PROMPT_BOX_COORDS = (300, 1050)
DEFAULT_ACCEPT_BUTTON_COORDS = (1800, 500)

# -------------
# LOGGING SETUP
# -------------
logger = logging.getLogger("CursorSessionManager")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(console_handler)


class CursorSessionManager:
    """
    Unified class that handles:
      1) UI calibration for Cursor (prompt box + accept button)
      2) Task queueing with auto/manual acceptance
      3) Batch prompt building (optional)
      4) Dynamic wait for 'Accept' detection
      5) Execution history of tasks
    """

    # Define the DEFAULT_HOTKEYS dictionary as a class attribute
    DEFAULT_HOTKEYS = {
        "submit_prompt": "enter",
        "cancel_operation": "escape",
        "accept_suggestion": "tab"
    }

    def __init__(self, project_root: str = ".", dry_run: bool = DRY_RUN):
        """
        Args:
            project_root (str): Directory for launching Cursor (if you do so).
            dry_run (bool): If True, simulates all actions, no real UI interaction.
        """
        self.project_root = project_root
        self.dry_run = dry_run
        self.logger = logger

        # Hotkeys or extended actions can be placed here if needed
        self.auto_accept = False   # Toggle for automatically processing tasks
        self.task_queue = Queue()  # Thread-safe queue
        self.execution_history: List[Dict[str, Any]] = []  # Store results

        # If you need a background thread for tasks, you can do so:
        self._active = False
        self._thread = threading.Thread(target=self._task_loop, daemon=True)

        # Coordinates for prompt box / accept button
        self.prompt_box_coords: Optional[tuple] = None
        self.accept_button_coords: Optional[tuple] = None
        self._load_or_calibrate_coords()

        # Allows external or GUI callback to update the UI
        self._on_update: Optional[Callable[[Dict[str, Any]], None]] = None

    # ---------------
    # COORD CALIBRATION
    # ---------------
    def _load_or_calibrate_coords(self):
        """Load from JSON or calibrate if not found."""
        if os.path.exists(CALIBRATION_FILE):
            try:
                with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                    coords = json.load(f)
                self.prompt_box_coords = tuple(coords.get("prompt_box", DEFAULT_PROMPT_BOX_COORDS))
                self.accept_button_coords = tuple(coords.get("accept_button", DEFAULT_ACCEPT_BUTTON_COORDS))
                self.logger.info(f"Loaded calibrated coords from {CALIBRATION_FILE}: {coords}")
            except Exception as e:
                self.logger.error(f"Error loading calibration file: {e}")
                # fallback
                self.prompt_box_coords = DEFAULT_PROMPT_BOX_COORDS
                self.accept_button_coords = DEFAULT_ACCEPT_BUTTON_COORDS
        else:
            self.logger.info("=== No calibration file found; starting calibration ===")
            self.prompt_box_coords = self._calibrate("Calibrate Prompt Input Box:")
            self.accept_button_coords = self._calibrate("Calibrate Accept Button:")
            self._save_calibrated_coords({
                "prompt_box": self.prompt_box_coords,
                "accept_button": self.accept_button_coords
            })

    def _save_calibrated_coords(self, coords: dict):
        try:
            with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
                json.dump(coords, f, indent=2)
            self.logger.info(f"Saved coords: {coords}")
        except Exception as e:
            self.logger.error(f"Failed to save coords: {e}")

    def _calibrate(self, prompt: str) -> tuple:
        if self.dry_run:
            self.logger.info(f"(Dry-run) Calibration prompt: {prompt}")
            return (100, 100)
        print(prompt)
        input("Place your mouse over the target and press Enter to record position...")
        pos = pyautogui.position()
        self.logger.info(f"Recorded coords {pos} for {prompt}")
        return (pos.x, pos.y)

    # ---------------
    # PUBLIC TASK METHODS
    # ---------------
    def queue_task(self, prompt_text: str, context: Optional[Dict[str, Any]] = None):
        """
        Add a prompt to the queue. If auto_accept is True, it processes immediately in the background thread.
        """
        task = {
            "prompt_text": prompt_text,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "accepted": False,
        }
        self.task_queue.put(task)
        self.logger.info(f"Queued task: {prompt_text[:50]}...")

    def start_loop(self):
        """Start the background loop that processes tasks if auto_accept is True."""
        if not self._active:
            self._active = True
            self._thread.start()
            self.logger.info("CursorSessionManager loop started.")

    def stop_loop(self):
        """Stop the background loop."""
        self._active = False
        self.logger.info("CursorSessionManager loop stopping...")

    def accept_next_task(self):
        """
        Manually accept & execute the next queued task. (If auto_accept=False)
        Equivalent to a user clicking 'Accept' in a GUI.
        """
        try:
            task = self.task_queue.get_nowait()
            task["accepted"] = True
            self._execute_task(task)
        except Empty:
            self.logger.warning("No tasks to accept.")

    def toggle_auto_accept(self, enabled: bool):
        """Enable/Disable auto_accept mode."""
        self.auto_accept = enabled
        self.logger.info(f"Auto-accept set to {enabled}")

    def set_on_update_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a UI or external callback for updates (task completions, errors)."""
        self._on_update = callback

    def build_prompt_batch(self, tasks: List[str]) -> str:
        """
        Optional helper: Combine multiple tasks into one prompt string.
        Like a 'batch prompt builder'.
        """
        lines = "\n".join(f"{i+1}. {t}" for i, t in enumerate(tasks))
        return f"# BATCH TASKS:\n\n{lines}\n"

    def run_overnight_mode(self, prompts: List[str]):
        """
        Simple method: no background thread.
        Directly process a batch of prompts in sequential order, ignoring self.task_queue.
        """
        self.logger.info("=== Starting Overnight Mode (direct batch) ===")
        for i, prompt in enumerate(prompts, start=1):
            self.logger.info(f"--- Processing prompt {i}/{len(prompts)}: {prompt[:50]}... ---")
            # Build a single task
            task = {
                "prompt_text": prompt,
                "context": {},
                "timestamp": datetime.now().isoformat(),
                "accepted": True,
            }
            self._execute_task(task)
        self.logger.info("=== Overnight Mode Complete ===")

    # ---------------
    # INTERNAL LOOP
    # ---------------
    def _task_loop(self):
        """Background loop that auto-accepts tasks if self.auto_accept=True."""
        while self._active:
            try:
                task = self.task_queue.get(timeout=1)
                if self.auto_accept:
                    task["accepted"] = True
                    self._execute_task(task)
                else:
                    # Let the user manually call accept_next_task
                    # Or pass the 'pending' task to a UI callback
                    if self._on_update:
                        self._on_update(task)
            except Empty:
                continue
        self.logger.info("CursorSessionManager loop exited.")

    # ---------------
    # EXECUTION LOGIC
    # ---------------
    def _execute_task(self, task: Dict[str, Any]):
        """
        Actually run the prompt in Cursor:
          1) Focus window
          2) Click prompt box
          3) Type the prompt + context
          4) Wait for dynamic or fallback
          5) Click accept
        """
        try:
            # Possibly inject context
            prompt_text = self._inject_context(task["prompt_text"], task["context"])
            # Mark start time
            start_ts = time.time()

            # Step 1: Focus
            if not self._focus_cursor_window():
                self.logger.error("Cannot focus Cursor window, aborting task.")
                return

            # Step 2: Click prompt box
            self._click_coordinate(self.prompt_box_coords)

            # Step 3: Type the prompt
            prompt_summary = prompt_text[:75].replace("\n", "\\n")
            self.logger.info(f"Typing prompt: {prompt_summary}...")
            self._type_prompt_and_send(prompt_text)

            # Step 4: Wait for dynamic accept
            if self._wait_for_response(MAX_WAIT_TIME):
                self.logger.info("Clicking detected Accept button...")
                self._click_coordinate(self.accept_button_coords)
            else:
                fallback = 30
                self.logger.warning(f"Dynamic wait timed out. Using fallback {fallback} seconds.")
                time.sleep(fallback)
                self._click_coordinate(self.accept_button_coords)

            # Step 5: Simulate or retrieve a response
            end_ts = time.time()
            # For now, we use a stub
            simulated_response = f"[Simulated Code from Prompt] TimeSpent={round(end_ts - start_ts,1)}s"

            # Construct an outcome
            outcome = {
                "task": task["prompt_text"],
                "context": task["context"],
                "response": simulated_response,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            self.execution_history.append(outcome)
            if self._on_update:
                self._on_update(outcome)

            self.logger.info(f"Task executed successfully. Elapsed={round(end_ts - start_ts,2)}s")

        except Exception as e:
            self.logger.error(f"Failed to execute task: {e}")
            if self._on_update:
                self._on_update({"error": str(e), "timestamp": datetime.now().isoformat()})

    # ---------------
    # HELPER METHODS
    # ---------------
    def _inject_context(self, prompt_text: str, context: Dict[str, Any]) -> str:
        """
        Optionally attach context as JSON. If you prefer advanced Jinja or some templating,
        you can do it here.
        """
        if context:
            serialized = json.dumps(context, indent=2)
            return f"{prompt_text}\n\n# CONTEXT:\n{serialized}"
        return prompt_text

    def _focus_cursor_window(self) -> bool:
        if self.dry_run:
            self.logger.info("(Dry-run) Would focus Cursor window.")
            return True
        try:
            windows = gw.getWindowsWithTitle(WINDOW_TITLE)
            if not windows:
                self.logger.error(f"Cannot find window titled '{WINDOW_TITLE}'")
                return False
            win = windows[0]
            win.activate()
            time.sleep(1)
            self.logger.info(f"Focused window '{WINDOW_TITLE}'")
            return True
        except Exception as e:
            self.logger.warning(f"Could not activate Cursor window: {e}")
            return False

    def _click_coordinate(self, coords: tuple):
        if self.dry_run:
            self.logger.info(f"(Dry-run) Would click at {coords}")
        else:
            pyautogui.moveTo(coords[0], coords[1])
            pyautogui.click()
        time.sleep(0.5)

    def _type_prompt_and_send(self, prompt: str):
        if self.dry_run:
            self.logger.info(f"(Dry-run) Would type: {prompt[:60]}...")
            self.logger.info("(Dry-run) Would press Enter.")
        else:
            pyautogui.write(prompt, interval=TYPING_SPEED)
            pyautogui.press("enter")

    def _wait_for_response(self, timeout: int) -> bool:
        if self.dry_run:
            self.logger.info("(Dry-run) Simulating dynamic wait.")
            return True
        self.logger.info("Waiting dynamically for Accept button...")
        start = time.time()
        while time.time() - start < timeout:
            location = pyautogui.locateOnScreen(ACCEPT_IMAGE, confidence=0.9)
            if location:
                self.logger.info(f"Detected Accept at {location}")
                return True
            time.sleep(POLL_INTERVAL)
        return False

    # ---------------
    # SHUTDOWN
    # ---------------
    def shutdown(self):
        """Cleanly stop background loop if running."""
        self.logger.info("Shutting down CursorSessionManager...")
        self.stop_loop()
        self.logger.info("Shutdown complete.")

# -------------------------
# Test or Demo "main"
# -------------------------
def _demo():
    logging.basicConfig(level=logging.INFO)
    mgr = CursorSessionManager(project_root=".", dry_run=DRY_RUN)

    # Example usage: start background loop, queue tasks
    mgr.toggle_auto_accept(False)  # Or True for immediate execution
    mgr.start_loop()

    mgr.queue_task("Test prompt #1", {"foo": "bar"})
    mgr.queue_task("Test prompt #2", {"baz": 123})
    
    # Now we can either accept them manually:
    time.sleep(2)
    mgr.accept_next_task()  # accept #1
    time.sleep(2)
    mgr.accept_next_task()  # accept #2

    # Or if auto_accept was True, they'd run automatically

    # Overnight mode ignoring the queue:
    # mgr.run_overnight_mode(["Large Prompt #1", "Large Prompt #2"])

    time.sleep(5)
    mgr.shutdown()
    print("History:", mgr.execution_history)

if __name__ == "__main__":
    if DRY_RUN:
        logger.info("Running new CursorSessionManager in DRY-RUN mode.")
    _demo()
