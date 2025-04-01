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
        """Load paths from config file and ensure required paths exist."""
        try:
            with open(self.config_path, "r") as f:
                self.paths = yaml.safe_load(f) or {}

            # Required default paths
            required_defaults = {
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
                "rate_limits": "cache/rate_limits",
                "resonance_models": "assets/resonance_models",  # 🤘 NEW: Meredith Tab
                "dreamscape_templates": "templates/dreamscape", # 🤘 Future-proof Dreamscape
                "message_templates": "templates/message_templates", # Added based on TemplateManager
                "discord_templates": "templates/discord_templates", # Added based on TemplateManager
                "dreamscape_memory": "memory/dreamscape"        # 🤘 Optional future key
            }

            # Auto-patch missing paths
            patched_keys = []
            for key, default in required_defaults.items():
                if key not in self.paths:
                    logger.warning(f"Missing path key '{key}', defaulting to: {default}")
                    self.paths[key] = default
                    patched_keys.append(key)

            # Convert to absolute paths
            project_root = Path(self.paths.get("project_root", ".")).resolve()
            # Make project_root absolute first
            self.paths["project_root"] = str(project_root)
            for key, path in self.paths.items():
                if key != "project_root":
                    # Check if already absolute (e.g., from previous run or manual config)
                    if not Path(path).is_absolute():
                        self.paths[key] = str(project_root / path)
                    # Else: keep the absolute path as is

            # Ensure directories exist
            for key, path_str in self.paths.items():
                if key != "project_root": # Don't try to mkdir the root
                    try:
                        os.makedirs(path_str, exist_ok=True)
                    except OSError as e:
                        # Handle potential errors if path points to a file or other issues
                        logger.error(f"Could not create directory {path_str} for key '{key}': {e}")

            # Auto-save patched config
            if patched_keys:
                # Prepare data for saving (use relative paths where possible based on project_root)
                save_data = {}
                for key, abs_path_str in self.paths.items():
                    if key == "project_root":
                        # Special handling or skip saving project_root if preferred?
                        # For simplicity, let's assume we save the relative path used in defaults
                        save_data[key] = required_defaults[key]
                    else:
                        try:
                            # Attempt to make relative to saved project_root
                            save_data[key] = str(Path(abs_path_str).relative_to(project_root))
                        except ValueError:
                            # Path is not within project root, save the absolute path
                            save_data[key] = abs_path_str
                with open(self.config_path, "w") as f:
                    yaml.dump(save_data, f, default_flow_style=False)
                    logger.info(f"✅ Auto-patched missing path keys into {self.config_path}: {', '.join(patched_keys)}")

        except Exception as e:
            logger.error(f"Failed to load paths config: {e}", exc_info=True) # Log traceback
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
