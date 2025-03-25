import os
import re
from pathlib import Path

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by replacing invalid characters."""
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', filename)
    return sanitized.strip().replace(' ', '_')[:50]

def get_project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return Path(__file__).parent.parent

def ensure_directory_exists(directory: str) -> None:
    """Ensure that a directory exists, creating it if necessary."""
    os.makedirs(directory, exist_ok=True)
