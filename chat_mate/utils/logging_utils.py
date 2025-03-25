import logging
from typing import Optional
from core.logging.utils.setup import setup_logging

def setup_basic_logging(
    logger_name: str,
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    log_to_file: bool = False,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """A simple wrapper around the advanced setup_logging function."""
    return setup_logging(
        logger_name=logger_name,
        log_level=log_level,
        log_to_console=log_to_console,
        log_to_file=log_to_file,
        log_file=log_file,
        log_format=log_format
    )
