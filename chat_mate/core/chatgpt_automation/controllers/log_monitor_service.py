import os
import logging

# Path to the log file that gets updated with new responses or commands.
LOG_FILE = "scraped_log.txt"

# Internal pointer to track our last read position in the log file.
_last_position = 0

def get_latest_log():
    """
    Monitors the scraped log file for new entries.
    Reads from the last known position, updates the pointer,
    and returns the new log text if available.
    If no new text is available, returns None.
    """
    global _last_position
    logger = logging.getLogger(__name__)

    if not os.path.exists(LOG_FILE):
        logger.warning(f"Log file '{LOG_FILE}' does not exist.")
        return None

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            # Move to the last read position.
            f.seek(_last_position)
            new_text = f.read()
            # Update the pointer for the next call.
            _last_position = f.tell()
            if new_text.strip():
                return new_text.strip()
    except Exception as e:
        logger.error(f"Error reading log file '{LOG_FILE}': {e}")
    
    return None
