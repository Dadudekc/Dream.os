import logging
import sys
from datetime import datetime

class ConsoleLogger:
    """
    A logger that outputs messages to the console with color formatting.
    """
    
    # ANSI color codes
    RESET = "\033[0m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    
    def __init__(self, name="ConsoleLogger", level=logging.INFO):
        """
        Initialize the console logger.
        
        Args:
            name (str): Name of the logger
            level (int): Logging level
        """
        self.name = name
        self.level = level
        
        # Configure logging
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Create console handler if not already exists
        if not self.logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            self.logger.addHandler(console_handler)
    
    def _format_message(self, level, message):
        """Format message with timestamp and level indicator."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if level == logging.DEBUG:
            color = self.CYAN
            level_str = "DEBUG"
        elif level == logging.INFO:
            color = self.GREEN
            level_str = "INFO"
        elif level == logging.WARNING:
            color = self.YELLOW
            level_str = "WARNING"
        elif level == logging.ERROR:
            color = self.RED
            level_str = "ERROR"
        elif level == logging.CRITICAL:
            color = self.MAGENTA + self.BOLD
            level_str = "CRITICAL"
        else:
            color = self.RESET
            level_str = "LOG"
        
        return f"{color}[{timestamp}] [{self.name}] [{level_str}] {message}{self.RESET}"
    
    def debug(self, message):
        """Log a debug message."""
        if self.level <= logging.DEBUG:
            formatted = self._format_message(logging.DEBUG, message)
            self.logger.debug(formatted)
    
    def info(self, message):
        """Log an info message."""
        if self.level <= logging.INFO:
            formatted = self._format_message(logging.INFO, message)
            self.logger.info(formatted)
    
    def warning(self, message):
        """Log a warning message."""
        if self.level <= logging.WARNING:
            formatted = self._format_message(logging.WARNING, message)
            self.logger.warning(formatted)
    
    def error(self, message):
        """Log an error message."""
        if self.level <= logging.ERROR:
            formatted = self._format_message(logging.ERROR, message)
            self.logger.error(formatted)
    
    def critical(self, message):
        """Log a critical message."""
        if self.level <= logging.CRITICAL:
            formatted = self._format_message(logging.CRITICAL, message)
            self.logger.critical(formatted)
    
    def log(self, level, message):
        """Log a message at the specified level."""
        if level == logging.DEBUG:
            self.debug(message)
        elif level == logging.INFO:
            self.info(message)
        elif level == logging.WARNING:
            self.warning(message)
        elif level == logging.ERROR:
            self.error(message)
        elif level == logging.CRITICAL:
            self.critical(message)
        else:
            self.info(message) 