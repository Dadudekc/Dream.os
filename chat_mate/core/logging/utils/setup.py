import logging
import os
from datetime import datetime
from typing import Optional, List

def setup_logging(
    logger_name: str,
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    log_dir: Optional[str] = None,
    handlers: Optional[List[logging.Handler]] = None
) -> logging.Logger:
    """Set up a logger with advanced configuration options."""
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if log_dir is None:
        log_dir = os.path.join(os.getcwd(), "logs")

    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    logger.handlers = []

    formatter = logging.Formatter(log_format)

    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_to_file:
        if log_file is None:
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = os.path.join(log_dir, f"{logger_name}_{date_str}.log")
        else:
            if not os.path.isabs(log_file):
                log_file = os.path.join(log_dir, log_file)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if handlers:
        for handler in handlers:
            if handler not in logger.handlers:
                logger.addHandler(handler)

    return logger
