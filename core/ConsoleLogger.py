from typing import Optional
from datetime import datetime
from core.config.config_manager import ConfigManager
from interfaces.pyqt.ILoggingAgent import ILoggingAgent

class ConsoleLogger(ILoggingAgent):
    """Logger implementation for console output."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.debug_mode = config_manager.get('logging.debug_mode', False)
        
    def log(self, message: str, domain: str = "General", level: str = "INFO") -> None:
        """Log a message to console with domain and level."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] [{domain}] {message}"
        print(log_line)
        
    def log_error(self, message: str, domain: str = "General") -> None:
        """Log an error message."""
        self.log(message, domain=domain, level="ERROR")
        
    def log_debug(self, message: str, domain: str = "General") -> None:
        """Log a debug message if debug mode is enabled."""
        if self.debug_mode:
            self.log(message, domain=domain, level="DEBUG")
            
    def log_event(self, event_name: str, payload: dict, domain: str = "General") -> None:
        """Log a structured event."""
        event_message = f"{event_name} - {payload}"
        self.log(event_message, domain=domain, level="EVENT")
        
    def log_system_event(self, domain: str, event: str, message: str) -> None:
        """Log a system event."""
        event_message = f"{event} - {message}"
        self.log(event_message, domain=domain, level="SYSTEM") 
