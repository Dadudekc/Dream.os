import os
import json
import logging
from datetime import datetime, UTC
from collections import defaultdict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigBase:
    """Base configuration class with shared functionality."""
    
    def __init__(self):
        self.env = os.environ
        self.path_manager = None  # Will be set after importing PathManager
        self._load_env()
        self._init_path_manager()
        
    def _load_env(self):
        """Load environment variables."""
        # Access base path via PathManager after initialization
        # dotenv_path = _PathRegistry._paths.get('base', os.getcwd()) / ".env"
        # load_dotenv(dotenv_path) # Loading handled earlier or differently?
        # Revisit env loading if needed, PathManager requires bootstrap paths first
        pass # Assuming .env is loaded earlier in bootstrap
        
    def _init_path_manager(self):
        """Initialize PathManager after other imports are done."""
        # Import PathManager here to avoid circular dependency issues
        from chat_mate.core.PathManager import PathManager
        self.path_manager = PathManager() # Assign the singleton instance
        # Ensure .env loading logic doesn't conflict
        dotenv_path = self.path_manager.get_path('base') / ".env"
        if dotenv_path.exists():
             load_dotenv(dotenv_path, override=False) # Load if exists, don't override existing env vars
        else:
             logger.warning(f".env file not found at {dotenv_path}")

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
