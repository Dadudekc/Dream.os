import os
import json
import logging
from datetime import datetime, UTC
from collections import defaultdict
from dotenv import load_dotenv
from core.PathManager import PathManager

logger = logging.getLogger(__name__)

class ConfigBase:
    """Base configuration class with shared functionality."""
    
    def __init__(self):
        self.env = os.environ
        self.path_manager = PathManager()
        self._load_env()
        
    def _load_env(self):
        """Load environment variables."""
        dotenv_path = self.path_manager.get_env_path(".env")
        load_dotenv(dotenv_path)
        
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
