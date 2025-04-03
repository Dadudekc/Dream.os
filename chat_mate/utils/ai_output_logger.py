"""
AI Output Logger Wrapper

This module provides a wrapper around the core.logging.services.ai_output_service
to maintain backward compatibility while avoiding circular dependencies.
"""

import logging
from typing import Optional, List, Dict, Any
from chat_mate.core.PathManager import PathManager
# Import reinforcement trainer only if needed
from chat_mate.utils.reinforcement_trainer import process_feedback

# Import the core service
from chat_mate.core.logging.services.ai_output_service import log_ai_output as core_log_ai_output
from chat_mate.core.logging.services.ai_output_service import sanitize_filename

# Initialize the logger
logger = logging.getLogger("ai_output_logger")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# Get base log directory from PathManager
path_manager = PathManager()
BASE_LOG_DIR = path_manager.get_path('reinforcement_logs')

def log_ai_output(
    context: str,
    input_prompt: str,
    ai_output: str,
    tags: Optional[List[str]] = None,
    result: Optional[str] = None,
    enable_reinforcement: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Wrapper function to maintain backward compatibility with existing code.
    
    Args:
        context: String indicating which system or module generated the output
        input_prompt: The prompt used to generate the output
        ai_output: The AI's generated output
        tags: Optional list of tags for categorizing this log entry
        result: Optional result (e.g., "executed", "failed") for additional context
        enable_reinforcement: If True, triggers post-processing reinforcement logic
        metadata: Optional dictionary with additional metadata
        
    Returns:
        Optional[str]: Path to the saved log file if successful
    """
    log_file_path = core_log_ai_output(
        context=context,
        input_prompt=input_prompt,
        ai_output=ai_output,
        base_log_dir=BASE_LOG_DIR,
        tags=tags,
        result=result,
        enable_reinforcement=enable_reinforcement,
        metadata=metadata
    )
    
    # Handle reinforcement processing if needed
    if log_file_path and enable_reinforcement:
        try:
            process_feedback(log_file_path)
        except Exception as e:
            logger.error(f"Error in reinforcement processing: {e}")
    
    return log_file_path
