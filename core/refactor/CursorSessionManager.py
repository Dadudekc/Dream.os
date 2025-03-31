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
from typing import Any, Dict, List, Optional, Callable, Tuple
from datetime import datetime
from queue import Queue, Empty
import uuid # For generating unique task IDs
import random

# Add import for the lifecycle hooks
from core.services.PromptLifecycleHooksService import PromptLifecycleHooksService
from core.services.TestGeneratorService import TestGeneratorService

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
MAX_WAIT_TIME = 300
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

# Assume these exist or adjust imports as needed
# from core.PathManager import PathManager
# from core.MemoryManager import MemoryManager 
# from core.StateManager import StateManager
# from core.services.TestGeneratorService import TestGeneratorService

class CursorSessionManager:
    """
    Unified class that handles:
      1) UI calibration for Cursor (prompt box + accept button)
      2) Task queueing with auto/manual acceptance
      3) Batch prompt building (optional)
      4) Dynamic wait for 'Accept' detection
      5) Execution history of tasks
      6) Lifecycle hooks for task processing
    """

    # Define the DEFAULT_HOTKEYS dictionary as a class attribute
    DEFAULT_HOTKEYS = {
        "submit_prompt": "enter",
        "cancel_operation": "escape",
        "accept_suggestion": "tab"
    }

    def __init__(self, 
                 project_root: str = ".", 
                 dry_run: bool = DRY_RUN,
                 # Inject services needed for context
                 path_manager=None, # Instance of PathManager
                 memory_manager=None, # Instance of MemoryManager
                 state_manager=None, # Instance of a state manager holding UI/system state
                 test_generator_service=None, # Added TestGeneratorService
                 lifecycle_hooks_service=None, # Added PromptLifecycleHooksService
                 service_registry=None # Alternative: get services from registry
                ):
        """
        Args:
            project_root (str): Directory for launching Cursor (if you do so).
            dry_run (bool): If True, simulates all actions, no real UI interaction.
            path_manager: Service for path lookups.
            memory_manager: Service for accessing Thea's memory.
            state_manager: Service for accessing current UI/system state.
            test_generator_service: Service for generating test skeletons.
            lifecycle_hooks_service: Service for prompt lifecycle hooks.
            service_registry: Optional registry to retrieve services.
        """
        self.project_root = project_root
        self.dry_run = dry_run
        self.logger = logger

        # --- Service Injection ---
        # Prioritize direct injection, fallback to registry if provided
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
            
            # Optionally log if services are still missing
            if not self.path_manager: self.logger.warning("PathManager service not available.")
            if not self.memory_manager: self.logger.warning("MemoryManager service not available.")
            if not self.state_manager: self.logger.warning("StateManager service not available.")
            if not self.test_generator_service: self.logger.warning("TestGeneratorService not available.")
            if not self.lifecycle_hooks: self.logger.warning("PromptLifecycleHooksService not available.")
        
        # Create a lifecycle hooks service if not provided
        if not self.lifecycle_hooks:
            self.lifecycle_hooks = PromptLifecycleHooksService(logger=self.logger)
            self._configure_default_hooks()  # Configure with default hooks

        # --- Core Attributes ---
        self.auto_accept = False
        self.task_queue = Queue()
        self.execution_history: List[Dict[str, Any]] = []
        self._active = False
        self._thread = threading.Thread(target=self._task_loop, daemon=True)
        self.prompt_box_coords: Optional[tuple] = None
        self.accept_button_coords: Optional[tuple] = None
        self._load_or_calibrate_coords()
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
    def queue_task(self, prompt_or_dict):
        """
        Queue a task for execution. Takes either a string prompt or a dictionary with task metadata.
        If a string is provided, it is converted to a task dictionary with a uniquely generated ID.
        
        Args:
            prompt_or_dict: Either a string prompt or a dictionary containing at least a 'prompt' key
            
        Returns:
            str: The task_id of the queued task
        """
        try:
            # Generate a random task ID with timestamp for uniqueness
            task_id = f"task_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
            
            # Handle string prompts by converting to a dictionary
            if isinstance(prompt_or_dict, str):
                task_dict = {
                    "task_id": task_id,
                    "prompt": prompt_or_dict,
                    "queued_at": datetime.now().isoformat(),
                    "status": "queued",
                    "priority": "medium"  # Default priority
                }
            else:
                # Ensure the dictionary has all required fields
                task_dict = prompt_or_dict.copy()  # Create a copy to avoid modifying the original
                
                # Required fields
                if "prompt" not in task_dict:
                    self.logger.error("Task data must include a 'prompt' key. Task rejected.")
                    return None
                    
                task_dict["task_id"] = task_id
                task_dict["queued_at"] = datetime.now().isoformat()
                task_dict["status"] = "queued"
                
                # Set default priority if not provided
                if "priority" not in task_dict:
                    task_dict["priority"] = "medium"
            
            # Process through on_queue lifecycle stage if available
            try:
                if self.lifecycle_hooks:
                    queued_task = self.lifecycle_hooks.process_on_queue(task_dict)
                    if queued_task is None:
                        self.logger.warning(f"Task {task_id} rejected during on_queue lifecycle stage")
                        
                        # Notify UI of rejection if callback is registered
                        if self._on_update:
                            self._on_update({
                                "event_type": "task_rejected",
                                "task_id": task_id,
                                "reason": "Rejected by queue lifecycle hooks"
                            })
                        return None
                    
                    # Use the processed task
                    task_dict = queued_task
            except Exception as e:
                self.logger.error(f"Error in queue_task lifecycle processing: {e}")
                # Continue with original task if lifecycle processing fails
                
            # Add the task to the queue
            self.task_queue.put(task_dict)
            
            # Sort the queue by priority and then by time queued (FIFO within priority levels)
            self._sort_task_queue()
            
            # Emit a queue_changed update
            if self._on_update:
                try:
                    self._on_update({
                        "event_type": "queue_changed",
                        "queue_snapshot": self._get_queue_snapshot()
                    })
                except Exception as e:
                    self.logger.error(f"Error emitting queue_changed update: {e}")
            
            self.logger.info(f"Task {task_id} queued. Queue length is now {self.task_queue.qsize()}.")
            return task_id
            
        except Exception as e:
            self.logger.error(f"Error queueing task: {e}")
            raise

    def cancel_task(self, task_id):
        """
        Cancel a queued task by ID.
        
        Args:
            task_id: The ID of the task to cancel
            
        Returns:
            bool: True if the task was found and cancelled, False otherwise
        """
        try:
            for i, task in enumerate(self.task_queue):
                if task.get("task_id") == task_id:
                    # Found the task, remove it
                    cancelled_task = self.task_queue.get(i)
                    
                    # Emit task cancelled update
                    if self._on_update:
                        try:
                            self._on_update({
                                "event_type": "task_cancelled",
                                "task_id": task_id,
                                "task_prompt": cancelled_task.get("prompt", "")[:50] + "..." if cancelled_task.get("prompt") else ""
                            })
                            
                            # Also emit a queue changed update
                            self._on_update({
                                "event_type": "queue_changed",
                                "queue_snapshot": self._get_queue_snapshot()
                            })
                        except Exception as e:
                            self.logger.error(f"Error emitting task cancelled update: {e}")
                    
                    self.logger.info(f"Task {task_id} cancelled. Queue length is now {self.task_queue.qsize()}.")
                    return True
            
            # Task not found
            self.logger.warning(f"Task {task_id} not found for cancellation.")
            return False
            
        except Exception as e:
            self.logger.error(f"Error cancelling task {task_id}: {e}")
            return False
            
    def update_task_priority(self, task_id, new_priority):
        """
        Update the priority of a queued task.
        
        Args:
            task_id: The ID of the task to update
            new_priority: The new priority level ('low', 'medium', 'high', or 'critical')
            
        Returns:
            bool: True if the task was found and updated, False otherwise
        """
        if new_priority not in ["low", "medium", "high", "critical"]:
            self.logger.warning(f"Invalid priority {new_priority}. Must be one of: low, medium, high, critical")
            return False
            
        try:
            for task in self.task_queue:
                if task.get("task_id") == task_id:
                    # Found the task, update priority
                    old_priority = task.get("priority", "medium")
                    task["priority"] = new_priority
                    
                    # Resort the queue
                    self._sort_task_queue()
                    
                    # Emit task updated update
                    if self._on_update:
                        try:
                            self._on_update({
                                "event_type": "task_updated",
                                "task_id": task_id,
                                "field": "priority",
                                "old_value": old_priority,
                                "new_value": new_priority
                            })
                            
                            # Also emit a queue changed update
                            self._on_update({
                                "event_type": "queue_changed",
                                "queue_snapshot": self._get_queue_snapshot()
                            })
                        except Exception as e:
                            self.logger.error(f"Error emitting task updated update: {e}")
                    
                    self.logger.info(f"Task {task_id} priority updated from {old_priority} to {new_priority}.")
                    return True
            
            # Task not found
            self.logger.warning(f"Task {task_id} not found for priority update.")
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating task {task_id} priority: {e}")
            return False
            
    def _sort_task_queue(self):
        """
        Sort the task queue by priority and then by queue time.
        Priority order (highest to lowest): critical, high, medium, low
        Within each priority level, tasks are ordered by queue time (FIFO)
        """
        # Define priority ranks
        priority_ranks = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3
        }
        
        # Sort the queue
        self.task_queue.sort(key=lambda task: (
            priority_ranks.get(task.get("priority", "medium"), 2),  # Sort by priority rank
            task.get("queued_at", "")  # Then by queue time
        ))
        
    def _get_queue_snapshot(self):
        """
        Get a snapshot of the current task queue for UI display.
        Returns a list of task dictionaries.
        """
        return [task.copy() for task in self.task_queue]

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
        Manually accept & execute the next queued task.
        The task will go through the validation, approval and dispatch 
        lifecycle stages before execution.
        """
        try:
            task = self.task_queue.get_nowait() # Task is now a dict
            task["accepted"] = True
            task["status"] = "processing"
            
            if self._on_update:
                try:
                    # Emit queue change *before* execution starts
                    self._on_update({
                        "event_type": "queue_changed",
                        "queue_snapshot": self._get_queue_snapshot()
                    })
                except Exception as e:
                    self.logger.error(f"Error calling on_update before executing task: {e}")

            # Process through the complete lifecycle if we have the service
            if self.lifecycle_hooks:
                try:
                    processed_task, messages = self.lifecycle_hooks.process_lifecycle(task)
                    
                    # Log the lifecycle processing messages
                    for msg in messages:
                        self.logger.debug(f"Lifecycle: {msg}")
                        
                    # Check if the task was rejected at any stage
                    if processed_task is None:
                        self.logger.warning(f"Task {task.get('task_id', 'unknown')} rejected during lifecycle processing")
                        if self._on_update:
                            self._on_update({
                                "event_type": "task_rejected",
                                "task_id": task.get('task_id', 'unknown'),
                                "reason": "Rejected during lifecycle processing"
                            })
                        return
                        
                    # Use the processed task for execution
                    task = processed_task
                except Exception as e:
                    self.logger.error(f"Error in lifecycle processing: {e}")
                    # Continue with original task if lifecycle processing fails

            self._execute_task(task) # Pass the full task dict

        except Empty:
            self.logger.warning("No tasks to accept.")
            if self._on_update:
                try:
                    self._on_update({"event_type": "queue_empty"})
                except Exception as e:
                    self.logger.error(f"Error calling on_update on empty queue: {e}")

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
                task = self.task_queue.get(timeout=1) # Task is a dict
                if self.auto_accept:
                    task["accepted"] = True
                    task["status"] = "processing"
                    if self._on_update:
                        try:
                             # Emit queue change *before* execution starts
                            self._on_update({
                                "event_type": "queue_changed",
                                "queue_snapshot": self._get_queue_snapshot()
                             })
                        except Exception as e:
                            self.logger.error(f"Error calling on_update before auto-executing task: {e}")
                    
                    # Process through the complete lifecycle if we have the service
                    if self.lifecycle_hooks:
                        try:
                            processed_task, messages = self.lifecycle_hooks.process_lifecycle(task)
                            
                            # Log the lifecycle processing messages
                            for msg in messages:
                                self.logger.debug(f"Lifecycle: {msg}")
                                
                            # Check if the task was rejected at any stage
                            if processed_task is None:
                                self.logger.warning(f"Task {task.get('task_id', 'unknown')} rejected during lifecycle processing")
                                if self._on_update:
                                    self._on_update({
                                        "event_type": "task_rejected",
                                        "task_id": task.get('task_id', 'unknown'),
                                        "reason": "Rejected during lifecycle processing"
                                    })
                                continue  # Skip to next task
                                
                            # Use the processed task for execution
                            task = processed_task
                        except Exception as e:
                            self.logger.error(f"Error in lifecycle processing: {e}")
                            # Continue with original task if lifecycle processing fails
                    
                    self._execute_task(task) # Pass full task dict
                else:
                    # Task remains in queue until manually accepted
                    if self._on_update:
                         try:
                             self._on_update({
                                 "event_type": "task_pending",
                                 "task_id": task.get("task_id"), # Use ID
                                 "task_prompt": task.get("prompt", "<No Prompt>")[:50] + "..."
                              })
                         except Exception as e:
                             self.logger.error(f"Error calling on_update for pending task: {e}")
            except Empty:
                continue
        self.logger.info("CursorSessionManager loop exited.")

    # ---------------
    # EXECUTION LOGIC
    # ---------------
    def _execute_task(self, task: Dict[str, Any]):
        task_id = task.get("task_id", "unknown_task")
        prompt_text = task.get("prompt", "")
        context = task.get("context", {}) # Get context from task if provided

        if not prompt_text:
             self.logger.error(f"Task {task_id} has no prompt. Aborting.")
             if self._on_update:
                 self._on_update({"event_type": "task_failed", "task_id": task_id, "error": "Missing prompt"})
             return

        if self._on_update:
            try:
                self._on_update({
                    "event_type": "task_started",
                    "task_id": task_id,
                    "task_prompt": prompt_text[:50] + "..."
                })
            except Exception as e:
                 self.logger.error(f"Error calling on_update at task start: {e}")

        generated_test_skeleton = None # Variable to hold generated test
        test_coverage_report = None    # Variable to hold test coverage report

        try:
            # --- Process through remaining lifecycle stages ---
            # 1. First, validate the task
            if self.lifecycle_hooks:
                task = self.lifecycle_hooks.process_on_validate(task)
                if task is None:
                    raise ValueError("Task rejected during validation stage")
                
                # Get updated values after validation
                prompt_text = task.get("prompt", "")
                context = task.get("context", {})
            
            # 2. Inject automatic context
            try:
                if self.lifecycle_hooks:
                    # Process through inject stage
                    task = self.lifecycle_hooks.process_on_inject(task)
                    if task is None:
                        raise ValueError("Task rejected during inject stage")
                    
                    # Get the updated values
                    prompt_text = task.get("prompt", "")
                    context = task.get("context", {})
                else:
                    # Legacy context injection if no lifecycle hooks
                    final_prompt = self._inject_automatic_context(prompt_text, task)
            except Exception as context_err:
                self.logger.error(f"Error in context injection stage for task {task_id}: {context_err}")
                # Fallback to legacy method if lifecycle hooks fail
                final_prompt = self._inject_context(prompt_text, context)
            
            # 3. Approval stage
            if self.lifecycle_hooks:
                task = self.lifecycle_hooks.process_on_approve(task)
                if task is None:
                    raise ValueError("Task rejected during approval stage")
                
                # Refresh values after approval
                prompt_text = task.get("prompt", "")
                
                # Get the final prompt text (which may include context from previous stages)
                if "formatted_prompt" in task:
                    final_prompt = task["formatted_prompt"]
                else:
                    # Build it ourselves if not provided by hooks
                    final_prompt = prompt_text
            else:
                # Use what we have if no lifecycle hooks
                final_prompt = prompt_text
                
            # 4. Dispatch stage
            if self.lifecycle_hooks:
                task = self.lifecycle_hooks.process_on_dispatch(task)
                if task is None:
                    raise ValueError("Task rejected during dispatch stage")
                
                # Final refresh of values if needed
                if "formatted_prompt" in task:
                    final_prompt = task["formatted_prompt"]
            
            # --- Execute the prompt ---
            start_ts = time.time()

            if not self._focus_cursor_window():
                raise RuntimeError("Cannot focus Cursor window")

            self._click_coordinate(self.prompt_box_coords)
            prompt_summary = final_prompt[:75].replace("\\n", "\\\\n") # Use final_prompt
            self.logger.info(f"Typing prompt for task {task_id}: {prompt_summary}...")
            self._type_prompt_and_send(final_prompt) # Use final_prompt

            if self._wait_for_response(MAX_WAIT_TIME):
                self.logger.info("Clicking detected Accept button...")
                self._click_coordinate(self.accept_button_coords)
            else:
                fallback = 30
                self.logger.warning(f"Dynamic wait timed out. Using fallback {fallback} seconds.")
                time.sleep(fallback)
                self._click_coordinate(self.accept_button_coords)

            end_ts = time.time()
            # TODO: Replace simulation with actual response capture mechanism
            simulated_response = f"[Simulated Response for Task {task_id}] TimeSpent={round(end_ts - start_ts,1)}s"

            # --- Test Generation Strategy Logic (Enhanced) ---
            # Determine the appropriate test generation mode
            target_file_path = task.get("file_path")
            generation_mode = task.get("mode", "post_implementation")
            
            # Check explicit flags for test generation
            should_generate_tests = (
                task.get("generate_tests", False) or 
                generation_mode in ["tdd", "coverage_driven", "test"]
            )
            
            # Check if we have feedback data for regeneration
            has_test_feedback = "test_feedback" in task
            test_feedback = task.get("test_feedback", {})
            
            # Coverage analysis
            should_analyze_coverage = (
                task.get("analyze_coverage", False) or
                generation_mode == "coverage_driven"
            )
            
            if target_file_path and self.test_generator_service:
                self.logger.info(f"Test generation strategy for {target_file_path}: "
                                f"mode={generation_mode}, generate={should_generate_tests}, "
                                f"has_feedback={has_test_feedback}, analyze_coverage={should_analyze_coverage}")
                
                try:
                    if has_test_feedback and should_generate_tests:
                        # Regenerate tests based on feedback
                        self.logger.info(f"Regenerating tests for {target_file_path} based on feedback")
                        generated_test_skeleton = self.test_generator_service.regenerate_tests_based_on_feedback(
                            target_file_path, test_feedback
                        )
                        if generated_test_skeleton:
                            self.logger.info(f"✅ Successfully regenerated tests for {target_file_path} based on feedback")
                            task["generated_test_path"] = f"test_{target_file_path}"
                        else:
                            self.logger.warning(f"Failed to regenerate tests for {target_file_path}")
                    
                    elif should_generate_tests:
                        # Generate tests with the appropriate mode
                        test_mode = "coverage_driven" if should_analyze_coverage else generation_mode
                        self.logger.info(f"Generating tests for {target_file_path} with mode {test_mode}")
                        generated_test_skeleton = self.test_generator_service.generate_tests(
                            target_file_path, mode=test_mode
                        )
                        if generated_test_skeleton:
                            self.logger.info(f"✅ Successfully generated test skeleton for {target_file_path}")
                            task["generated_test_path"] = f"test_{target_file_path}"
                        else:
                            self.logger.warning(f"TestGeneratorService ran but returned no skeleton for {target_file_path}")
                            
                    # Analyze coverage if requested, even if not generating tests
                    if should_analyze_coverage and hasattr(self.test_generator_service, 'coverage_analyzer'):
                        self.logger.info(f"Analyzing test coverage for {target_file_path}")
                        coverage_report = self.test_generator_service.coverage_analyzer.get_coverage_report(target_file_path)
                        
                        if "error" not in coverage_report:
                            test_coverage_report = coverage_report
                            self.logger.info(f"✅ Coverage analysis complete: {coverage_report.get('current_coverage')}% covered")
                            
                            # Add coverage trend analysis to task metadata
                            trend_analysis = self.test_generator_service.analyze_test_coverage_trend(target_file_path)
                            task["coverage_analysis"] = {
                                "percentage": coverage_report.get("current_coverage", 0),
                                "trend": coverage_report.get("trend", "unknown"),
                                "uncovered_functions_count": len(coverage_report.get("uncovered_functions", [])),
                                "needs_improvement": trend_analysis.get("needs_improvement", False)
                            }
                        else:
                            self.logger.warning(f"Coverage analysis failed: {coverage_report.get('error')}")
                except Exception as test_gen_err:
                    self.logger.error(f"❌ Error during test generation/analysis for {target_file_path}: {test_gen_err}")
            elif should_generate_tests and not target_file_path:
                 self.logger.warning(f"Cannot generate tests for task {task_id}: missing 'file_path'")
            elif should_generate_tests:
                 self.logger.warning(f"Cannot generate tests for task {task_id}: TestGeneratorService not available")

            # Store outcome
            outcome = {
                "task_id": task_id,
                "task_details": task,
                "response": simulated_response,
                "generated_test_skeleton": generated_test_skeleton, # Include skeleton in history
                "test_coverage_report": test_coverage_report, # Include coverage report
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            self.execution_history.append(outcome)
            
            # Emit task completed event
            if self._on_update:
                try:
                    completion_payload = {
                        "event_type": "task_completed",
                        "task_id": task_id,
                        "task_prompt": prompt_text[:50] + "...",
                        "response": simulated_response,
                        "generated_test_path": task.get("generated_test_path"),
                        "coverage_analysis": task.get("coverage_analysis") # Include coverage analysis
                    }
                    self._on_update(completion_payload)
                except Exception as e:
                    self.logger.error(f"Error calling on_update at task completion: {e}")

            self.logger.info(f"Task {task_id} executed successfully. Elapsed={round(end_ts - start_ts,2)}s")

        except Exception as e:
            error_str = str(e)
            self.logger.error(f"Failed to execute task {task_id}: {error_str}")
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

    # ---------------
    # HELPER METHODS
    # ---------------
    def _get_queue_snapshot(self) -> List[Dict[str, Any]]:
        """Return a list of task dictionaries currently in the queue."""
        # Provides a shallow copy of the internal list
        with self.task_queue.mutex:
            return list(self.task_queue.queue)

    # Renamed to format context, used by _inject_automatic_context
    def _format_context_for_prompt(self, context_dict: Dict[str, Any], context_label: str) -> str:
        """Formats a dictionary of context into a string suitable for appending to a prompt."""
        if not context_dict:
            return ""
        try:
            # Simple JSON representation for now
            serialized = json.dumps(context_dict, indent=2, default=str) # Use default=str for non-serializable types
            return f"\n\n# {context_label}:\n{serialized}"
        except Exception as e:
            self.logger.warning(f"Could not serialize context for label '{context_label}': {e}")
            return f"\n\n# {context_label} (Serialization Error):\n{str(context_dict)}"

    # Updated injection method to only handle task-provided context formatting
    def _inject_context(self, prompt_text: str, task_context: Dict[str, Any]) -> str:
        """Formats and attaches context provided *with the task*."""
        context_str = self._format_context_for_prompt(task_context, "PROVIDED CONTEXT")
        return f"{prompt_text}{context_str}"

    # --- Updated Method for context injection --- 
    def _inject_automatic_context(self, prompt_text: str, task_data: Dict[str, Any]) -> str:
        """
        Gathers system state, merges with task context, and formats for the prompt.
        This is called directly from _execute_task when lifecycle hooks aren't available,
        or can be registered as a custom inject hook.
        """
        self.logger.debug(f"Injecting automatic context for task {task_data.get('task_id')}...")
        auto_context = {}
        
        # 1. Get UI/System State (Requires StateManager)
        if self.state_manager:
            try:
                current_file = self.state_manager.get_current_file_path() # Hypothetical method
                if current_file: auto_context["current_file"] = str(current_file)
                
                # Add other relevant state: active tab, recent errors, etc.
                # auto_context["active_aide_tab"] = self.state_manager.get_active_aide_tab()
                # auto_context["recent_errors"] = self.state_manager.get_recent_errors(limit=3)
                self.logger.debug(f"State context: {auto_context}")
            except Exception as e:
                self.logger.warning(f"Failed to get state context: {e}")
        else:
             self.logger.debug("StateManager not available, skipping state context.")

        # 2. Get Memory Snapshot (Requires MemoryManager)
        if self.memory_manager:
            try:
                # Assuming memory manager has a method to get a relevant snapshot
                memory_snapshot = self.memory_manager.get_snapshot(topic=task_data.get("prompt")) 
                if memory_snapshot: auto_context["thea_memory_snapshot"] = memory_snapshot
                self.logger.debug("Retrieved memory snapshot.")
            except Exception as e:
                self.logger.warning(f"Failed to get memory snapshot: {e}")
        else:
            self.logger.debug("MemoryManager not available, skipping memory snapshot.")

        # 3. Get File Content if file_path is specified in task (Requires PathManager)
        task_file_path_str = task_data.get("file_path")
        if task_file_path_str and self.path_manager:
            try:
                # Use PathManager to resolve relative to project root if needed
                full_path = self.path_manager.resolve_path(task_file_path_str) 
                if full_path and full_path.is_file():
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                         # Limit context size if necessary
                        content = f.read(5000) # Read first 5k chars
                        auto_context["target_file_content_snippet"] = content
                        self.logger.debug(f"Added content snippet for {task_file_path_str}")
                else:
                    self.logger.warning(f"Target file path in task not found or invalid: {task_file_path_str}")
            except Exception as e:
                self.logger.warning(f"Failed to read target file content: {e}")
        elif task_file_path_str:
             self.logger.debug("PathManager not available, skipping target file content.")

        # 4. Add the automatic context to the task if we're using the hook-based approach
        if self.lifecycle_hooks and isinstance(task_data, dict):
            # If this is being called as part of a lifecycle hook, update the context directly
            task_context = task_data.get("context", {})
            for key, value in auto_context.items():
                task_context[f"auto_{key}"] = value
            
            task_data["context"] = task_context
            task_data["formatted_prompt"] = self._format_prompt_with_context(prompt_text, task_context)
            return task_data["formatted_prompt"]
            
        # 5. Combine automatic context with task-provided context for direct usage
        provided_context = task_data.get("context", {}) if isinstance(task_data, dict) else {}
        
        # Format and append contexts for legacy approach
        final_prompt = prompt_text
        final_prompt += self._format_context_for_prompt(auto_context, "AUTOMATIC CONTEXT (System State)")
        final_prompt += self._format_context_for_prompt(provided_context, "PROVIDED CONTEXT (Task Specific)")
        
        self.logger.debug("Finished assembling final prompt with context.")
        return final_prompt

    # New helper method for formatting prompt with context
    def _format_prompt_with_context(self, prompt_text: str, context: Dict[str, Any]) -> str:
        """Format a prompt with context in a standardized way."""
        if not context:
            return prompt_text
            
        try:
            # Format context as JSON
            context_json = json.dumps(context, indent=2, default=str)
            return f"{prompt_text}\n\n# CONTEXT:\n{context_json}"
        except Exception as e:
            self.logger.warning(f"Error formatting context for prompt: {e}")
            return f"{prompt_text}\n\n# CONTEXT: (Error formatting context)"

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

    # Add this method after __init__
    def _configure_default_hooks(self):
        """Configure default lifecycle hooks for task processing."""
        try:
            from core.services.PromptLifecycleHooksService import (
                basic_validation_hook, 
                priority_normalization_hook,
                sanitize_prompt_hook
            )
            
            # Queue stage hooks
            self.lifecycle_hooks.register_queue_hook(sanitize_prompt_hook)
            self.lifecycle_hooks.register_queue_hook(priority_normalization_hook)
            
            # Validation stage hooks
            self.lifecycle_hooks.register_validate_hook(basic_validation_hook)
            
            # Register custom hooks for specific requirements
            self.lifecycle_hooks.register_inject_hook(self._custom_context_injection_hook)
            
            self.logger.info("Default prompt lifecycle hooks configured")
        except Exception as e:
            self.logger.error(f"Failed to configure default hooks: {e}")

    def _custom_context_injection_hook(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Example custom hook to inject context into a task."""
        # This is just a simple implementation; in a real scenario, 
        # this would add meaningful context from the system state
        if "context" not in task:
            task["context"] = {}
            
        # Add timestamp to context
        task["context"]["injection_timestamp"] = datetime.now().isoformat()
        
        # Add current file path if available from state manager
        if self.state_manager and hasattr(self.state_manager, 'get_current_file_path'):
            try:
                current_file = self.state_manager.get_current_file_path()
                if current_file:
                    task["context"]["current_file"] = str(current_file)
            except Exception as e:
                self.logger.warning(f"Error getting current file from state manager: {e}")
                
        return task

