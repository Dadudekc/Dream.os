"""
Interface for logging agents.
"""

from abc import ABC, abstractmethod

class ILoggingAgent(ABC):
    """Base interface for logging agents."""
    
    @abstractmethod
    def log(self, message: str, domain: str = "General", level: str = "INFO") -> None:
        """
        Logs a simple text message.
        
        Args:
            message: The message to log
            domain: The logging domain
            level: The log level
        """
        pass

    @abstractmethod
    def log_error(self, message: str, domain: str = "General") -> None:
        """
        Logs an error message.
        
        Args:
            message: The error message
            domain: The logging domain
        """
        pass

    @abstractmethod
    def log_debug(self, message: str, domain: str = "General") -> None:
        """
        Logs a debug message.
        
        Args:
            message: The debug message
            domain: The logging domain
        """
        pass

    @abstractmethod
    def log_event(self, event_name: str, payload: dict, domain: str = "General") -> None:
        """
        Logs structured event data.
        
        Args:
            event_name: Name of the event
            payload: Event data
            domain: The logging domain
        """
        pass

    @abstractmethod
    def log_system_event(self, domain: str, event: str, message: str) -> None:
        """
        Logs a system event.
        
        Args:
            domain: The logging domain
            event: The event name
            message: The event message
        """
        pass 