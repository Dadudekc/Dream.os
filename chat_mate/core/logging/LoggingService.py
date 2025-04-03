import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Union

class LoggingService:
    """
    Centralized logging service that provides standardized logging capabilities
    across the application. Supports multiple output destinations including
    console, file, and custom handlers.
    """
    
    def __init__(
        self, 
        name: str, 
        level: int = logging.INFO,
        log_file: Optional[str] = None,
        log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        date_format: str = "%Y-%m-%d %H:%M:%S"
    ):
        """
        Initialize the logging service.
        
        Args:
            name: Logger name (typically module or component name)
            level: Logging level (default: INFO)
            log_file: Optional path to log file
            log_format: Format string for log messages
            date_format: Format string for timestamps
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.log_format = log_format
        self.date_format = date_format
        
        # Create formatter
        self.formatter = logging.Formatter(log_format, date_format)
        
        # Ensure the logger doesn't already have handlers
        if not self.logger.handlers:
            # Add console handler by default
            self._add_console_handler()
            
            # Add file handler if specified
            if log_file:
                self._add_file_handler(log_file)
    
    def _add_console_handler(self) -> None:
        """Add a handler that logs to console."""
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
    
    def _add_file_handler(self, log_file: str) -> None:
        """Add a handler that logs to a file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
    
    def add_custom_handler(self, handler: logging.Handler) -> None:
        """Add a custom log handler."""
        handler.setFormatter(self.formatter)
        self.logger.addHandler(handler)
    
    # Logging methods
    def debug(self, message: str, *args, **kwargs) -> None:
        """Log a debug message."""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, domain: str = None, **kwargs) -> None:
        """Log an info message."""
        if domain:
            message = f"[{domain}] {message}"
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs) -> None:
        """Log a warning message."""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs) -> None:
        """Log an error message."""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs) -> None:
        """Log a critical message."""
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, exc_info=True, **kwargs) -> None:
        """Log an exception."""
        self.logger.exception(message, *args, exc_info=exc_info, **kwargs)
    
    def log_system_event(self, message: str, event_type: str = "INFO") -> None:
        """Log a system event with special formatting."""
        level = getattr(logging, event_type.upper(), logging.INFO)
        self.logger.log(level, f"SYSTEM EVENT: {message}")
    
    def set_level(self, level: int) -> None:
        """Set the logging level."""
        self.logger.setLevel(level)

    def log(self, message: str, level: int = logging.INFO, *args, domain: str = None, **kwargs) -> None:
        """
        Log a message with the specified level.
        
        Args:
            message: The message to log
            level: The logging level (default: INFO)
            domain: Optional domain to prefix the message with
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        if domain:
            message = f"[{domain}] {message}"
        self.logger.log(level, message, *args, **kwargs) 
