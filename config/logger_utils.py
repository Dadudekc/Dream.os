"""
Logging utilities for configuring and managing application logging.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

def setup_logger(
    name: str,
    level: str = "INFO",
    log_format: Optional[str] = None,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with the specified configuration.
    
    Args:
        name: Name of the logger
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom format string for log messages
        log_file: Name of the log file
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set log level
    level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Use default format if none provided
    if not log_format:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        if log_dir:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            log_file = str(log_path / log_file)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(config: Dict[str, Any], name: str = None) -> logging.Logger:
    """
    Get a logger configured according to the application configuration.
    
    Args:
        config: Configuration dictionary containing logging settings
        name: Optional name for the logger (defaults to root logger)
        
    Returns:
        Configured logger instance
    """
    logging_config = config.get("logging", {})
    log_dir = os.path.join(config.get("paths", {}).get("logs", "logs"))
    
    return setup_logger(
        name=name or "root",
        level=logging_config.get("level", "INFO"),
        log_format=logging_config.get("format"),
        log_file=logging_config.get("file"),
        log_dir=log_dir
    )

def clear_handlers(logger: logging.Logger) -> None:
    """
    Remove all handlers from a logger.
    Useful when reconfiguring logging or shutting down.
    
    Args:
        logger: Logger instance to clear
    """
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close() 
