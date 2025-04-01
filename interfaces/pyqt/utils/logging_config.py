"""
Logging Configuration Module

This module provides centralized logging configuration for the Dream.OS interface.
"""

import logging
import os
from typing import Optional

def configure_logging(level: int = logging.DEBUG) -> None:
    """
    Configure logging for the Dream.OS interface.
    This should be called once at application startup.
    
    Args:
        level: The logging level to use. Defaults to DEBUG.
    """
    # Check if logging is already configured
    if logging.getLogger().hasHandlers():
        return
        
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Set level for specific loggers
    logging.getLogger('matplotlib').setLevel(logging.INFO)
    logging.getLogger('git').setLevel(logging.INFO)
    
    # Create logger for the interface
    interface_logger = logging.getLogger('interfaces.pyqt')
    interface_logger.setLevel(level)
    
    # Log configuration complete
    interface_logger.debug("Logging configured successfully") 