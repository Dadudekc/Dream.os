"""
Output handling service for centralizing and standardizing output across the system.
"""

import logging
from typing import Optional, Callable, List, Dict, Any
import os
import datetime

class OutputHandler:
    """
    Centralized service for handling output across the system.
    Supports console output, logging, and optional GUI callbacks.
    """
    
    def __init__(self, logger=None, output_callbacks=None, log_to_file=True, output_dir="logs"):
        """
        Initialize the OutputHandler.
        
        Args:
            logger: Optional custom logger
            output_callbacks: Optional list of callback functions for GUI updates
            log_to_file: Whether to log output to file
            output_dir: Directory for log files
        """
        self.logger = logger or logging.getLogger("OutputHandler")
        self.output_callbacks = output_callbacks or []
        self.log_to_file = log_to_file
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if self.log_to_file and not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            
        # Initialize log file if enabled
        self.log_file = None
        if self.log_to_file:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = os.path.join(self.output_dir, f"output_{timestamp}.log")
            
        self.logger.info(f"OutputHandler initialized. Log file: {self.log_file}")
    
    def output(self, message: str, level: str = "info", metadata: Optional[Dict[str, Any]] = None):
        """
        Process and distribute output to all configured destinations.
        
        Args:
            message: The message to output
            level: Log level (info, warning, error, debug)
            metadata: Optional metadata to attach to the message
        """
        # Format message with metadata if provided
        formatted_message = message
        if metadata:
            formatted_message = f"{message} [metadata: {metadata}]"
        
        # Console output
        print(formatted_message)
        
        # Log to logger with appropriate level
        if level.lower() == "warning":
            self.logger.warning(formatted_message)
        elif level.lower() == "error":
            self.logger.error(formatted_message)
        elif level.lower() == "debug":
            self.logger.debug(formatted_message)
        else:
            self.logger.info(formatted_message)
            
        # Log to file if enabled
        if self.log_to_file and self.log_file:
            try:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] [{level.upper()}] {message}\n")
            except Exception as e:
                self.logger.error(f"Failed to write to log file: {e}")
                
        # Call all registered callbacks
        for callback in self.output_callbacks:
            try:
                callback(formatted_message, level, metadata)
            except Exception as e:
                self.logger.error(f"Error in output callback: {e}")
    
    def add_callback(self, callback: Callable[[str, str, Optional[Dict[str, Any]]], None]) -> None:
        """
        Add a callback function for output.
        
        Args:
            callback: Function that accepts message, level, and metadata
        """
        if callback not in self.output_callbacks:
            self.output_callbacks.append(callback)
            self.logger.debug(f"Added output callback: {callback}")
    
    def remove_callback(self, callback: Callable) -> bool:
        """
        Remove a callback function.
        
        Args:
            callback: The callback function to remove
            
        Returns:
            bool: True if callback was removed, False if not found
        """
        if callback in self.output_callbacks:
            self.output_callbacks.remove(callback)
            self.logger.debug(f"Removed output callback: {callback}")
            return True
        return False
    
    def info(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Helper method for info-level output."""
        self.output(message, "info", metadata)
    
    def warning(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Helper method for warning-level output."""
        self.output(message, "warning", metadata)
    
    def error(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Helper method for error-level output."""
        self.output(message, "error", metadata)
    
    def debug(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Helper method for debug-level output."""
        self.output(message, "debug", metadata) 
