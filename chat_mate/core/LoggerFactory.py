# core/logging/LoggerFactory.py

import logging
from typing import Optional
import os

# Import the new LoggerFactory
from core.logging.factories.LoggerFactory import LoggerFactory as NewLoggerFactory
from core.config.config_manager import ConfigManager
from core.ConsoleLogger import ConsoleLogger

class LoggerFactory:
    """
    Legacy bridge to the new logging system.
    Provides backward compatibility while redirecting to the new implementation.
    """

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str, level: int = logging.INFO, log_to_file: Optional[str] = None) -> logging.Logger:
        """
        Bridge method that creates a Python standard logger.
        This maintains compatibility with code expecting a standard logger.

        Args:
            name (str): Name of the logger.
            level (int): Logging level (default: logging.INFO).
            log_to_file (Optional[str]): Path to a log file (optional).

        Returns:
            logging.Logger: Configured logger instance.
        """
        if not isinstance(name, str):
            raise TypeError('A logger name must be a string')
            
        if name in cls._loggers:
            return cls._loggers[name]

        # Use the new factory's method to create a standard logger
        logger = NewLoggerFactory.create_standard_logger(name, level, log_to_file)
        cls._loggers[name] = logger
        return logger
