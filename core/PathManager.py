#!/usr/bin/env python3
"""
PathManager.py

Manages paths for the Dream.OS application.
"""

import os
import logging
import yaml
from pathlib import Path
from typing import Dict, Optional, Union

logger = logging.getLogger(__name__)

class PathManager:
    """Manages paths for the Dream.OS application."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the path manager.
        
        Args:
            config_path: Optional path to the config file. If not provided,
                        will look in default locations.
        """
        self.paths = {}
        self.config_path = config_path or self._find_config()
        self._load_config()
        
    def _find_config(self) -> str:
        """
        Find the paths config file.
        
        Returns:
            str: Path to the config file
        """
        possible_locations = [
            Path("config/paths.yml"),
            Path("../config/paths.yml"),
            Path(__file__).parent.parent / "config" / "paths.yml"
        ]
        
        for location in possible_locations:
            if location.exists():
                return str(location)
                
        # If no config found, use default paths relative to project root
        default_config = {
            "project_root": ".",
            "templates": "templates",
            "cache": "cache",
            "logs": "logs",
            "metrics": "metrics",
            "outputs": "outputs",
            "episodes": "episodes",
            "memory": "memory",
            "assets": "assets",
            "reports": "reports",
            "tests": "tests",
            "reinforcement_logs": "logs/reinforcement",
            "social_logs": "logs/social",
            "utils_logs": "logs/utils",
            "rate_limits": "cache/rate_limits"
        }
        
        # Create config directory if it doesn't exist
        os.makedirs("config", exist_ok=True)
        
        # Write default config
        with open("config/paths.yml", "w") as f:
            yaml.dump(default_config, f)
            
        return "config/paths.yml"
        
    def _load_config(self):
        """Load paths from config file."""
        try:
            with open(self.config_path, "r") as f:
                self.paths = yaml.safe_load(f)
                
            # Convert relative paths to absolute
            project_root = Path(self.paths.get("project_root", ".")).resolve()
            for key, path in self.paths.items():
                if key != "project_root":
                    self.paths[key] = str(project_root / path)
                    
            # Ensure directories exist
            for path in self.paths.values():
                os.makedirs(path, exist_ok=True)
                
        except Exception as e:
            logger.error(f"Failed to load paths config: {e}")
            raise
            
    def get_path(self, key: str) -> str:
        """
        Get a path by key.
        
        Args:
            key: The path key from the config
            
        Returns:
            str: The resolved path
            
        Raises:
            KeyError: If the path key is not found
        """
        if key not in self.paths:
            logger.warning(f"Path key '{key}' not found.")
            raise KeyError(f"Path key '{key}' not found.")
            
        return self.paths[key]
        
    def get_all_paths(self) -> Dict[str, str]:
        """
        Get all configured paths.
        
        Returns:
            Dict[str, str]: Mapping of path keys to paths
        """
        return self.paths.copy()
        
    def get_env_path(self, filename: str = ".env") -> Union[str, Path]:
        """
        Get the path to the environment file.
        
        Args:
            filename: Name of the environment file
            
        Returns:
            Union[str, Path]: Path to the environment file
        """
        project_root = Path(self.paths["project_root"])
        return project_root / filename
        
    def get_relative_path(self, key: str, *paths: str) -> Path:
        """
        Get a path relative to a registered base path.
        
        Args:
            key: The base path key
            *paths: Additional path components
            
        Returns:
            Path: The combined path
        """
        base = Path(self.get_path(key))
        return base.joinpath(*paths)
        
    def get_rate_limit_state_path(self, filename: str = "rate_limit_state.json") -> Path:
        """
        Get the path to the rate limit state file.
        
        Args:
            filename: Name of the rate limit state file
            
        Returns:
            Path: Path to the rate limit state file
        """
        return Path(self.get_path("rate_limits")) / filename
