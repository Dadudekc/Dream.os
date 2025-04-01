"""
Memory Utilities

This module provides utility functions for memory management, including file operations,
validation, and repair functions.
"""

import os
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def load_memory_file(file_path: str, default_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load and validate a memory file, with backup and repair functionality.
    
    Args:
        file_path: Path to the memory file.
        default_data: Default data structure to use if file is invalid or missing.
        
    Returns:
        Dictionary containing the memory data.
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
            return data
        else:
            # Create new file with default data
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(default_data, f, indent=2)
            return default_data
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {file_path}, attempting repair")
        return repair_memory_file(file_path, default_data)
    except Exception as e:
        logger.error(f"Error loading memory file {file_path}: {e}")
        return default_data

def repair_memory_file(file_path: str, default_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attempt to repair a corrupted memory file.
    
    Args:
        file_path: Path to the corrupted file.
        default_data: Default data to use if repair fails.
        
    Returns:
        Dictionary containing the repaired or default data.
    """
    try:
        # Create backup
        backup_path = create_backup(file_path)
        logger.info(f"Created backup at {backup_path}")

        # Try to repair JSON
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Basic JSON repair attempts
        content = content.strip()
        if not content.startswith('{'):
            content = '{' + content
        if not content.endswith('}'):
            content = content + '}'
        
        # Try to parse repaired content
        try:
            data = json.loads(content)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully repaired {file_path}")
            return data
        except:
            logger.warning(f"Could not repair {file_path}, using default data")
            with open(file_path, 'w') as f:
                json.dump(default_data, f, indent=2)
            return default_data
    except Exception as e:
        logger.error(f"Error during repair of {file_path}: {e}")
        return default_data

def create_backup(file_path: str) -> str:
    """
    Create a backup of a file with timestamp.
    
    Args:
        file_path: Path to the file to backup.
        
    Returns:
        Path to the backup file.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{file_path}_backup_{timestamp}"
    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup of {file_path}: {e}")
        return ""

def fix_memory_file(file_path: str) -> bool:
    """
    Fix a memory file by removing invalid entries.
    
    Args:
        file_path: Path to the file to fix.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        # Create backup first
        backup_path = create_backup(file_path)
        if not backup_path:
            return False

        # Read and parse file
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Remove null or invalid entries
        if isinstance(data, dict):
            data = {k: v for k, v in data.items() if v is not None}
        elif isinstance(data, list):
            data = [item for item in data if item is not None]

        # Save cleaned data
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        return True
    except Exception as e:
        logger.error(f"Failed to fix memory file {file_path}: {e}")
        return False

def merge_memory_files(source_path: str, target_path: str) -> bool:
    """
    Merge two memory files, preserving unique entries.
    
    Args:
        source_path: Path to the source memory file.
        target_path: Path to the target memory file.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        # Load both files
        with open(source_path, 'r') as f:
            source_data = json.load(f)
        with open(target_path, 'r') as f:
            target_data = json.load(f)

        # Merge based on data type
        if isinstance(source_data, dict) and isinstance(target_data, dict):
            merged_data = {**target_data, **source_data}  # Source overwrites target
        elif isinstance(source_data, list) and isinstance(target_data, list):
            # Merge lists, removing duplicates
            merged_data = target_data.copy()
            for item in source_data:
                if item not in merged_data:
                    merged_data.append(item)
        else:
            logger.error("Incompatible memory file formats")
            return False

        # Save merged data
        with open(target_path, 'w') as f:
            json.dump(merged_data, f, indent=2)

        return True
    except Exception as e:
        logger.error(f"Failed to merge memory files: {e}")
        return False

def validate_memory_structure(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate memory data against a schema.
    
    Args:
        data: Memory data to validate.
        schema: Schema to validate against.
        
    Returns:
        True if valid, False otherwise.
    """
    try:
        def _validate_type(value: Any, expected_type: str) -> bool:
            if expected_type == "string":
                return isinstance(value, str)
            elif expected_type == "number":
                return isinstance(value, (int, float))
            elif expected_type == "boolean":
                return isinstance(value, bool)
            elif expected_type == "array":
                return isinstance(value, list)
            elif expected_type == "object":
                return isinstance(value, dict)
            return False

        def _validate_object(obj: Dict[str, Any], obj_schema: Dict[str, Any]) -> bool:
            # Check required fields
            required = obj_schema.get("required", [])
            for field in required:
                if field not in obj:
                    logger.error(f"Missing required field: {field}")
                    return False

            # Validate each field
            properties = obj_schema.get("properties", {})
            for field, value in obj.items():
                if field in properties:
                    field_schema = properties[field]
                    if not _validate_type(value, field_schema.get("type")):
                        logger.error(f"Invalid type for field {field}")
                        return False

                    # Recursive validation for objects
                    if field_schema.get("type") == "object" and isinstance(value, dict):
                        if not _validate_object(value, field_schema):
                            return False

            return True

        return _validate_object(data, schema)
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return False 