# -------------------------
# Test or Demo "main"
# -------------------------
def _demo():
    logging.basicConfig(level=logging.INFO)
    
    # Create services
    from core.services.TestGeneratorService import TestGeneratorService
    from core.services.PromptLifecycleHooksService import PromptLifecycleHooksService
    
    test_gen_service = TestGeneratorService(project_root=".", logger=logger)
    lifecycle_hooks = PromptLifecycleHooksService(logger=logger)
    
    # Register a custom hook for demo purposes
    def demo_validation_hook(task):
        """Demo validation hook that logs the task."""
        logger.info(f"Demo validation hook processing task: {task.get('task_id')}")
        
        # You could validate, modify, or reject the task here
        return task
        
    lifecycle_hooks.register_validate_hook(demo_validation_hook)
    
    # Create CursorSessionManager with services
    mgr = CursorSessionManager(
        project_root=".", 
        dry_run=DRY_RUN,
        test_generator_service=test_gen_service,
        lifecycle_hooks_service=lifecycle_hooks
    )

    # Example usage: start background loop, queue tasks
    mgr.toggle_auto_accept(False)  # Or True for immediate execution
    mgr.start_loop()

    # Queue tasks with rich metadata
    mgr.queue_task({
        "prompt": "Test prompt #1 with lifecycle hooks",
        "context": {"foo": "bar"},
        "priority": "high",
        "source": "demo",
        "mode": "tdd",
        "generate_tests": True
    })
    
    mgr.queue_task({
        "prompt": "Test prompt #2 with lifecycle hooks",
        "context": {"baz": 123},
        "priority": "medium",
        "source": "demo"
    })
    
    # Now we can either accept them manually:
    time.sleep(2)
    logger.info("Accepting first task...")
    mgr.accept_next_task()  # accept #1
    time.sleep(2)
    logger.info("Accepting second task...")
    mgr.accept_next_task()  # accept #2

    # Or if auto_accept was True, they'd run automatically
    time.sleep(5)
    
    # Check lifecycle stats
    if mgr.lifecycle_hooks:
        stats = mgr.lifecycle_hooks.get_stats()
        logger.info(f"Lifecycle hook stats: {stats}")
    
    mgr.shutdown()
    logger.info(f"History entries: {len(mgr.execution_history)}")

if __name__ == "__main__":
    if DRY_RUN:
        logger.info("Running new CursorSessionManager in DRY-RUN mode.")
    _demo()
