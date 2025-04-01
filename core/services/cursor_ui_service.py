#!/usr/bin/env python3
"""
CursorUIService

This module provides modular UI interaction capabilities for automating Cursor
interactions, previously contained in the monolithic cursor_automation.py script.
It extracts the core automation functionality into reusable components that can
be composed and injected into the larger system architecture.
"""

import os
import json
import time
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple, Callable
from pathlib import Path
from datetime import datetime
from enum import Enum

# Optional import with graceful fallback
try:
    import pyautogui
    import pyperclip
    from PIL import Image
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

# Default settings
DEFAULT_CONFIDENCE = 0.7
DEFAULT_TIMEOUT = 30  # seconds
SCREENSHOT_DIR = "debug/screenshots"

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status values for task execution."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class CursorUIService:
    """
    Provides modular UI interaction for Cursor automation.
    
    This service extracts and modularizes the core functionality from the old
    cursor_automation.py script, making it more reusable and maintainable.
    """
    
    def __init__(self, 
                browser_path: Optional[str] = None,
                cursor_url: str = "https://cursor.sh/",
                debug_mode: bool = False,
                screenshot_dir: str = SCREENSHOT_DIR,
                confidence_level: float = DEFAULT_CONFIDENCE,
                default_timeout: int = DEFAULT_TIMEOUT,
                callbacks: Optional[Dict[str, Callable]] = None):
        """
        Initialize the CursorUIService.
        
        Args:
            browser_path: Path to browser executable (optional)
            cursor_url: URL for Cursor web interface
            debug_mode: Whether to enable debug mode with screenshots
            screenshot_dir: Directory for debug screenshots
            confidence_level: Confidence threshold for image matching
            default_timeout: Default timeout for UI operations in seconds
            callbacks: Optional callbacks for various events
        """
        # Check if automation is possible
        if not HAS_PYAUTOGUI:
            logger.warning("PyAutoGUI not available, UI automation disabled")
            self.automation_available = False
        else:
            self.automation_available = True
            # Set pyautogui settings
            pyautogui.PAUSE = 0.5  # Half-second pause between actions
            pyautogui.FAILSAFE = True  # Move mouse to top-left to abort
        
        # Configuration
        self.browser_path = browser_path
        self.cursor_url = cursor_url
        self.debug_mode = debug_mode
        self.screenshot_dir = screenshot_dir
        self.confidence_level = confidence_level
        self.default_timeout = default_timeout
        
        # Event callbacks
        self.callbacks = callbacks or {}
        
        # Check if screenshot directory exists
        if debug_mode:
            os.makedirs(screenshot_dir, exist_ok=True)
            
        logger.info("CursorUIService initialized")
    
    def _trigger_callback(self, event_name: str, data: Any = None) -> None:
        """
        Trigger a callback if it exists.
        
        Args:
            event_name: Name of the event
            data: Data to pass to the callback
        """
        if event_name in self.callbacks and callable(self.callbacks[event_name]):
            try:
                self.callbacks[event_name](data)
            except Exception as e:
                logger.error(f"Error in callback for {event_name}: {e}")
    
    # ------------ SCREENSHOT FUNCTIONALITY ------------
    
    def take_screenshot(self, name: str, include_timestamp: bool = True) -> Optional[str]:
        """
        Take a screenshot for debugging or validation.
        
        Args:
            name: Base name for the screenshot
            include_timestamp: Whether to include a timestamp in the filename
            
        Returns:
            Path to the screenshot file, or None if screenshot couldn't be taken
        """
        if not self.automation_available or not self.debug_mode:
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name}.png" if include_timestamp else f"{name}.png"
            filepath = str(Path(self.screenshot_dir) / filename)
            
            pyautogui.screenshot(filepath)
            logger.debug(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
    
    # ------------ BROWSER INTERACTION ------------
    
    def start_browser(self) -> bool:
        """
        Start the browser and navigate to Cursor.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.automation_available:
            logger.warning("Automation not available, cannot start browser")
            return False
        
        try:
            # If browser path is provided, use it
            if self.browser_path:
                logger.info(f"Starting browser at {self.browser_path}")
                os.system(f'"{self.browser_path}" {self.cursor_url}')
            else:
                # Otherwise try to open with default browser
                logger.info(f"Opening {self.cursor_url} with default browser")
                pyautogui.hotkey('win', 'r')
                time.sleep(1)
                pyautogui.write(self.cursor_url)
                pyautogui.press('enter')
            
            # Wait for browser to load
            time.sleep(5)
            self.take_screenshot("browser_started")
            self._trigger_callback("browser_started", {"url": self.cursor_url})
            return True
            
        except Exception as e:
            logger.error(f"Error starting browser: {e}")
            self._trigger_callback("browser_error", {"error": str(e)})
            return False
    
    def locate_on_screen(self, image_path: str, timeout: int = None) -> Optional[Tuple[int, int]]:
        """
        Locate an image on screen with timeout.
        
        Args:
            image_path: Path to the image to look for
            timeout: Maximum time to wait in seconds (uses default_timeout if None)
            
        Returns:
            Tuple of (x, y) coordinates if found, None otherwise
        """
        if not self.automation_available:
            return None
        
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                location = pyautogui.locateCenterOnScreen(
                    image_path, 
                    confidence=self.confidence_level
                )
                if location:
                    logger.info(f"Found image {image_path} at {location}")
                    self._trigger_callback("image_found", {
                        "image": image_path,
                        "location": location
                    })
                    return location
            except Exception as e:
                logger.debug(f"Error looking for image {image_path}: {e}")
            
            time.sleep(0.5)
        
        logger.warning(f"Image {image_path} not found after {timeout} seconds")
        self.take_screenshot(f"image_not_found_{Path(image_path).stem}")
        self._trigger_callback("image_not_found", {"image": image_path})
        return None
    
    def click_image(self, image_path: str, timeout: int = None) -> bool:
        """
        Click on an image when it appears on screen.
        
        Args:
            image_path: Path to the image to click
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if clicked, False otherwise
        """
        if not self.automation_available:
            return False
        
        location = self.locate_on_screen(image_path, timeout)
        if location:
            x, y = location
            pyautogui.click(x, y)
            logger.info(f"Clicked on {image_path}")
            self.take_screenshot(f"after_click_{Path(image_path).stem}")
            self._trigger_callback("image_clicked", {
                "image": image_path,
                "location": location
            })
            return True
        return False
    
    # ------------ KEYBOARD ACTIONS ------------
    
    def type_text(self, text: str, use_clipboard: bool = True) -> bool:
        """
        Type text at the current cursor position.
        
        Args:
            text: Text to type
            use_clipboard: Whether to use clipboard for pasting (more reliable)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.automation_available:
            return False
        
        try:
            if use_clipboard:
                # Use pyperclip for more reliable pasting of complex text
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')
            else:
                # Type directly (slower but works when clipboard is unavailable)
                pyautogui.write(text)
                
            logger.info(f"Typed text: {text[:30]}...")
            self._trigger_callback("text_typed", {"length": len(text)})
            return True
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            self._trigger_callback("typing_error", {"error": str(e)})
            return False
    
    def trigger_hotkey(self, *keys) -> bool:
        """
        Trigger keyboard hotkey.
        
        Args:
            keys: Key combinations to press
            
        Returns:
            True if successful, False otherwise
        """
        if not self.automation_available:
            return False
        
        try:
            pyautogui.hotkey(*keys)
            logger.info(f"Triggered hotkey: {'+'.join(keys)}")
            self._trigger_callback("hotkey_triggered", {"keys": keys})
            return True
        except Exception as e:
            logger.error(f"Error triggering hotkey: {e}")
            self._trigger_callback("hotkey_error", {"error": str(e)})
            return False
    
    # ------------ CLIPBOARD ACTIONS ------------
    
    def get_clipboard_content(self) -> Optional[str]:
        """
        Get content from clipboard.
        
        Returns:
            Clipboard content as string, or None if failed
        """
        if not self.automation_available:
            return None
        
        try:
            content = pyperclip.paste()
            logger.debug(f"Got clipboard content: {len(content)} chars")
            return content
        except Exception as e:
            logger.error(f"Error getting clipboard content: {e}")
            return None
    
    def set_clipboard_content(self, content: str) -> bool:
        """
        Set content to clipboard.
        
        Args:
            content: Content to set
            
        Returns:
            True if successful, False otherwise
        """
        if not self.automation_available:
            return False
        
        try:
            pyperclip.copy(content)
            logger.debug(f"Set clipboard content: {len(content)} chars")
            return True
        except Exception as e:
            logger.error(f"Error setting clipboard content: {e}")
            return False
    
    # ------------ INTEGRATED TASK EXECUTION ------------
    
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task by interacting with Cursor through the browser.
        
        This method encapsulates the complete task execution flow, from
        opening the browser to submitting the prompt and capturing the result.
        
        Args:
            task: Task data including ID, prompt, and context
            
        Returns:
            Result data with status and output
        """
        if not self.automation_available:
            return {
                "task_id": task.get("id"),
                "status": ExecutionStatus.ERROR.value,
                "error": "UI automation not available"
            }
        
        # Prepare result data structure
        result = {
            "task_id": task.get("id"),
            "start_time": datetime.now().isoformat(),
            "status": ExecutionStatus.RUNNING.value,
            "output": "",
            "screenshot": None
        }
        
        self._trigger_callback("task_execution_started", {
            "task_id": task.get("id"),
            "timestamp": result["start_time"]
        })
        
        # Log timing
        start_time = time.time()
        
        try:
            # Start browser if needed
            browser_started = self.start_browser()
            if not browser_started:
                result["status"] = ExecutionStatus.ERROR.value
                result["error"] = "Failed to start browser"
                return result
            
            # Get the rendered prompt from the task
            prompt = task.get("rendered_prompt", "")
            if not prompt:
                logger.error("Task has no rendered prompt")
                result["status"] = ExecutionStatus.ERROR.value
                result["error"] = "Task has no rendered prompt"
                return result
            
            # Look for new chat button and click it
            new_chat_found = self.click_image("resources/cursor_new_chat.png")
            if not new_chat_found:
                logger.warning("New chat button not found, trying to use existing chat")
            
            # Wait for prompt input area
            input_found = self.click_image("resources/cursor_input_area.png")
            if not input_found:
                logger.error("Prompt input area not found")
                result["status"] = ExecutionStatus.ERROR.value
                result["error"] = "Input area not found"
                result["screenshot"] = self.take_screenshot("input_area_not_found")
                return result
            
            # Type the prompt
            self.type_text(prompt)
            time.sleep(1)
            
            # Press Ctrl+Enter to submit
            self.trigger_hotkey('ctrl', 'enter')
            logger.info("Submitted prompt")
            self.take_screenshot("prompt_submitted")
            
            # Wait for response to complete
            response_complete = False
            wait_start = time.time()
            
            # Check for the "regenerate" button to appear, indicating completion
            while time.time() - wait_start < 120:  # 2 minute max wait
                if self.locate_on_screen("resources/cursor_regenerate.png", timeout=2):
                    response_complete = True
                    break
                time.sleep(2)
            
            if not response_complete:
                logger.warning("Response may not have completed")
                result["status"] = ExecutionStatus.TIMEOUT.value
            else:
                logger.info("Response completed")
                result["status"] = ExecutionStatus.COMPLETED.value
            
            # Take a screenshot of the result
            if self.debug_mode:
                screenshot_path = self.take_screenshot(f"task_{task.get('id')}")
                result["screenshot"] = screenshot_path
            
            # Use keyboard shortcuts to select and copy all text
            self.trigger_hotkey('ctrl', 'a')
            time.sleep(0.5)
            self.trigger_hotkey('ctrl', 'c')
            time.sleep(0.5)
            
            # Get the copied text from clipboard
            output = self.get_clipboard_content()
            result["output"] = output or ""
            result["end_time"] = datetime.now().isoformat()
            result["duration_seconds"] = time.time() - start_time
            
            logger.info(f"Task execution completed in {result['duration_seconds']:.2f} seconds")
            self._trigger_callback("task_execution_completed", result)
            return result
            
        except Exception as e:
            logger.error(f"Error executing task: {e}")
            self.take_screenshot("task_execution_error")
            
            # Update result with error
            result["status"] = ExecutionStatus.ERROR.value
            result["error"] = str(e)
            result["end_time"] = datetime.now().isoformat()
            result["duration_seconds"] = time.time() - start_time
            
            self._trigger_callback("task_execution_error", {
                "task_id": task.get("id"),
                "error": str(e)
            })
            return result
    
    # ------------ VALIDATION FUNCTIONALITY ------------
    
    def validate_task_result(self, result: Dict[str, Any], 
                           criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a task result against criteria.
        
        Args:
            result: Task execution result
            criteria: Validation criteria
            
        Returns:
            Validation results
        """
        logger.info(f"Validating task result for task {result.get('task_id')}")
        
        validation = {
            "task_id": result.get("task_id"),
            "timestamp": datetime.now().isoformat(),
            "passed": False,
            "checks": [],
            "requeue": False
        }
        
        output = result.get("output", "")
        
        # Run checks
        all_passed = True
        
        # Check if output contains expected content
        if "expected_content" in criteria:
            for content in criteria["expected_content"]:
                check = {
                    "type": "content_present",
                    "expected": content,
                    "passed": content in output
                }
                validation["checks"].append(check)
                all_passed = all_passed and check["passed"]
        
        # Check if output excludes unwanted content
        if "excluded_content" in criteria:
            for content in criteria["excluded_content"]:
                check = {
                    "type": "content_absent",
                    "excluded": content,
                    "passed": content not in output
                }
                validation["checks"].append(check)
                all_passed = all_passed and check["passed"]
        
        # Check minimum length
        if "min_length" in criteria:
            min_length = criteria["min_length"]
            check = {
                "type": "min_length",
                "expected": min_length,
                "actual": len(output),
                "passed": len(output) >= min_length
            }
            validation["checks"].append(check)
            all_passed = all_passed and check["passed"]
        
        # Check images if needed
        if "image_validation" in criteria and result.get("screenshot"):
            # Simple presence check for now
            check = {
                "type": "image_present",
                "passed": os.path.exists(result["screenshot"])
            }
            validation["checks"].append(check)
            all_passed = all_passed and check["passed"]
        
        # Set validation result
        validation["passed"] = all_passed
        
        # Determine if task should be requeued
        should_requeue = not all_passed and criteria.get("requeue_on_failure", False)
        max_attempts = criteria.get("max_attempts", 3)
        current_attempts = result.get("attempts", 1)
        
        if should_requeue and current_attempts < max_attempts:
            validation["requeue"] = True
        
        logger.info(f"Validation {'passed' if all_passed else 'failed'}")
        self._trigger_callback("task_validated", validation)
        
        return validation


# Factory for creating CursorUIService instances
class CursorUIServiceFactory:
    """Factory for creating properly configured CursorUIService instances."""
    
    @staticmethod
    def create(browser_path: Optional[str] = None,
              debug_mode: bool = False,
              service_registry = None) -> CursorUIService:
        """
        Create a properly configured CursorUIService instance.
        
        Args:
            browser_path: Path to browser executable
            debug_mode: Whether to enable debug mode
            service_registry: Optional service registry for dependency injection
            
        Returns:
            Configured CursorUIService instance
        """
        # Create service with base configuration
        service = CursorUIService(
            browser_path=browser_path,
            debug_mode=debug_mode,
            callbacks={
                "task_execution_completed": lambda data: logger.info(
                    f"Task {data.get('task_id')} completed with "
                    f"{len(data.get('output', ''))} chars output"
                ),
                "task_execution_error": lambda data: logger.error(
                    f"Task {data.get('task_id')} failed: {data.get('error')}"
                )
            }
        )
        
        # Add registry-based callback support if available
        if service_registry:
            # Try to get task history service for event recording
            task_history = service_registry.get("task_history_service")
            if task_history:
                service.callbacks["task_execution_completed"] = task_history.record_execution
                service.callbacks["task_validated"] = task_history.record_validation
        
        return service


# For testing/debugging in standalone mode
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create service
    service = CursorUIServiceFactory.create(debug_mode=True)
    
    # Basic test task
    test_task = {
        "id": f"test_{int(time.time())}",
        "rendered_prompt": "What is 2+2?"
    }
    
    # Execute task
    result = service.execute_task(test_task)
    
    # Validate result
    validation = service.validate_task_result(
        result, 
        {"expected_content": ["4"], "min_length": 1}
    )
    
    # Print results
    print(f"Task execution result: {result.get('status')}")
    print(f"Output: {result.get('output')}")
    print(f"Validation passed: {validation.get('passed')}")
    for check in validation.get("checks", []):
        print(f"Check '{check.get('type')}': {check.get('passed')}") 