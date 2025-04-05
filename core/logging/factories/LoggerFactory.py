import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from core.logging.LoggingService import LoggingService
from core.bootstrap import get_bootstrap_paths

class LoggerFactory:
    """
    Factory class for creating standardized loggers across the application.
    Provides methods to create different types of loggers with consistent 
    configuration.
    """
    
    _loggers: Dict[str, LoggingService] = {}
    
    @classmethod
    def create_standard_logger(
        cls,
        name: str,
        level: int = logging.INFO,
        log_to_file: bool = False
    ) -> LoggingService:
        """
        Create or retrieve a standard logger with consistent formatting.
        
        Args:
            name: Logger name (typically module or component name)
            level: Logging level (default: INFO)
            log_to_file: Whether to log to a file as well as console
            
        Returns:
            LoggingService: The configured logger
        """
        # Return existing logger if already created
        if name in cls._loggers:
            return cls._loggers[name]
        
        # Determine log file path if needed
        log_file = None
        if log_to_file:
            paths = get_bootstrap_paths()
            log_dir = paths.get('logs', os.path.join(os.path.dirname(__file__), '..', '..', '..', 'outputs', 'logs'))
            log_file = os.path.join(log_dir, f"{name.lower().replace(' ', '_')}.log")
        
        # Create new logger
        logger = LoggingService(
            name=name,
            level=level,
            log_file=log_file
        )
        
        # Cache the logger
        cls._loggers[name] = logger
        
        if log_file:
            logger.info(f"Logging initialized at {log_file}")
        else:
            logger.info(f"Logging initialized for {name}")
            
        return logger
    
    @classmethod
    def create_module_logger(cls, module_name: str, level: int = logging.INFO) -> LoggingService:
        """
        Create a logger specifically for a module.
        
        Args:
            module_name: Name of the module
            level: Logging level
            
        Returns:
            LoggingService: The configured logger
        """
        return cls.create_standard_logger(f"module.{module_name}", level)
    
    @classmethod
    def create_agent_logger(cls, agent_name: str, level: int = logging.INFO) -> LoggingService:
        """
        Create a logger specifically for an agent.
        
        Args:
            agent_name: Name of the agent
            level: Logging level
            
        Returns:
            LoggingService: The configured logger
        """
        return cls.create_standard_logger(f"agent.{agent_name}", level, log_to_file=True)
    
    @classmethod
    def get_logger(cls, name: str) -> Optional[LoggingService]:
        """
        Retrieve an existing logger.
        
        Args:
            name: Logger name
            
        Returns:
            Optional[LoggingService]: The logger if it exists, None otherwise
        """
        return cls._loggers.get(name)

    @classmethod
    def apply_library_log_levels(cls, library_levels: Dict[str, int]):
        """
        Applies specific logging levels to library loggers to reduce noise.

        Args:
            library_levels: Dictionary mapping library logger names to logging levels.
        """
        for lib_name, level in library_levels.items():
            try:
                logging.getLogger(lib_name).setLevel(level)
                # Use the root logger (or a dedicated factory logger) to log this action
                root_logger = cls._loggers.get("root") or logging.getLogger()
                root_logger.debug(f"Set level for library logger '{lib_name}' to {logging.getLevelName(level)}")
            except Exception as e:
                # Avoid crashing the app if setting a level fails
                root_logger = cls._loggers.get("root") or logging.getLogger()
                root_logger.error(f"Failed to set level for library logger '{lib_name}': {e}")
