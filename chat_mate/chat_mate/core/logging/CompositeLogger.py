from abc import ABC, abstractmethod
from typing import List, Dict, Any
from chat_mate.core.interfaces.ILoggingAgent import ILoggingAgent
from chat_mate.core.logging.utils.AsyncDispatcher import AsyncDispatcher
from chat_mate.core.logging.ConsoleLogger import ConsoleLogger
from chat_mate.core.FileLogger import FileLogger
from chat_mate.core.services.discord.DiscordLogger import DiscordLogger
from chat_mate.core.config.ConfigManager import ConfigManager
import logging

logger = logging.getLogger(__name__)

class CompositeLogger(ILoggingAgent):
    """Composite logger that manages multiple logging handlers."""
    
    def __init__(self, loggers: List[ILoggingAgent], config_manager: ConfigManager, fallback_logger: ILoggingAgent = None):
        self.loggers = loggers
        self.fallback_logger = fallback_logger or ConsoleLogger(config_manager)
        self.dispatcher = AsyncDispatcher()
        
    def _safe_log(self, logger: ILoggingAgent, method: str, *args: Any, **kwargs: Any) -> None:
        """Safely execute a logging method on a logger."""
        try:
            getattr(logger, method)(*args, **kwargs)
        except Exception as e:
            # Log error to fallback logger
            self.fallback_logger.log_error(f"Logger {logger.__class__.__name__} failed: {str(e)}")
            
    def log(self, message: str, domain: str = "General", level: str = "INFO") -> None:
        """Log a message to all registered loggers."""
        for logger in self.loggers:
            self.dispatcher.dispatch(self._safe_log, logger, "log", message, domain, level)
            
    def log_error(self, message: str, domain: str = "General") -> None:
        """Log an error to all registered loggers."""
        for logger in self.loggers:
            self.dispatcher.dispatch(self._safe_log, logger, "log_error", message, domain)
            
    def log_debug(self, message: str, domain: str = "General") -> None:
        """Log a debug message to all registered loggers."""
        for logger in self.loggers:
            self.dispatcher.dispatch(self._safe_log, logger, "log_debug", message, domain)
            
    def log_event(self, event_name: str, payload: dict, domain: str = "General") -> None:
        """Log an event to all registered loggers."""
        for logger in self.loggers:
            self.dispatcher.dispatch(self._safe_log, logger, "log_event", event_name, payload, domain)
            
    def log_system_event(self, domain: str, event: str, message: str) -> None:
        """Log a system event to all registered loggers."""
        for logger in self.loggers:
            self.dispatcher.dispatch(self._safe_log, logger, "log_system_event", domain, event, message)
            
    def add_logger(self, logger: ILoggingAgent) -> None:
        """Add a new logger to the composite."""
        self.loggers.append(logger)
        
    def remove_logger(self, logger: ILoggingAgent) -> None:
        """Remove a logger from the composite."""
        if logger in self.loggers:
            self.loggers.remove(logger)
            
    def shutdown(self) -> None:
        """Gracefully shutdown the composite logger."""
        self.dispatcher.shutdown() 