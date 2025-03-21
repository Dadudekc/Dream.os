import os
import json
import yaml
import logging
import threading
from typing import Optional, Union, Dict, Any
from .PathManager import PathManager

logger = logging.getLogger("file_manager")


class FileManager:
    """
    Unified file management system for ChatMate.
    Handles all file operations using PathManager for consistent directory structure.
    Supports JSON, YAML, and plain text formats with thread-safe operations.
    """

    def __init__(self):
        """Initialize FileManager using PathManager for directory structure."""
        self.path_manager = PathManager
        self.path_manager.ensure_directories()
        self.lock = threading.Lock()

    def save_response(self, content: str, prompt_type: str, chat_title: Optional[str] = None) -> Optional[str]:
        """
        Save a response with proper organization under outputs directory.
        
        Args:
            content: The content to save
            prompt_type: Type of prompt (e.g., 'dreamscape', 'content_ideas')
            chat_title: Optional chat title for better organization
        
        Returns:
            Path to saved file or None if failed
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine the appropriate subdirectory
        if chat_title:
            subdir = os.path.join(self.path_manager.cycles_dir, prompt_type, self.sanitize_filename(chat_title))
        else:
            subdir = os.path.join(self.path_manager.cycles_dir, prompt_type)
            
        os.makedirs(subdir, exist_ok=True)
        
        filename = f"response_{timestamp}.txt"
        filepath = os.path.join(subdir, filename)
        
        return self._save_file(content, filepath)

    def save_memory_state(self, content: Dict[str, Any], memory_type: str) -> Optional[str]:
        """Save memory state files in the memory directory."""
        filename = f"{memory_type}_state.json"
        filepath = os.path.join(self.path_manager.memory_dir, filename)
        return self._save_file(content, filepath, file_type="json")

    def save_log(self, content: str, log_type: str) -> Optional[str]:
        """Save log files in the logs directory."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{log_type}_{timestamp}.log"
        filepath = os.path.join(self.path_manager.logs_dir, filename)
        return self._save_file(content, filepath)

    def archive_file(self, source_path: str, archive_type: str) -> Optional[str]:
        """
        Archive a file by moving it to the appropriate archive directory.
        Creates a dated subdirectory structure.
        """
        from datetime import datetime
        date_str = datetime.now().strftime("%Y/%m")
        archive_dir = os.path.join(self.path_manager.outputs_dir, "archives", archive_type, date_str)
        os.makedirs(archive_dir, exist_ok=True)
        
        dest_path = os.path.join(archive_dir, os.path.basename(source_path))
        try:
            os.rename(source_path, dest_path)
            logger.info(f"Archived file: {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to archive file {source_path}: {e}")
            return None

    def _save_file(self, content: Union[str, Dict], filepath: str, file_type: str = "text") -> Optional[str]:
        """Internal method for thread-safe file saving."""
        with self.lock:
            try:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    if file_type == "json":
                        json.dump(content, f, indent=4, ensure_ascii=False)
                    elif file_type == "yaml":
                        yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
                    else:
                        f.write(str(content))
                
                logger.info(f"Saved file: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Failed to save file {filepath}: {e}")
                return None

    def load_file(self, filepath: str, file_type: str = "text") -> Optional[Union[str, Dict]]:
        """Thread-safe file loading with format detection."""
        with self.lock:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    if file_type == "json":
                        return json.load(f)
                    elif file_type == "yaml":
                        return yaml.safe_load(f)
                    else:
                        return f.read()
            except Exception as e:
                logger.error(f"Failed to load file {filepath}: {e}")
                return None

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Create a safe filename from the given string."""
        return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_").lower()
