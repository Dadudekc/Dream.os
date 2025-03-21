import os
import json
import threading
from datetime import datetime, UTC
import logging
from utils.reinforcement_trainer import process_feedback
from core.FileManager import FileManager
from core.PathManager import PathManager
from core.UnifiedLoggingAgent import UnifiedLoggingAgent
from typing import Optional, List

# Initialize the unified logger
_unified_logger = UnifiedLoggingAgent()
logger = logging.getLogger("ai_output_logger")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# Module-level lock for thread-safe file access
write_lock = threading.Lock()
file_manager = FileManager()

def log_ai_output(
    context: str,
    input_prompt: str,
    ai_output: str,
    tags: Optional[List[str]] = None,
    result: Optional[str] = None,
    enable_reinforcement: bool = True
) -> Optional[str]:
    """
    Log AI output using the UnifiedLoggingAgent.
    Maintains backward compatibility with existing code.
    
    Args:
        context: String indicating which system or module generated the output
        input_prompt: The prompt used to generate the output
        ai_output: The AI's generated output
        tags: Optional list of tags for categorizing this log entry
        result: Optional result (e.g., "executed", "failed") for additional context
        enable_reinforcement: If True, triggers post-processing reinforcement logic
        
    Returns:
        Optional[str]: Path to the saved log file if successful
    """
    return _unified_logger.log_ai_output(
        context=context,
        input_prompt=input_prompt,
        ai_output=ai_output,
        tags=tags,
        result=result,
        enable_reinforcement=enable_reinforcement
    )
