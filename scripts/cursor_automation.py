#!/usr/bin/env python3
"""
cursor_automation.py - DEPRECATED

This module is deprecated. Please use core.services.cursor_ui_service.CursorUIService instead.

This file now serves as a backward compatibility layer, redirecting all calls to the 
new modular implementation in CursorUIService.
"""

import os
import sys
import time
import json
import logging
import warnings
from typing import Dict, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the new service
from core.services.cursor_ui_service import CursorUIService, CursorUIServiceFactory

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cursor_automation')

# Issue deprecation warning
warnings.warn(
    "cursor_automation.py is deprecated. Please use core.services.cursor_ui_service.CursorUIService instead.",
    DeprecationWarning,
    stacklevel=2
)

class CursorAutomation:
    """
    DEPRECATED: Compatibility wrapper for CursorUIService.
    
    This class is maintained for backward compatibility. New code should use
    core.services.cursor_ui_service.CursorUIService directly.
    """
    
    def __init__(self, browser_path: Optional[str] = None, debug_mode: bool = False):
        """
        Initialize the CursorAutomation wrapper.
        
        Args:
            browser_path: Path to browser executable
            debug_mode: Whether to enable debug mode
        """
        # Issue another deprecation warning at instance creation time
        warnings.warn(
            "CursorAutomation is deprecated. Please use CursorUIService instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Create underlying service
        self.service = CursorUIServiceFactory.create(
            browser_path=browser_path,
            debug_mode=debug_mode
        )
        logger.info("CursorAutomation initialized (using CursorUIService internally)")
    
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task by interacting with Cursor.
        
        Args:
            task: Task data including prompt
            
        Returns:
            Execution result
        """
        # Forward to service
        return self.service.execute_task(task)
    
    def validate_task_result(self, result: Dict[str, Any], 
                           criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a task result against criteria.
        
        Args:
            result: Execution result
            criteria: Validation criteria
            
        Returns:
            Validation result
        """
        # Forward to service
        return self.service.validate_task_result(result, criteria)
    
    # Legacy methods below redirect to appropriate service methods
    
    def start_browser(self) -> bool:
        """Start the browser and navigate to Cursor."""
        return self.service.start_browser()
    
    def click_image(self, image_path: str, timeout: Optional[int] = None) -> bool:
        """Click on an image when it appears on screen."""
        return self.service.click_image(image_path, timeout)
    
    def take_screenshot(self, name: str) -> Optional[str]:
        """Take a screenshot for debugging or validation."""
        return self.service.take_screenshot(name)
    
    def type_text(self, text: str, use_clipboard: bool = True) -> bool:
        """Type text at the current cursor position."""
        return self.service.type_text(text, use_clipboard)
    
    def get_clipboard_content(self) -> Optional[str]:
        """Get content from clipboard."""
        return self.service.get_clipboard_content()


# Function for backward compatibility with script execution
def execute_prompt(prompt: str, 
                 browser_path: Optional[str] = None, 
                 debug_mode: bool = False) -> Dict[str, Any]:
    """
    Execute a prompt using the CursorUIService.
    
    Args:
        prompt: Prompt text to execute
        browser_path: Path to browser executable
        debug_mode: Whether to enable debug mode
        
    Returns:
        Execution result
    """
    # Create service
    service = CursorUIServiceFactory.create(
        browser_path=browser_path,
        debug_mode=debug_mode
    )
    
    # Create a simple task
    task = {
        "id": f"manual_{int(time.time())}",
        "rendered_prompt": prompt
    }
    
    # Execute task
    return service.execute_task(task)


# Command-line interface for backward compatibility
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="DEPRECATED: Execute prompts in Cursor")
    parser.add_argument("--prompt", type=str, help="Prompt to execute")
    parser.add_argument("--file", type=str, help="File containing prompt")
    parser.add_argument("--browser", type=str, help="Path to browser executable")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Display deprecation message
    print("===== DEPRECATION NOTICE =====")
    print("This script is deprecated and will be removed in a future version.")
    print("Please use the new CursorUIService class directly:")
    print("from core.services.cursor_ui_service import CursorUIService, CursorUIServiceFactory")
    print("===============================\n")
    
    # Get prompt text
    prompt_text = ""
    if args.prompt:
        prompt_text = args.prompt
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                prompt_text = f.read()
        except Exception as e:
            logger.error(f"Error reading prompt file: {e}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
    
    # Execute prompt
    result = execute_prompt(
        prompt=prompt_text,
        browser_path=args.browser,
        debug_mode=args.debug
    )
    
    # Print result
    print(f"Status: {result.get('status')}")
    print(f"Output length: {len(result.get('output', ''))}")
    if result.get('output'):
        print("\nOutput preview:")
        print(result.get('output')[:500] + ("..." if len(result.get('output')) > 500 else "")) 