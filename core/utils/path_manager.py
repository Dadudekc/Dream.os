"""
Path Manager Module

This module provides utilities for managing application paths and directories.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class PathManager:
    """Manages application paths and directories."""
    
    def __init__(self):
        """Initialize the path manager."""
        self.root_dir = self._find_project_root()
        self.memory_dir = self.root_dir / "memory"
        self.config_dir = self.root_dir / "config"
        self.logs_dir = self.root_dir / "logs"
        
        # Create required directories
        self._ensure_directories()
        
    def _find_project_root(self) -> Path:
        """Find the project root directory."""
        current_dir = Path.cwd()
        while current_dir.parent != current_dir:
            if (current_dir / "core").exists():
                logger.info(f"Project root detected at: {current_dir}")
                return current_dir
            current_dir = current_dir.parent
        return Path.cwd()
        
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        for directory in [self.memory_dir, self.config_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
    def get_memory_path(self) -> Path:
        """Get the memory directory path."""
        return self.memory_dir
        
    def get_config_path(self) -> Path:
        """Get the config directory path."""
        return self.config_dir
        
    def get_logs_path(self) -> Path:
        """Get the logs directory path."""
        return self.logs_dir
        
    def get_file_path(self, filename: str, directory: Optional[str] = None) -> Path:
        """
        Get the path for a file in a specific directory.
        
        Args:
            filename: Name of the file
            directory: Optional directory name (memory, config, logs)
            
        Returns:
            Path object for the file
        """
        if directory == "memory":
            return self.memory_dir / filename
        elif directory == "config":
            return self.config_dir / filename
        elif directory == "logs":
            return self.logs_dir / filename
        else:
            return self.root_dir / filename 