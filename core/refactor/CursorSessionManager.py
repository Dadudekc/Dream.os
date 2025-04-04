#!/usr/bin/env python3
"""
CursorSessionManager with Task Queue, History, Auto-Accept, Prompt Batch Builder, Lifecycle Hooks,
UI calibration, test generation & coverage analysis, overnight mode, dry-run mode, and more.

Merged Features:
  - UI calibration for Cursor
  - Task queueing (auto or manual accept) with priority sorting
  - Building batch prompts from tasks
  - Dynamic 'Accept' button detection
  - Execution history (success/failure tracking)
  - Lifecycle hooks for validate/inject/approve/dispatch
  - Optional test generation and coverage analysis
  - Optional overnight/batch mode
  - Dry-run mode for safe UI testing
"""

import time
import sys
import json
import os
import logging
import threading
from typing import Any, Dict, List, Optional, Callable, Tuple
from datetime import datetime
from queue import Queue, Empty
import uuid  # For generating unique task IDs
import random
import pyperclip  # For clipboard operations

# Flag for simulating UI interactions (no real pyautogui or window focus)
DRY_RUN = "--dry-run" in sys.argv
if not DRY_RUN:
    import pyautogui
    import pygetwindow as gw
else:
    print("Running in DRY-RUN mode: UI actions will be simulated.")

# Attempt to import lifecycle hooks & test generation services
try:
    from core.services.PromptLifecycleHooksService import PromptLifecycleHooksService
    from core.services.TestGeneratorService import TestGeneratorService
except ImportError:
    PromptLifecycleHooksService = None
    TestGeneratorService = None

# -------------------
# GLOBAL CONFIG
# -------------------
WINDOW_TITLE = "Cursor"
TYPING_SPEED = 0.03
MAX_WAIT_TIME = 300
POLL_INTERVAL = 2
ACCEPT_IMAGE = "accept_button.png"
CALIBRATION_FILE = "calibration.json"
LOG_FILE = "cursor_manager.log"

