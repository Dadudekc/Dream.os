"""
AI Output Logging Service

This module provides functions for logging AI-generated outputs
while avoiding circular dependencies.
"""

import os
import json
import logging
import threading
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any

# Initialize logger
logger = logging.getLogger("ai_output_service")

# Module-level lock for thread-safe file access
write_lock = threading.Lock()

def log_ai_output(
    context: str,
    input_prompt: str,
    ai_output: str,
    base_log_dir: str,
    tags: Optional[List[str]] = None,
    result: Optional[str] = None,
    enable_reinforcement: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Core function to log AI output to a file.
    
    Args:
        context: String indicating which system or module generated the output
        input_prompt: The prompt used to generate the output
        ai_output: The AI's generated output
        base_log_dir: Base directory for storing log files
        tags: Optional list of tags for categorizing this log entry
        result: Optional result (e.g., "executed", "failed") for additional context
        enable_reinforcement: If True, triggers post-processing reinforcement logic
        metadata: Optional dictionary with additional metadata
        
    Returns:
        Optional[str]: Path to the saved log file if successful
    """
    if not tags:
        tags = []
    
    if not metadata:
        metadata = {}
    
    timestamp = datetime.now(UTC).isoformat()
    
    # Create sanitized filename
    timestamp_for_filename = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    sanitized_context = sanitize_filename(context)
    filename = f"{timestamp_for_filename}_{sanitized_context}.json"
    
    # Create output directory path
    log_dir = os.path.join(base_log_dir, sanitized_context)
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, filename)
    
    log_data = {
        "timestamp": timestamp,
        "context": context,
        "input_prompt": input_prompt,
        "ai_output": ai_output,
        "tags": tags,
        "result": result,
        "metadata": metadata
    }
    
    with write_lock:
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            logger.info(f"AI output logged to {log_file_path}")
            
            # Process for reinforcement if enabled - this will be handled at a higher level
            if enable_reinforcement:
                # Log that reinforcement would be triggered
                logger.info(f"Reinforcement learning triggered for {log_file_path}")
            
            return log_file_path
            
        except Exception as e:
            logger.error(f"Failed to log AI output: {e}")
            return None

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        filename: The string to sanitize
        
    Returns:
        str: A sanitized string that can be used as a filename
    """
    # Replace invalid characters with underscores
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length to prevent path length issues
    if len(filename) > 128:
        filename = filename[:128]
    
    return filename 