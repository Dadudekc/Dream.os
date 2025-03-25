import os
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class PathManager:
    """
    Centralized path management for the application.
    Handles path resolution and ensures consistent access across modules.
    """
    
    _instance = None
    _paths = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PathManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize path mappings."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Core paths
        self._paths = {
            'base': base_dir,
            'data': os.path.join(base_dir, 'data'),
            'logs': os.path.join(base_dir, 'outputs', 'logs'),
            'outputs': os.path.join(base_dir, 'outputs'),
            'config': os.path.join(base_dir, 'config'),
            'configs': os.path.join(base_dir, 'configs'),
            'cache': os.path.join(base_dir, 'cache'),
            'memory': os.path.join(base_dir, 'memory'),
            'templates': os.path.join(base_dir, 'templates'),
            'drivers': os.path.join(base_dir, 'drivers'),
            
            # Output subdirectories
            'cycles': os.path.join(base_dir, 'outputs', 'cycles'),
            'dreamscape': os.path.join(base_dir, 'outputs', 'cycles', 'dreamscape'),
            'workflow_audits': os.path.join(base_dir, 'outputs', 'cycles', 'workflow_audits'),
            'discord_exports': os.path.join(base_dir, 'outputs', 'discord_exports'),
            'reinforcement_logs': os.path.join(base_dir, 'outputs', 'reinforcement_logs'),
            
            # Template subdirectories
            'discord_templates': os.path.join(base_dir, 'templates', 'discord_templates'),
            'message_templates': os.path.join(base_dir, 'templates', 'message_templates'),
            'engagement_templates': os.path.join(base_dir, 'templates', 'engagement_templates'),
            'report_templates': os.path.join(base_dir, 'templates', 'report_templates'),
            
            # Social paths
            'strategies': os.path.join(base_dir, 'chat_mate', 'social', 'strategies'),
            'context_db': os.path.join(base_dir, 'chat_mate', 'social', 'strategies', 'context_db.json'),
        }
        
        # Create directories if they don't exist
        for path in self._paths.values():
            if not os.path.exists(path) and not path.endswith('.json'):
                os.makedirs(path, exist_ok=True)
                
        logger.info(f"Bootstrap: Registered paths: {self._paths}")
    
    @classmethod
    def get_path(cls, key: str) -> str:
        """Get a registered path by key."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance._paths.get(key, '')
    
    @classmethod
    def get_env_path(cls, filename: str) -> str:
        """Get the path to an environment file."""
        if cls._instance is None:
            cls._instance = cls()
        return os.path.join(cls._instance._paths['base'], filename)
    
    def get_rate_limit_state_path(self) -> str:
        """Get the path to the rate limit state file."""
        return os.path.join(self._paths['data'], 'rate_limit_state.json')
    
    def get_chrome_profile_path(self) -> str:
        """Get the path to the Chrome profile directory."""
        return os.path.join(self._paths['data'], 'chrome_profile') 