# Default coordinates if calibration or image detection fails
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
    A unified manager for:
      1) UI calibration for Cursor (prompt box + accept button)
      2) Task queueing with auto/manual acceptance
      3) Batch prompt building (optional)
      4) Dynamic wait for 'Accept' button detection
      5) Execution history (success/failure tracking)
      6) Lifecycle hooks for validate/inject/approve/dispatch
      7) Optional test generation & coverage analysis
      8) Overnight/batch mode for direct prompt processing
      9) Dry-run mode for safe UI testing
    """

    DEFAULT_HOTKEYS = {
        "submit_prompt": "enter",
        "cancel_operation": "escape",
        "accept_suggestion": "tab"
    }

    def __init__(
        self,
        project_root: str = ".",
        dry_run: bool = DRY_RUN,
        # Optional, inject external services for context
        path_manager=None,
        memory_manager=None,
        state_manager=None,
        test_generator_service=None,
        lifecycle_hooks_service=None,
        service_registry=None
    ):
        """
        Args:
            project_root (str): Base directory for your project (files/tests, etc.).
            dry_run (bool): If True, simulates UI actions (no real clicks/typing).
            path_manager: (Optional) A PathManager-like service for resolving file paths.
            memory_manager: (Optional) A MemoryManager-like service for retrieving conversation context.
            state_manager: (Optional) A service to get current UI/app state.
            test_generator_service: (Optional) A service for test generation & coverage.
            lifecycle_hooks_service: (Optional) A service for hooking into validate/inject/approve/dispatch.
            service_registry: (Optional) A dict-like registry from which to pull services not directly passed in.
        """
        self.project_root = project_root
        self.dry_run = dry_run
        self.logger = logger

        # -------------------------
        # Inject or fetch services
        # -------------------------
        self.path_manager = path_manager
        self.memory_manager = memory_manager
        self.state_manager = state_manager
        self.test_generator_service = test_generator_service
        self.lifecycle_hooks = lifecycle_hooks_service

        if service_registry:
            self.path_manager = self.path_manager or service_registry.get('path_manager')
            self.memory_manager = self.memory_manager or service_registry.get('memory_manager')
            self.state_manager = self.state_manager or service_registry.get('state_manager')
            self.test_generator_service = self.test_generator_service or service_registry.get('test_generator_service')
            self.lifecycle_hooks = self.lifecycle_hooks or service_registry.get('lifecycle_hooks_service')

        if not self.lifecycle_hooks and PromptLifecycleHooksService is not None:
            self.lifecycle_hooks = PromptLifecycleHooksService(logger=self.logger)
            self._configure_default_hooks()
        elif not self.lifecycle_hooks:
            self.logger.warning("No LifecycleHooksService provided; skipping hook configuration.")

        # ----------------------
        # Core Manager Attributes
        # ----------------------
        self.auto_accept = False
        self.task_queue = Queue()
        self.execution_history: List[Dict[str, Any]] = []

        # Thread loop management
        self._active = False
        self._thread = threading.Thread(target=self._task_loop, daemon=True)

        # Coordinates
        self.prompt_box_coords: Optional[tuple] = None
        self.accept_button_coords: Optional[tuple] = None
        self._load_or_calibrate_coords()

        # Optional callback for external updates (UI or logs)
        self._on_update: Optional[Callable[[Dict[str, Any]], None]] = None

    # ---------------------------------------
    # COORDINATE CALIBRATION & PERSISTENCE
    # ---------------------------------------
    def _load_or_calibrate_coords(self):
        """Load coordinates for the prompt box & accept button, or run calibration if missing."""
        if os.path.exists(CALIBRATION_FILE):
            try:
                with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                    coords = json.load(f)
                self.prompt_box_coords = tuple(coords.get("prompt_box", DEFAULT_PROMPT_BOX_COORDS))
                self.accept_button_coords = tuple(coords.get("accept_button", DEFAULT_ACCEPT_BUTTON_COORDS))
                self.logger.info(f"Loaded calibrated coords from {CALIBRATION_FILE}: {coords}")
            except Exception as e:
                self.logger.error(f"Error loading calibration file: {e}")
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

    def _calibrate(self, prompt: str) -> tuple:
        """Prompt the user to hover over a location and press Enter to record the mouse position."""
        if self.dry_run:
            self.logger.info(f"(Dry-run) {prompt} -> using placeholder (100,100)")
            return (100, 100)
        print(prompt)
        input("Hover your mouse over the target and press Enter...")
        pos = pyautogui.position()
        self.logger.info(f"Recorded coords {pos} for {prompt}")
        return (pos.x, pos.y)

    def _save_calibrated_coords(self, coords: dict):
        """Write calibrated coords to a JSON file."""
        try:
            with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
                json.dump(coords, f, indent=2)
            self.logger.info(f"Saved coords to {CALIBRATION_FILE}: {coords}")
        except Exception as e:
            self.logger.error(f"Failed to save coords: {e}")

    # --------------
    # PUBLIC METHODS
    # --------------
    def queue_task(self, prompt_or_dict) -> Optional[str]:
        """
        Add a new task to the queue. If given a string, wrap it in a dict.
        Returns:
            (str) The task_id if queued, else None if rejected or error.
        """
        try:
            task_id = f"task_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"

            if isinstance(prompt_or_dict, str):
                task_dict = {
                    "task_id": task_id,
                    "prompt": prompt_or_dict,
                    "queued_at": datetime.now().isoformat(),
                    "status": "queued",
                    "priority": "medium"
                }
            else:
                # Validate presence of 'prompt'
                if "prompt" not in prompt_or_dict:
                    self.logger.error("Task data must include 'prompt'. Rejecting.")
                    return None
                task_dict = prompt_or_dict.copy()
                task_dict["task_id"] = task_id
                task_dict["queued_at"] = datetime.now().isoformat()
                task_dict["status"] = "queued"
                if "priority" not in task_dict:
                    task_dict["priority"] = "medium"

            # Lifecycle: on_queue
            if self.lifecycle_hooks:
                queued_task = self.lifecycle_hooks.process_on_queue(task_dict)
                if queued_task is None:
                    self.logger.warning(f"Task {task_id} rejected in on_queue hook.")
                    if self._on_update:
                        self._on_update({
                            "event_type": "task_rejected",
                            "task_id": task_id,
                            "reason": "Rejected by on_queue lifecycle hook"
                        })
                    return None
                task_dict = queued_task

            self.task_queue.put(task_dict)
            self._sort_task_queue()

            if self._on_update:
                self._on_update({
                    "event_type": "queue_changed",
                    "queue_snapshot": self._get_queue_snapshot()
                })

            self.logger.info(f"Queued task {task_id}. Queue size={self.task_queue.qsize()}")
            return task_id

        except Exception as e:
            self.logger.error(f"Error queueing task: {e}", exc_info=True)
            return None

    def cancel_task(self, task_id: str) -> bool:
        """
        Remove a task from the queue by ID.
        Returns True if removed, False if not found.
        """
        try:
            with self.task_queue.mutex:
                current_list = list(self.task_queue.queue)
            new_list = [t for t in current_list if t.get("task_id") != task_id]

            if len(new_list) == len(current_list):
                # Not found
                self.logger.warning(f"Task {task_id} not found in queue.")
                return False

            # Rebuild queue
            with self.task_queue.mutex:
                self.task_queue.queue.clear()
                for t in new_list:
                    self.task_queue.queue.append(t)

            if self._on_update:
                # We'll try to find the original prompt for logging
                cancelled_prompt = "<No Prompt>"
                for t in current_list:
                    if t.get("task_id") == task_id:
                        cancelled_prompt = (t.get("prompt") or "")[:50] + "..."
                        break

                self._on_update({
                    "event_type": "task_cancelled",
                    "task_id": task_id,
                    "task_prompt": cancelled_prompt
                })
                self._on_update({
                    "event_type": "queue_changed",
                    "queue_snapshot": self._get_queue_snapshot()
                })

            self.logger.info(f"Cancelled task {task_id}. New queue size={self.task_queue.qsize()}")
            return True

        except Exception as e:
            self.logger.error(f"Error cancelling task {task_id}: {e}", exc_info=True)
            return False

    def update_task_priority(self, task_id: str, new_priority: str) -> bool:
        """
        Update the priority of a queued task (low, medium, high, critical).
        Returns True if updated, False otherwise.
        """
        valid_priorities = ["low", "medium", "high", "critical"]
        if new_priority not in valid_priorities:
            self.logger.warning(f"Invalid priority '{new_priority}'. Must be one of {valid_priorities}")
            return False

        found = False
        old_priority = None

        try:
            with self.task_queue.mutex:
                queue_list = list(self.task_queue.queue)
                for t in queue_list:
                    if t.get("task_id") == task_id:
                        old_priority = t.get("priority", "medium")
                        t["priority"] = new_priority
                        found = True
                        break

                if found:
                    # Sort after updating
                    queue_list.sort(key=lambda x: (
                        self._priority_rank(x.get("priority", "medium")),
                        x.get("queued_at", "")
                    ))
                    self.task_queue.queue.clear()
                    for item in queue_list:
                        self.task_queue.queue.append(item)

            if found:
                self.logger.info(f"Task {task_id} priority updated from {old_priority} to {new_priority}")
                if self._on_update:
                    self._on_update({
                        "event_type": "task_updated",
                        "task_id": task_id,
                        "field": "priority",
                        "old_value": old_priority,
                        "new_value": new_priority
                    })
                    self._on_update({
                        "event_type": "queue_changed",
                        "queue_snapshot": self._get_queue_snapshot()
                    })
                return True
            else:
                self.logger.warning(f"Task {task_id} not found for priority update.")
                return False

        except Exception as e:
            self.logger.error(f"Error updating priority for {task_id}: {e}", exc_info=True)
            return False

    def accept_next_task(self):
        """
        Manually accept the next queued task (FIFO by priority).
        """
        try:
            task = self.task_queue.get_nowait()
            task["accepted"] = True
            task["status"] = "processing"

            if self._on_update:
                self._on_update({
                    "event_type": "queue_changed",
                    "queue_snapshot": self._get_queue_snapshot()
                })

            # Run full lifecycle hooks if present
            if self.lifecycle_hooks:
                processed_task, messages = self.lifecycle_hooks.process_lifecycle(task)
                for msg in messages:
                    self.logger.debug(f"Lifecycle: {msg}")
                if processed_task is None:
                    self.logger.warning(f"Task {task.get('task_id','unknown')} was rejected in lifecycle.")
                    if self._on_update:
                        self._on_update({
                            "event_type": "task_rejected",
                            "task_id": task.get("task_id", "unknown"),
                            "reason": "Rejected in lifecycle"
                        })
                    return
                task = processed_task

            # Execute
            self._execute_task(task)

        except Empty:
            self.logger.info("No tasks to accept (queue is empty).")
            if self._on_update:
                self._on_update({"event_type": "queue_empty"})
        except Exception as e:
            self.logger.error(f"Error accepting next task: {e}", exc_info=True)

    def toggle_auto_accept(self, enabled: bool):
        """Enable/disable auto-accept mode (tasks will be processed automatically)."""
        self.auto_accept = enabled
        self.logger.info(f"Auto-accept set to {enabled}")

    def set_on_update_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register an external callback for event notifications (UI or logs)."""
        self._on_update = callback

    def build_prompt_batch(self, tasks: List[str]) -> str:
        """
        Combine multiple task prompts into a single batch prompt.
        """
        lines = "\n".join(f"{i+1}. {t}" for i, t in enumerate(tasks))
        return f"# BATCH TASKS:\n\n{lines}\n"

    def run_overnight_mode(self, prompts: List[Any]):
        """
        Bypasses the queue, directly processes a list of prompts/dicts in sequence.
        Good for automated "overnight" runs where you don't need manual acceptance.
        """
        self.logger.info("=== Starting Overnight Mode (direct sequential processing) ===")
        total = len(prompts)
        for i, p in enumerate(prompts, start=1):
            self.logger.info(f"--- Processing overnight prompt {i}/{total} ---")

            if isinstance(p, dict):
                if "prompt" not in p:
                    self.logger.error("Overnight prompt dict missing 'prompt' key; skipping.")
                    continue
                task_data = p.copy()
            else:
                task_data = {"prompt": str(p)}

            task_data.setdefault("task_id", f"overnight_{int(time.time())}_{i}")
            task_data.setdefault("queued_at", datetime.now().isoformat())
            task_data["status"] = "processing"
            task_data["accepted"] = True
            task_data.setdefault("priority", "medium")
            task_data.setdefault("source", "overnight_mode")

            try:
                self._execute_task(task_data)
                time.sleep(random.uniform(1, 3))  # short random delay
            except Exception as e:
                self.logger.error(f"Error in overnight task {task_data['task_id']}: {e}", exc_info=True)
                # Record immediate fail if not handled
                if not any(h["task_id"] == task_data["task_id"] for h in self.execution_history):
                    self.execution_history.append({
                        "task_id": task_data["task_id"],
                        "task_details": task_data,
                        "response": f"[Overnight Execution Failed: {e}]",
                        "success": False,
                        "timestamp": datetime.now().isoformat()
                    })

        self.logger.info(f"=== Overnight Mode Complete ({total} prompts processed) ===")

    # ---------------
    # INTERNAL LOOP
    # ---------------
    def start_loop(self):
        """Start the background thread for auto-accept task processing."""
        if not self._active:
            self._active = True
            if not self._thread.is_alive():
                self._thread = threading.Thread(target=self._task_loop, daemon=True)
            self._thread.start()
            self.logger.info("CursorSessionManager background loop started.")

    def stop_loop(self):
        """Stop the background thread."""
        self._active = False
        self.logger.info("Stopping CursorSessionManager loop...")
        if self._thread.is_alive():
            self._thread.join(timeout=2)
        self.logger.info("Loop stopped.")

    def _task_loop(self):
        """
        Automatically accepts tasks if auto_accept is enabled; 
        otherwise sets them to 'pending_manual' until accept_next_task() is called.
        """
        self.logger.info("Task loop is running. (Auto-accept={})".format(self.auto_accept))
        while self._active:
            try:
                task = self.task_queue.get(timeout=1)
                if not self._active:
                    # If we were asked to stop, put the task back
                    if task:
                        self.task_queue.put(task)
                    break

                if self.auto_accept:
                    task_id = task.get("task_id", "unknown")
                    self.logger.info(f"Auto-accepting task {task_id}...")
                    task["accepted"] = True
                    task["status"] = "processing_auto"

                    if self._on_update:
                        self._on_update({
                            "event_type": "queue_changed",
                            "queue_snapshot": self._get_queue_snapshot()
                        })

                    try:
                        # Lifecycle
                        if self.lifecycle_hooks:
                            processed_task, messages = self.lifecycle_hooks.process_lifecycle(task)
                            for msg in messages:
                                self.logger.debug(f"Lifecycle: {msg}")
                            if processed_task is None:
                                self.logger.warning(f"Task {task_id} was rejected during lifecycle.")
                                if self._on_update:
                                    self._on_update({
                                        "event_type": "task_rejected",
                                        "task_id": task_id,
                                        "reason": "Rejected in lifecycle"
                                    })
                                continue
                            task = processed_task

                        self._execute_task(task)

                    except Exception as e:
                        self.logger.error(f"Auto-exec error for task {task_id}: {e}", exc_info=True)
                        # If not recorded, record as failed
                        if not any(h["task_id"] == task_id and not h["success"] for h in self.execution_history):
                            self.execution_history.append({
                                "task_id": task_id,
                                "task_details": task,
                                "response": f"[Auto-execution error: {e}]",
                                "success": False,
                                "timestamp": datetime.now().isoformat()
                            })
                            if self._on_update:
                                self._on_update({
                                    "event_type": "task_failed",
                                    "task_id": task_id,
                                    "error": str(e)
                                })
                else:
                    # Manual mode: put it back as "pending_manual"
                    task["status"] = "pending_manual"
                    self.task_queue.put(task)
                    self._sort_task_queue()

                    if self._on_update:
                        self._on_update({
                            "event_type": "task_pending",
                            "task_id": task.get("task_id", ""),
                            "task_prompt": task.get("prompt", "<No Prompt>")[:50] + "..."
                        })
                        self._on_update({
                            "event_type": "queue_changed",
                            "queue_snapshot": self._get_queue_snapshot()
                        })

            except Empty:
                continue
            except Exception as loop_err:
                self.logger.error(f"Unexpected error in task loop: {loop_err}", exc_info=True)
                time.sleep(5)

        self.logger.info("Task loop exited.")

    # ---------------
    # EXECUTION LOGIC
    # ---------------
    def _execute_task(self, task: Dict[str, Any]):
        """
        Executes a single task, including:
          - Gathering the final prompt
          - UI automation (focus window, type/paste, wait for accept)
          - Clipboard capture
          - Test generation & coverage analysis (if configured)
          - Recording success/failure in execution_history
        """
        task_id = task.get("task_id", "unknown_task")
        prompt_text = task.get("prompt", "")

        if not prompt_text:
            self.logger.error(f"Task {task_id} has no prompt text. Cannot proceed.")
            self._record_task_failure(task, "Missing prompt text")
            return

        # Inform external callback that task started
        if self._on_update:
            try:
                self._on_update({
                    "event_type": "task_started",
                    "task_id": task_id,
                    "task_prompt": prompt_text[:50] + "..."
                })
            except Exception as e:
                self.logger.error(f"Error emitting task_started: {e}")

        generated_test_skeleton = None
        test_coverage_report = None
        final_prompt = prompt_text
        start_ts = time.time()

        try:
            # --- Lifecycle Stage Processing (if hooks service exists) ---
            if self.lifecycle_hooks:
                # Note: process_lifecycle handles running stages sequentially.
                # We call it here again to ensure all stages run if _execute_task
                # is called directly (like overnight mode).
                # The individual hook processing methods within process_lifecycle
                # should ideally be idempotent or handle being called multiple times.
                try:
                    processed_task, messages = self.lifecycle_hooks.process_lifecycle(task)
                    for msg in messages:
                        self.logger.debug(f"Lifecycle ({task_id}): {msg}")

                    if processed_task is None:
                        # Task rejected during processing within _execute_task
                        raise ValueError("Task rejected during lifecycle processing in _execute_task")

                    task = processed_task # Use the fully processed task
                    prompt_text = task.get("prompt", "") # Refresh potentially modified values
                    context = task.get("context", {})
                    final_prompt = task.get("formatted_prompt", prompt_text) # Get the final prompt

                except Exception as lifecycle_err:
                     self.logger.error(f"Error during lifecycle processing within _execute_task for {task_id}: {lifecycle_err}", exc_info=True)
                     # Re-raise as a specific error or handle differently? Re-raising for now.
                     raise ValueError(f"Lifecycle processing failed: {lifecycle_err}")

            else:
                # --- Legacy Context Injection (if no lifecycle hooks) ---
                try:
                    # Use the more comprehensive automatic context injection
                    final_prompt = self._inject_automatic_context(prompt_text, task)
                    # Update task context if _inject_automatic_context modifies it
                    context = task.get("context", {})
                except Exception as context_err:
                    self.logger.error(f"Error in legacy context injection for task {task_id}: {context_err}")
                    # Fallback to simple context injection
                    final_prompt = self._inject_context(prompt_text, context)

            # --- UI Interaction ---
            # Focus window must happen before clicking/typing
            if not self._focus_cursor_window():
                raise RuntimeError("Cannot focus Cursor window")

            self._click_coordinate(self.prompt_box_coords)
            prompt_summary = final_prompt[:75].replace('\n', '\\n') 
            self.logger.info(f"Typing prompt for task {task_id}: {prompt_summary}...")
            self._type_prompt_and_send(final_prompt)

            # Wait for accept button and click
            if self._wait_for_response(MAX_WAIT_TIME):
                self.logger.info("Clicking detected Accept button...")
                self._click_coordinate(self.accept_button_coords)
            else:
                # Fallback if accept button isn't detected
                fallback_wait = 30 # seconds
                self.logger.warning(f"Dynamic wait for Accept button timed out after {MAX_WAIT_TIME}s. "
                                   f"Attempting fallback click at {self.accept_button_coords} after {fallback_wait}s delay.")
                time.sleep(fallback_wait)
                self._click_coordinate(self.accept_button_coords) # Try clicking anyway

            end_ts = time.time()

            # --- Response Capture ---
            actual_response = "[Response Capture Failed: Clipboard Error or Empty]"
            try:
                # Add a slightly longer delay to ensure clipboard updates
                time.sleep(2.0)
                clipboard_content = pyperclip.paste()
                if clipboard_content:
                    actual_response = clipboard_content
                    self.logger.info(f"Captured response from clipboard (length={len(actual_response)}).")
                else:
                    self.logger.warning("Clipboard was empty after expected response generation.")
                    actual_response = "[Response Capture Warning: Clipboard Empty]"
            except pyperclip.PyperclipException as clip_err: # Catch specific pyperclip errors
                self.logger.error(f"Pyperclip error reading clipboard: {clip_err}")
                actual_response = f"[Response Capture Failed: PyperclipException - {clip_err}]"
            except Exception as e:
                 # Catch other potential errors
                 self.logger.exception(f"Unexpected error reading clipboard: {e}")
                 actual_response = f"[Response Capture Failed: Unexpected error - {e}]"

            # --- Test Generation & Coverage Analysis ---
            target_file_path = task.get("file_path") # Get file path from task
            # Determine if tests should be generated based on task flags/mode
            should_generate_tests = (
                task.get("generate_tests", False) or
                task.get("mode") in ["tdd", "coverage_driven", "test"] # Add 'test' as a trigger
            )
            # Check for feedback specifically for regeneration
            has_test_feedback = "test_feedback" in task
            test_feedback = task.get("test_feedback", {})
            # Determine if coverage should be analyzed
            should_analyze_coverage = (
                 task.get("analyze_coverage", False) or
                 task.get("mode") == "coverage_driven"
            )

            if target_file_path and self.test_generator_service:
                self.logger.info(f"Test strategy for {target_file_path}: "
                                f"generate={should_generate_tests}, "
                                f"has_feedback={has_test_feedback}, "
                                f"analyze_coverage={should_analyze_coverage}, "
                                f"mode={task.get('mode', 'post_implementation')}")
                try:
                    # 1. Regenerate tests based on feedback (if applicable)
                    if has_test_feedback and should_generate_tests:
                        self.logger.info(f"Regenerating tests for {target_file_path} based on feedback...")
                        regen_result = self.test_generator_service.regenerate_tests_based_on_feedback(
                            target_file_path, test_feedback
                        )
                        # Assuming regen returns path on success, None/False on failure
                        if regen_result:
                            generated_test_skeleton = f"[Regenerated test file: {regen_result}]"
                            task["generated_test_path"] = regen_result # Store the actual path
                            self.logger.info(f"✅ Successfully regenerated tests: {regen_result}")
                        else:
                            self.logger.warning(f"Failed to regenerate tests for {target_file_path} based on feedback.")
                            generated_test_skeleton = "[Test Regeneration Failed]"

                    # 2. Generate new tests (if no feedback regeneration happened)
                    elif should_generate_tests:
                        # Determine mode for generation
                        test_gen_mode = task.get("mode", "post_implementation")
                        # If coverage driven, prioritize that mode for generation
                        if should_analyze_coverage:
                            test_gen_mode = "coverage_driven"

                        self.logger.info(f"Generating tests for {target_file_path} with mode '{test_gen_mode}'...")
                        gen_result = self.test_generator_service.generate_tests(
                            target_file_path, mode=test_gen_mode
                        )
                         # Assuming gen returns path on success, None/False on failure
                        if gen_result:
                            generated_test_skeleton = f"[Generated test file: {gen_result}]"
                            task["generated_test_path"] = gen_result # Store actual path
                            self.logger.info(f"✅ Successfully generated test skeleton: {gen_result}")
                        else:
                            self.logger.warning(f"TestGeneratorService returned no skeleton for {target_file_path} (mode: {test_gen_mode}).")
                            generated_test_skeleton = "[Test Generation Failed - No skeleton returned]"

                    # 3. Analyze coverage (if requested)
                    if should_analyze_coverage and hasattr(self.test_generator_service, 'coverage_analyzer'):
                        self.logger.info(f"Analyzing test coverage for {target_file_path}...")
                        # Ensure the analyzer is available and method exists
                        if hasattr(self.test_generator_service.coverage_analyzer, 'get_coverage_report'):
                            coverage_report_data = self.test_generator_service.coverage_analyzer.get_coverage_report(target_file_path)
                            if coverage_report_data and "error" not in coverage_report_data:
                                test_coverage_report = coverage_report_data # Store the full report
                                coverage_percent = coverage_report_data.get('current_coverage', 0)
                                self.logger.info(f"✅ Coverage analysis complete: {coverage_percent:.2f}% covered.") # Format percentage

                                # Perform trend analysis (if method exists)
                                trend_analysis = {}
                                if hasattr(self.test_generator_service, 'analyze_test_coverage_trend'):
                                     trend_analysis = self.test_generator_service.analyze_test_coverage_trend(target_file_path)

                                # Update task metadata with structured coverage info
                                task["coverage_analysis"] = {
                                    "percentage": coverage_percent,
                                    "trend": trend_analysis.get("trend", coverage_report_data.get("trend", "unknown")), # Prefer trend analysis result
                                    "uncovered_lines": coverage_report_data.get("uncovered_lines", []),
                                    "uncovered_functions": coverage_report_data.get("uncovered_functions", []),
                                    "needs_improvement": trend_analysis.get("needs_improvement", False)
                                }
                            else:
                                error_msg = coverage_report_data.get('error', 'Unknown error') if coverage_report_data else 'No report data'
                                self.logger.warning(f"Coverage analysis failed or returned error: {error_msg}")
                                test_coverage_report = {"error": error_msg} # Store error info
                        else:
                             self.logger.warning("Coverage analyzer or 'get_coverage_report' method not found.")
                             test_coverage_report = {"error": "Coverage analyzer unavailable"}

                except Exception as test_gen_err:
                    self.logger.exception(f"❌ Error during test generation/analysis for {target_file_path}: {test_gen_err}")
                    generated_test_skeleton = f"[Test Generation/Analysis Error: {test_gen_err}]"
                    test_coverage_report = {"error": f"Exception during analysis: {test_gen_err}"}

            elif should_generate_tests and not target_file_path:
                 self.logger.warning(f"Cannot generate tests for task {task_id}: missing 'file_path' in task data.")
            elif should_generate_tests:
                 self.logger.warning(f"Cannot generate tests for task {task_id}: TestGeneratorService not available or not injected.")

            # --- Record Outcome ---
            outcome = {
                "task_id": task_id,
                "task_details": task, # Include the potentially updated task dict
                "response": actual_response,
                "generated_test_info": generated_test_skeleton, # Renamed for clarity
                "test_coverage_report": test_coverage_report,
                "success": True, # Assume success unless exception caught below
                "start_timestamp": start_ts,
                "end_timestamp": end_ts,
                "duration_seconds": round(end_ts - start_ts, 2),
                "timestamp": datetime.now().isoformat() # Completion timestamp
            }
            self.execution_history.append(outcome)

            # --- Emit Completion Event ---
            if self._on_update:
                try:
                    completion_payload = {
                        "event_type": "task_completed",
                        "task_id": task_id,
                        "task_prompt": prompt_text[:50] + "...",
                        "response_snippet": actual_response[:100] + ("..." if len(actual_response) > 100 else ""), # Snippet only
                        "generated_test_path": task.get("generated_test_path"), # Pass path if generated
                        "coverage_analysis": task.get("coverage_analysis"), # Pass structured analysis
                        "duration": outcome["duration_seconds"]
                    }
                    self._on_update(completion_payload)
                except Exception as e:
                    self.logger.error(f"Error calling on_update at task completion: {e}")

            self.logger.info(f"Task {task_id} executed successfully. Elapsed={outcome['duration_seconds']}s")

        # --- Handle Execution Failure ---
        # This except block corresponds to the main try starting on line 595
        except Exception as e: 
            end_ts = time.time()
            error_str = str(e)
            self.logger.exception(f"Failed to execute task {task_id}: {error_str}") # Log full traceback

            # Record failure in history
            failure_outcome = {
                "task_id": task_id,
                "task_details": task,
                "response": f"[Execution Failed: {error_str}]",
                "generated_test_info": generated_test_skeleton, # Include any partial results
                "test_coverage_report": test_coverage_report,
                "success": False,
                "error_message": error_str,
                "start_timestamp": start_ts, # Include start time
                "end_timestamp": end_ts,
                "duration_seconds": round(end_ts - start_ts, 2),
                "timestamp": datetime.now().isoformat()
            }
            self.execution_history.append(failure_outcome)

            # Emit failure event
            if self._on_update:
                try:
                    self._on_update({
                        "event_type": "task_failed",
                        "task_id": task_id,
                        "task_prompt": prompt_text[:50] + "...",
                        "error": error_str
                    })
                except Exception as inner_e:
                     self.logger.error(f"Error calling on_update at task failure: {inner_e}")

    def _record_task_failure(self, task: Dict[str, Any], reason: str):
        """
        Helper to mark a task as failed in the execution_history without fully attempting to run UI steps.
        """
        task_id = task.get("task_id", "unknown")
        outcome = {
            "task_id": task_id,
            "task_details": task,
            "response": f"[Execution Aborted: {reason}]",
            "success": False,
            "timestamp": datetime.now().isoformat()
        }
        self.execution_history.append(outcome)
        if self._on_update:
            try:
                self._on_update({
                    "event_type": "task_failed",
                    "task_id": task_id,
                    "error": reason
                })
            except Exception as e:
                self.logger.error(f"Error emitting task_failed: {e}", exc_info=True)

    def _capture_response_from_clipboard(self) -> str:
        """
        Attempt to read from the clipboard as the AI's final response text.
        """
        if self.dry_run:
            self.logger.info("(Dry-run) Simulating response capture from clipboard.")
            return "[Simulated DRY-RUN Response]"
        try:
            content = pyperclip.paste()
            if not content:
                self.logger.warning("Clipboard was empty after final wait.")
                return "[No content captured from clipboard]"
            return content
        except Exception as e:
            self.logger.error(f"Clipboard error: {e}")
            return f"[Clipboard error: {e}]"

    def _handle_test_generation(self, task: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Check the task for test generation or coverage analysis flags and run them if configured.
        Returns:
            (generated_test_skeleton, test_coverage_report)
        """
        if not self.test_generator_service:
            # If the user wants tests but there's no service, just warn.
            if task.get("generate_tests") or task.get("mode") in ["tdd", "coverage_driven", "test"]:
                self.logger.warning("TestGeneratorService not available; skipping test generation.")
            return (None, None)

        file_path = task.get("file_path")
        mode = task.get("mode", "post_implementation")
        should_generate_tests = (task.get("generate_tests") or mode in ["tdd", "coverage_driven", "test"])
        has_test_feedback = "test_feedback" in task
        test_feedback = task.get("test_feedback", {})
        should_analyze_coverage = (task.get("analyze_coverage") or mode == "coverage_driven")

        generated_test = None
        coverage_report_data = None

        if file_path:
            self.logger.info(
                f"Test generation for {file_path}: "
                f"should_generate={should_generate_tests}, has_feedback={has_test_feedback}, coverage={should_analyze_coverage}, mode={mode}"
            )
            try:
                # If we have test feedback, we can do a regeneration
                if has_test_feedback and should_generate_tests:
                    result = self.test_generator_service.regenerate_tests_based_on_feedback(file_path, test_feedback)
                    if result:
                        generated_test = f"[Regenerated test file: {result}]"
                        task["generated_test_path"] = result
                        self.logger.info(f"Regenerated tests: {result}")
                    else:
                        generated_test = "[Test Regeneration Failed]"
                        self.logger.warning("Test regeneration returned no result.")
                elif should_generate_tests:
                    # Possibly coverage-driven
                    gen_mode = "coverage_driven" if should_analyze_coverage else mode
                    result = self.test_generator_service.generate_tests(file_path, mode=gen_mode)
                    if result:
                        generated_test = f"[Generated test file: {result}]"
                        task["generated_test_path"] = result
                        self.logger.info(f"Generated test skeleton: {result}")
                    else:
                        generated_test = "[Test Generation Failed]"
                        self.logger.warning("No test file returned from generation.")

                # Coverage analysis if requested
                if should_analyze_coverage and hasattr(self.test_generator_service, 'coverage_analyzer'):
                    coverage_report = self.test_generator_service.coverage_analyzer.get_coverage_report(file_path)
                    if coverage_report and "error" not in coverage_report:
                        coverage_report_data = coverage_report
                        coverage_percent = coverage_report.get("current_coverage", 0)
                        self.logger.info(f"Coverage analysis complete: {coverage_percent}% covered.")
                        # Check if there's a coverage trend analysis
                        if hasattr(self.test_generator_service, 'analyze_test_coverage_trend'):
                            trend = self.test_generator_service.analyze_test_coverage_trend(file_path)
                            coverage_report_data["trend"] = trend.get("trend", "unknown")
                            coverage_report_data["needs_improvement"] = trend.get("needs_improvement", False)
                        task["coverage_analysis"] = coverage_report_data
                    else:
                        err = coverage_report.get("error", "Unknown error") if coverage_report else "No data"
                        coverage_report_data = {"error": err}
                        self.logger.warning(f"Coverage analysis error: {err}")

            except Exception as e:
                self.logger.error(f"Test generation/analysis error for {file_path}: {e}", exc_info=True)
                if not generated_test:
                    generated_test = f"[Error: {e}]"
        else:
            if should_generate_tests:
                self.logger.warning(f"Cannot generate tests: missing file_path in task {task.get('task_id')}.")
        return (generated_test, coverage_report_data)

    # -------------------------------------
    # HELPER: SORTING THE TASK QUEUE
    # -------------------------------------
    def _sort_task_queue(self):
        """Sort tasks in the queue by priority (critical→high→medium→low) then FIFO by queued_at."""
        with self.task_queue.mutex:
            queue_list = list(self.task_queue.queue)
            queue_list.sort(key=lambda x: (
                self._priority_rank(x.get("priority", "medium")),
                x.get("queued_at", "")
            ))
            self.task_queue.queue.clear()
            for item in queue_list:
                self.task_queue.queue.append(item)

    def _priority_rank(self, priority: str) -> int:
        ranks = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return ranks.get(priority, 2)

    def _get_queue_snapshot(self) -> List[Dict[str, Any]]:
        """Return a shallow copy of tasks currently in the queue."""
        with self.task_queue.mutex:
            return [t.copy() for t in self.task_queue.queue]

    # -------------------------
    # UI INTERACTION HELPERS
    # -------------------------
    def _focus_cursor_window(self) -> bool:
        """Attempt to focus/activate the 'Cursor' window."""
        if self.dry_run:
            self.logger.info("(Dry-run) Would focus the Cursor window.")
            return True

        try:
            # Attempt exact title match first
            possible_windows = gw.getWindowsWithTitle(WINDOW_TITLE)
            if not possible_windows:
                # Fallback: search in all titles
                all_titles = gw.getAllTitles()
                matches = [title for title in all_titles if WINDOW_TITLE.lower() in title.lower()]
                if not matches:
                    self.logger.error(f"No window found containing '{WINDOW_TITLE}' in title.")
                    return False
                fallback_title = matches[0]
                possible_windows = gw.getWindowsWithTitle(fallback_title)
                if not possible_windows:
                    self.logger.error(f"Failed to retrieve window handle for fallback title '{fallback_title}'")
                    return False

            win = possible_windows[0]
            title_str = win.title

            if win.isMinimized:
                win.restore()
                time.sleep(0.5)
            win.activate()
            time.sleep(1.0)

            # Verify
            active_win = gw.getActiveWindow()
            if active_win and active_win.title == title_str:
                self.logger.info(f"Successfully focused window '{title_str}'.")
            else:
                self.logger.warning(f"Focused attempt on '{title_str}' but active window is different.")
            return True

        except Exception as e:
            self.logger.error(f"Cannot focus Cursor window: {e}", exc_info=True)
            return False

    def _click_coordinate(self, coords: Optional[Tuple[int, int]]):
        """Click on the given screen coords, unless in dry_run mode."""
        if coords is None:
            raise ValueError("No coordinates to click (coords=None).")

        if self.dry_run:
            self.logger.info(f"(Dry-run) Would click at {coords}.")
        else:
            try:
                pyautogui.moveTo(coords[0], coords[1], duration=0.25)
                pyautogui.click()
                self.logger.debug(f"Clicked at {coords}")
            except Exception as e:
                self.logger.error(f"Error clicking at {coords}: {e}")
                raise
        time.sleep(0.5)

    def _type_prompt_and_send(self, prompt: str):
        """
        Type (or paste) the prompt into the active window and press Enter.
        """
        if self.dry_run:
            self.logger.info(f"(Dry-run) Would paste and send: {prompt[:60]}...")
            return

        try:
            pyperclip.copy(prompt)
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.2)
            pyautogui.press("enter")
            self.logger.debug("Prompt pasted and Enter pressed.")
        except Exception as e:
            self.logger.error(f"Error typing prompt: {e}", exc_info=True)
            raise

    def _wait_for_response(self, timeout: int) -> bool:
        """
        Wait up to 'timeout' seconds for ACCEPT_IMAGE to appear on screen.
        If found, update self.accept_button_coords to the center of the located region.
        """
        if self.dry_run:
            self.logger.info("(Dry-run) Simulating Accept button detection.")
            time.sleep(random.uniform(1, 2))
            self.accept_button_coords = (
                DEFAULT_ACCEPT_BUTTON_COORDS[0] + random.randint(-5, 5),
                DEFAULT_ACCEPT_BUTTON_COORDS[1] + random.randint(-5, 5)
            )
            return True

        accept_img_path = os.path.abspath(ACCEPT_IMAGE)
        if not os.path.exists(accept_img_path):
            self.logger.error(f"Accept button image not found at {accept_img_path}. Using fallback coords.")
            return False

        self.logger.info(f"Waiting for Accept button (image={accept_img_path}), timeout={timeout}s")
        start = time.time()
        conf = 0.9
        found = False

        while time.time() - start < timeout:
            try:
                loc = pyautogui.locateOnScreen(accept_img_path, confidence=conf)
                if loc:
                    center_x = loc.left + loc.width // 2
                    center_y = loc.top + loc.height // 2
                    self.accept_button_coords = (center_x, center_y)
                    self.logger.info(f"Found Accept button at {self.accept_button_coords} (conf={conf})")
                    found = True
                    break
            except Exception as e:
                self.logger.warning(f"Error while locating Accept image: {e}")

            time.sleep(POLL_INTERVAL)
            # Possibly lower confidence if we're near the end
            if not found and time.time() - start > (timeout * 0.75) and conf > 0.8:
                conf = 0.8
                self.logger.info("Lowering confidence to 0.8 to locate Accept button.")

        if not found:
            self.logger.warning("Timeout locating Accept button. Using fallback coords.")
        return found

    # ---------------
    # SHUTDOWN
    # ---------------
    def shutdown(self):
        """Stop background loop and clean up if necessary."""
        self.logger.info("Shutting down CursorSessionManager...")
        self.stop_loop()
        self.logger.info("Shutdown complete.")

    # -------------------------
    # LIFECYCLE HOOKS SETUP
    # -------------------------
    def _configure_default_hooks(self):
        """
        Configure some default hooks if the PromptLifecycleHooksService is available.
        """
        if not self.lifecycle_hooks:
            self.logger.error("No lifecycle_hooks to configure.")
            return

        try:
            from core.services.PromptLifecycleHooksService import (
                basic_validation_hook,
                priority_normalization_hook,
                sanitize_prompt_hook
            )

            # queue stage
            self.lifecycle_hooks.register_queue_hook(sanitize_prompt_hook)
            self.lifecycle_hooks.register_queue_hook(priority_normalization_hook)

            # validate stage
            self.lifecycle_hooks.register_validate_hook(basic_validation_hook)

            # inject stage (example)
            self.lifecycle_hooks.register_inject_hook(self._inject_automatic_context_hook_wrapper)

            # simple approve
            def simple_approval_hook(task):
                # always approve
                return task
            self.lifecycle_hooks.register_approve_hook(simple_approval_hook)

            # simple dispatch
            def simple_dispatch_hook(task):
                return task
            self.lifecycle_hooks.register_dispatch_hook(simple_dispatch_hook)

            self.logger.info("Default lifecycle hooks configured successfully.")

        except ImportError as e:
            self.logger.warning(f"Cannot import default hooks from PromptLifecycleHooksService: {e}")
        except Exception as e:
            self.logger.error(f"Error configuring default hooks: {e}", exc_info=True)

    def _inject_automatic_context_hook_wrapper(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        A lifecycle inject-stage hook that calls internal context injection logic.
        Return None if injection fails, else updated task.
        """
        try:
            self._inject_automatic_context(task)
            return task
        except Exception as e:
            self.logger.error(f"Error injecting automatic context for {task.get('task_id','unknown')}: {e}", exc_info=True)
            return None

    def _inject_automatic_context(self, task_data: Dict[str, Any]):
        """
        Gathers system context (state_manager, memory_manager, file snippet) and merges
        it into task_data['context']. Also sets task_data['formatted_prompt'].
        """
        prompt_text = task_data.get("prompt", "")
        auto_context = {}

        # Possibly pull from state_manager
        if self.state_manager and hasattr(self.state_manager, 'get_current_file_path'):
            try:
                current_file = self.state_manager.get_current_file_path()
                if current_file:
                    auto_context["current_file"] = str(current_file)
            except Exception as e:
                self.logger.warning(f"Failed to get state context: {e}")

        # Possibly pull from memory_manager
        if self.memory_manager and hasattr(self.memory_manager, 'get_snapshot'):
            try:
                snapshot = self.memory_manager.get_snapshot(topic=prompt_text)
                if snapshot:
                    auto_context["thea_memory_snapshot"] = snapshot
            except Exception as e:
                self.logger.warning(f"Failed to get memory snapshot: {e}")

        # Possibly read partial file content
        file_path = task_data.get("file_path")
        if file_path and self.path_manager and hasattr(self.path_manager, 'resolve_path'):
            try:
                full_path = self.path_manager.resolve_path(file_path)
                if full_path and full_path.is_file():
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        snippet = f.read(5000)
                        auto_context["target_file_content_snippet"] = snippet
            except Exception as e:
                self.logger.warning(f"Failed reading file snippet: {e}")

        # Merge auto_context with existing
        context_dict = task_data.setdefault("context", {})
        for k, v in auto_context.items():
            context_dict[f"auto_{k}"] = v

        # Format final prompt with context appended
        formatted_prompt = self._format_prompt_with_context(prompt_text, context_dict)
        task_data["formatted_prompt"] = formatted_prompt

    def _format_prompt_with_context(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Return prompt + JSON-serialized context appended. If context is empty, just return prompt.
        """
        if not context:
            return prompt
        try:
            cjson = json.dumps(context, indent=2, default=str)
            return f"{prompt}\n\n# CONTEXT:\n{cjson}"
        except Exception as e:
            self.logger.warning(f"Failed to serialize context: {e}")
            return f"{prompt}\n\n# CONTEXT: (Error formatting context)"

    # --------------
    # DEMO FUNCTION
    # --------------
    def _demo(self):
        """
        Demonstration usage of the merged CursorSessionManager.
        Shows adding tasks, manually accepting them, toggling auto-accept, and overnight mode.
        """

        self.logger.info("=== DEMO START ===")

        def demo_callback(event_data: Dict[str, Any]):
            evt = event_data.get("event_type", "unknown")
            tid = event_data.get("task_id", "")
            if evt == "task_completed":
                snippet = event_data.get("response_snippet", "")
                self.logger.info(f"[DEMO CALLBACK] Task {tid} completed. Response snippet: {snippet}")
            elif evt == "task_failed":
                err = event_data.get("error", "No error info")
                self.logger.info(f"[DEMO CALLBACK] Task {tid} failed. Error: {err}")
            else:
                self.logger.info(f"[DEMO CALLBACK] Event='{evt}', Data={event_data}")

        self.set_on_update_callback(demo_callback)
        self.toggle_auto_accept(False)
        self.start_loop()

        # Queue some tasks
        t1 = self.queue_task({
            "prompt": "Test prompt #1 (with lifecycle hooks, high priority)",
            "context": {"foo": "bar"},
            "priority": "high",
            "mode": "test",
            "generate_tests": True
        })
        t2 = self.queue_task("Simple string prompt #2 (medium priority)")

        time.sleep(2)
        self.logger.info("Manually accept first task...")
        self.accept_next_task()

        time.sleep(3)
        self.logger.info("Manually accept second task...")
        self.accept_next_task()

        # Auto-accept example
        self.toggle_auto_accept(True)
        self.queue_task({"prompt": "Auto-accept prompt #3", "priority": "low"})
        time.sleep(5)

        # Overnight/batch mode
        self.toggle_auto_accept(False)
        self.logger.info("Running overnight mode for a direct batch of 2 prompts...")
        self.run_overnight_mode([
            "Overnight prompt #1: refactor code",
            {
                "prompt": "Overnight prompt #2: run coverage",
                "file_path": "core/CursorSessionManager.py",
                "mode": "coverage_driven"
            }
        ])

        time.sleep(2)
        self.shutdown()

        self.logger.info(f"Total execution history entries: {len(self.execution_history)}")
        success_count = sum(1 for x in self.execution_history if x.get("success"))
        fail_count = len(self.execution_history) - success_count
        self.logger.info(f"DEMO complete. Success={success_count}, Fail={fail_count}")

        self.logger.info("=== DEMO END ===")


def _demo():
    """
    Optional standalone demo if you run this script directly.
    """
    if DRY_RUN:
        logger.info("Running CursorSessionManager in DRY-RUN mode (no real UI).")
    else:
        logger.info("Running CursorSessionManager in LIVE UI mode.")

    mgr = CursorSessionManager(dry_run=DRY_RUN)
    mgr._demo()

if __name__ == "__main__":
    if DRY_RUN:
        logger.info("Running CursorSessionManager demo in DRY-RUN mode.")
    else:
        logger.info("Running CursorSessionManager demo in LIVE mode (will interact with UI).")
        print("------------------------------------------------------------")
        print("--- STARTING LIVE DEMO in 5 seconds... ---")
        print("--- Ensure the 'Cursor' window is visible and accessible ---")
        print("--- Press Ctrl+C in this terminal to cancel ---")
        print("------------------------------------------------------------")
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nDemo cancelled by user.")
            sys.exit(0)

    _demo()
