#!/usr/bin/env python3
"""
overnight_prompt_queue_dynamic_wait_enhanced.py

Enhanced version that automates overnight prompt submission to the Cursor IDE with:
1. Dynamic waiting for an Accept button image.
2. Fallback fixed delay.
3. Persistent calibration of coordinates.
4. Logging to console and file.
5. Dry-run mode.
6. Queueing prompts with context injection.
7. Post-execution review of responses.
8. Modularized output handling.

Usage:
    python overnight_prompt_queue_dynamic_wait_enhanced.py
    python overnight_prompt_queue_dynamic_wait_enhanced.py --dry-run
"""

import time
import sys
import json
import os
import argparse
import logging
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv

if not DRY_RUN:
    import pyautogui
    import pygetwindow as gw
else:
    print("Running in DRY-RUN mode: UI actions will be simulated.")

# ------------- CONFIGURATION -------------
WINDOW_TITLE = "Cursor"                  # Title of your Cursor IDE window
TYPING_SPEED = 0.03                      # Delay between keystrokes
MAX_WAIT_TIME = 600                      # Max dynamic wait time (seconds)
POLL_INTERVAL = 2                        # Poll interval (seconds)
ACCEPT_IMAGE = "accept_button.png"       # Image file for detecting generation completion
CALIBRATION_FILE = "calibration.json"    # File to store/load calibrated coords
LOG_FILE = "prompt_queue.log"            # Log file path

# Default coords if in dry-run mode and no calibration exists
DEFAULT_PROMPT_BOX_COORDS = (300, 1050)
DEFAULT_ACCEPT_BUTTON_COORDS = (1800, 500)
# -----------------------------------------

# Setup logger for console + file
logger = logging.getLogger("PromptQueueLogger")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)

# -------------------------
# Modular Output Handler
# -------------------------
class OutputHandler:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("OutputHandler")
    
    def output(self, message: str):
        print(message)
        self.logger.info(message)

output_handler = OutputHandler(logger=logger)

# -------------------------
# Calibration & Utility Functions
# -------------------------
def load_calibrated_coords() -> dict:
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                coords = json.load(f)
            logger.info(f"Loaded calibrated coordinates from {CALIBRATION_FILE}: {coords}")
            return coords
        except Exception as e:
            logger.error(f"Error loading calibration file: {e}")
    return {}

def save_calibrated_coords(coords: dict):
    try:
        with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
            json.dump(coords, f, indent=2)
        logger.info(f"Saved calibrated coordinates to {CALIBRATION_FILE}.")
    except Exception as e:
        logger.error(f"Error saving calibration file: {e}")

def calibrate_coordinate(prompt: str) -> tuple:
    logger.info(prompt)
    if DRY_RUN:
        dummy = (100, 100)
        logger.info(f"(Dry-run) Would record coordinates: {dummy}")
        return dummy

    print(prompt)
    print("Move your mouse to the desired location and press Enter...")
    input("Press Enter to record the current mouse position: ")
    pos = pyautogui.position()
    coords = (pos.x, pos.y)
    logger.info(f"Recorded coordinates: {coords}")
    return coords

def focus_cursor_window(window_title: str) -> bool:
    if DRY_RUN:
        logger.info(f"(Dry-run) Would focus window titled '{window_title}'.")
        return True
    windows = gw.getWindowsWithTitle(window_title)
    if not windows:
        logger.error(f"Could not find a window titled '{window_title}'.")
        return False
    win = windows[0]
    win.activate()
    time.sleep(1)
    logger.info(f"Focused window titled '{window_title}'.")
    return True

def click_coordinate(coords: tuple):
    if DRY_RUN:
        logger.info(f"(Dry-run) Would click at {coords}.")
    else:
        pyautogui.moveTo(coords[0], coords[1])
        pyautogui.click()
    time.sleep(0.5)

def type_prompt_and_send(prompt: str, typing_speed: float):
    if DRY_RUN:
        logger.info(f"(Dry-run) Would type: {prompt}")
        logger.info("(Dry-run) Would press Enter.")
    else:
        pyautogui.write(prompt, interval=typing_speed)
        pyautogui.press("enter")
    logger.info("Prompt sent.")

def wait_for_generation(max_wait: int, poll_interval: int) -> bool:
    if DRY_RUN:
        logger.info(f"(Dry-run) Would wait dynamically for {max_wait} seconds.")
        return True
    logger.info("Waiting dynamically for generation to complete...")
    start_time = time.time()
    while time.time() - start_time < max_wait:
        location = pyautogui.locateOnScreen(ACCEPT_IMAGE, confidence=0.9)
        if location:
            logger.info(f"Detected Accept button at {location}.")
            return True
        time.sleep(poll_interval)
    logger.warning("Dynamic wait timed out. Falling back to fixed wait.")
    return False

