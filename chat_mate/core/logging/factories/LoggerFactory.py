from typing import List, Optional
from core.ConfigManager import ConfigManager
from core.interfaces.ILoggingAgent import ILoggingAgent
from core.ConsoleLogger import ConsoleLogger
from core.FileLogger import FileLogger
from core.DiscordLogger import DiscordLogger
from core.logging.CompositeLogger import CompositeLogger

class LoggerFactory:
    """Factory class for creating different types of loggers."""
    
    @staticmethod
    def create_logger(config_manager: ConfigManager) -> ILoggingAgent:
        """
        Create a logger instance based on configuration.
        
        Args:
            config_manager: ConfigManager instance for configuration access
            
        Returns:
            ILoggingAgent: Configured logger instance
            
        Raises:
            ValueError: If logger type is invalid
        """
        logger_config = config_manager.get('logging', {})
        logger_types = logger_config.get('types', ['console'])
        
        if not isinstance(logger_types, list):
            logger_types = [logger_types]
            
        loggers: List[ILoggingAgent] = []
        
        for logger_type in logger_types:
            try:
                if logger_type == 'console':
                    loggers.append(ConsoleLogger(config_manager))
                elif logger_type == 'file':
                    loggers.append(FileLogger(config_manager))
                elif logger_type == 'discord':
                    loggers.append(DiscordLogger(config_manager))
                else:
                    raise ValueError(f"Invalid logger type: {logger_type}")
            except Exception as e:
                # Log error but continue with other loggers
                print(f"Failed to initialize logger {logger_type}: {str(e)}")
                
        if not loggers:
            # Fallback to console logger if no loggers were created
            return ConsoleLogger(config_manager)
            
        # Create composite logger with all successfully initialized loggers
        return CompositeLogger(loggers) 