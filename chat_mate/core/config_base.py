import os
import json
import logging
from datetime import datetime, UTC
from collections import defaultdict
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigBase:
    """Base configuration class with shared functionality."""
    
    def __init__(self):
        self.env = os.environ
        # --- Initialize PathManager directly --- 
        from chat_mate.core.PathManager import PathManager
        self.path_manager = PathManager() # Assign the singleton instance immediately
        # -------------------------------------
        self._load_env() # Now load .env using the assigned path_manager
        
    def _load_env(self):
        """Load environment variables using a calculated project root."""
        try:
            # Calculate project root directly for this initial load
            # Assumes this file is always at chat_mate/core/config_base.py
            project_root = Path(__file__).resolve().parent.parent.parent 
            dotenv_path = project_root / ".env"
            
            if dotenv_path.exists():
                 load_dotenv(dotenv_path, override=False) # Load if exists, don't override existing env vars
                 logger.info(f"Loaded .env file from: {dotenv_path}") # Add confirmation log
            else:
                 # Use the calculated path in the warning
                 logger.warning(f".env file not found at calculated path: {dotenv_path}")
        except Exception as e:
            logger.error(f"Error loading .env file: {e}", exc_info=True)

    def get_env(self, key: str, default=None) -> str:
        """Get environment variable value."""
        return self.env.get(key, default)

    def _validate_required_keys(self, required_keys):
        """Validate required environment variables exist."""
        missing = [key for key in required_keys if not self.get_env(key)]
        if missing:
            logger.warning(f"Missing required env vars: {missing}")
            return False
        return True