# -------------------------
# Context Injection Simulation
# -------------------------
def retrieve_context() -> dict:
    """
    Simulate retrieval of external context (e.g., project analysis or memory snapshot)
    from a ProjectScanner or similar service.
    """
    # In production, import and call your ProjectScanner here.
    context = {
        "project_analysis": "All systems operational. Module integration complete.",
        "memory_snapshot": {"last_update": datetime.now().isoformat(), "status": "stable"}
    }
    logger.info(f"Retrieved external context: {context}")
    return context

# -------------------------
# Post-Execution Review
# -------------------------
def post_execution_review(responses: List[str]):
    """
    Aggregate and analyze the responses collected from the prompt queue.
    For instance, report average length and warn if responses are too short.
    """
    if not responses:
        output_handler.output("⚠️ No responses to review.")
        return

    total_length = sum(len(resp) for resp in responses)
    avg_length = total_length / len(responses)
    output_handler.output(f"Post-Execution Review: {len(responses)} responses collected. Average length: {avg_length:.2f} characters.")
    
    # Example check: if any response is unusually short, flag it.
    for idx, resp in enumerate(responses, start=1):
        if len(resp) < 50:
            output_handler.output(f"⚠️ Response {idx} seems too short.")

# -------------------------
# Queueing Prompts and Processing
# -------------------------
def run_prompt_queue(prompts: List[str],
                     prompt_box_coords: tuple,
                     accept_button_coords: tuple,
                     window_title: str,
                     typing_speed: float):
    """
    Processes each prompt by:
      1. Focusing the Cursor window.
      2. Clicking the prompt input box.
      3. Typing + sending the prompt (with injected context).
      4. Dynamically waiting for generation or fallback.
      5. Clicking the Accept button.
    Collects and returns responses for post-execution review.
    """
    collected_responses = []

    # Retrieve external context and inject into each prompt.
    external_context = retrieve_context()
    
    for i, prompt in enumerate(prompts, start=1):
        output_handler.output(f"--- Processing prompt {i} of {len(prompts)} ---")

        if not focus_cursor_window(window_title):
            logger.error("Unable to focus Cursor window. Exiting prompt queue.")
            break

        output_handler.output("Clicking the prompt input box...")
        click_coordinate(prompt_box_coords)

        # Inject context into the prompt.
        prompt_with_context = f"{prompt}\nContext: {json.dumps(external_context, indent=2)}"
        output_handler.output(f"Typing prompt #{i}:\n{prompt_with_context}")
        type_prompt_and_send(prompt_with_context, typing_speed)

        if wait_for_generation(MAX_WAIT_TIME, POLL_INTERVAL):
            output_handler.output("Clicking the dynamically detected Accept button...")
            click_coordinate(accept_button_coords)
        else:
            FIXED_WAIT = 30
            output_handler.output(f"Falling back: waiting an extra {FIXED_WAIT} seconds before clicking Accept.")
            time.sleep(FIXED_WAIT)
            click_coordinate(accept_button_coords)

        # In a real scenario, you might capture a response from the UI.
        # For simulation, we use a stub response.
        simulated_response = f"[Simulated Response for Prompt {i}]"
        collected_responses.append(simulated_response)
        output_handler.output(f"Prompt {i} processed. Response: {simulated_response}")

    output_handler.output("All queued prompts have been processed.")
    return collected_responses

# -------------------------
# Argument Parsing and Main Entry
# -------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Overnight Prompt Queue with Dynamic Wait, Calibration, Context Injection, and Post-Execution Review (Dry-Run Supported)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate UI actions without actual clicks/typing")
    return parser.parse_args()

def main():
    global DRY_RUN
    args = parse_args()
    if args.dry_run:
        DRY_RUN = True

    # Load saved calibration if available
    coords = load_calibrated_coords()
    if coords.get("prompt_box") and coords.get("accept_button"):
        prompt_box_coords = tuple(coords["prompt_box"])
        accept_button_coords = tuple(coords["accept_button"])
    else:
        print("=== Calibration Phase ===")
        prompt_box_coords = calibrate_coordinate("Calibrate Prompt Input Box:")
        accept_button_coords = calibrate_coordinate("Calibrate Accept Button:")
        save_calibrated_coords({
            "prompt_box": prompt_box_coords,
            "accept_button": accept_button_coords
        })

    logger.info(f"Using Prompt Box Coordinates: {prompt_box_coords}")
    logger.info(f"Using Accept Button Coordinates: {accept_button_coords}")

    # Example queue of high-level prompts.
    queued_prompts = [
        "Increase test coverage for chat_mate.py by generating additional tests. Focus on edge cases.",
        "Refactor PathManager into a micro-factory with dependency injection.",
        "Clean up feedback engine for memory safety and reduce overhead in chat_mate project.",
        "Enhance logging in overnight_test_generator for better debugging."
    ]

    responses = run_prompt_queue(
        prompts=queued_prompts,
        prompt_box_coords=prompt_box_coords,
        accept_button_coords=accept_button_coords,
        window_title=WINDOW_TITLE,
        typing_speed=TYPING_SPEED
    )

    post_execution_review(responses)

if __name__ == "__main__":
    main()
