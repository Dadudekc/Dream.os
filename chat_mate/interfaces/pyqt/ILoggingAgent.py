from abc import ABC, abstractmethod

class ILoggingAgent(ABC):
    @abstractmethod
    def log(self, message: str) -> None:
        """
        Logs a simple text message.
        """
        pass

    @abstractmethod
    def log_error(self, message: str) -> None:
        """
        Logs an error message.
        """
        pass

    @abstractmethod
    def log_debug(self, message: str) -> None:
        """
        Logs a debug message.
        """
        pass

    @abstractmethod
    def log_event(self, event_name: str, payload: dict) -> None:
        """
        Logs structured event data.
        """
        pass
