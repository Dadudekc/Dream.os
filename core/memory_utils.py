import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

def load_memory_file(path: str, default_structure: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Load a memory file with proper handling of empty or non-existent files.
    
    Args:
        path (str): Path to the memory file
        default_structure (Dict[str, Any], optional): Default structure to use if file is empty/invalid.
            If not provided, returns an empty dict.
            
    Returns:
        Dict[str, Any]: The loaded memory data or default structure
    """
    # Default structure if none provided
    if default_structure is None:
        default_structure = {}
        
    try:
        # If file doesn't exist or is empty, return default structure
        if not os.path.exists(path) or os.stat(path).st_size == 0:
            logger.info(f"Memory file {path} is empty or doesn't exist. Using default structure.")
            # Ensure directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # Save default structure
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default_structure, f, indent=2)
            return default_structure
            
        # Try to load existing file
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Successfully loaded memory from {path}")
            return data
            
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON in memory file {path}. Using default structure.")
        # Backup corrupted file
        if os.path.exists(path):
            backup_path = f"{path}.corrupted"
            try:
                os.rename(path, backup_path)
                logger.info(f"Backed up corrupted file to {backup_path}")
            except Exception as e:
                logger.error(f"Failed to backup corrupted file: {e}")
        
        # Create new file with default structure
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default_structure, f, indent=2)
        return default_structure
        
    except Exception as e:
        logger.error(f"Error loading memory file {path}: {e}")
        return default_structure

def fix_memory_file(file_path: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    Verifies and fixes memory JSON files, ensuring valid JSON structure.

    Args:
        file_path: Path to the memory JSON file.
        logger: Optional logger for logging the repair process.

    Returns:
        bool: True if the file was repaired or already valid, False if unrecoverable.
    """
    log = logger or logging.getLogger(__name__)
    path = Path(file_path)

    if not path.exists():
        log.warning(f"Memory file not found at {file_path}. Creating default empty JSON.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        return True

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            json.load(file)
        log.info(f"Memory file {file_path} is already valid.")
        return True
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON detected in {file_path}: {e}. Attempting repair...")
        backup_path = path.with_suffix(".bak.json")
        path.rename(backup_path)
        path.write_text("{}", encoding="utf-8")
        log.info(f"Repaired memory file. Backup saved at {backup_path}.")
        return True
    except Exception as e:
        log.critical(f"Unexpected error repairing {file_path}: {e}")
        return False 