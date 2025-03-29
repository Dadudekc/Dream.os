import json
from pathlib import Path
import shutil
import datetime
import logging

def repair_memory_files(memory_dir: str | Path, logger: logging.Logger = None) -> None:
    """
    Repair corrupted memory files by backing them up and replacing with empty JSON structure.
    
    Args:
        memory_dir: Directory containing memory files
        logger: Optional logger for tracking repairs
    """
    memory_dir = Path(memory_dir)
    empty_json = {}
    
    memory_files = [
        "feedback_memory.json",
        "chat_memory.json",
        "conversation_memory.json"
    ]
    
    for filename in memory_files:
        path = memory_dir / filename
        if path.exists():
            try:
                with path.open('r', encoding='utf-8') as f:
                    json.load(f)  # Try to parse
                if logger:
                    logger.info(f"✅ {filename} is valid JSON")
            except json.JSONDecodeError:
                if logger:
                    logger.warning(f"🔄 Fixing corrupted {filename}")
                timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                backup = path.with_name(f"{path.stem}_backup_{timestamp}.json")
                shutil.copy2(path, backup)
                
                with path.open('w', encoding='utf-8') as f:
                    json.dump(empty_json, f, indent=2)
                if logger:
                    logger.info(f"✅ Reset {filename} with empty structure")

def load_json_safe(path: str | Path, default: dict = None, logger: logging.Logger = None) -> dict:
    """
    Load a JSON file safely. If it's missing, empty, or corrupted, returns default and saves it.

    Args:
        path (str|Path): Path to the JSON file
        default (dict): Fallback data to use on failure
        logger (Logger): Optional logger

    Returns:
        dict: Loaded or fallback data
    """
    path = Path(path)
    default = default or {}

    try:
        if not path.exists() or path.stat().st_size == 0:
            raise ValueError("Missing or empty file")
        
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)

    except Exception as e:
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = path.parent / f"{path.stem}_backup_{timestamp}.json"

        if path.exists():
            try:
                shutil.copy(path, backup_path)
                if logger:
                    logger.warning(f"Backed up corrupted file to: {backup_path}")
            except Exception as backup_error:
                if logger:
                    logger.error(f"Failed to backup corrupt JSON: {backup_error}")

        try:
            with path.open('w', encoding='utf-8') as f:
                json.dump(default, f, indent=2)
            if logger:
                logger.info(f"Rewrote {path} with default structure.")
        except Exception as write_error:
            if logger:
                logger.error(f"Failed to rewrite corrupted JSON at {path}: {write_error}")

        return default
