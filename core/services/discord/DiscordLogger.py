from typing import Optional
from chat_mate.core.interfaces.ILoggingAgent import ILoggingAgent
from .DiscordManager import DiscordManager

class DiscordLogger(ILoggingAgent):
    """Logs messages to Discord using a DiscordManager instance."""
    
    def __init__(self, discord_manager: DiscordManager):
        """
        Initializes the DiscordLogger.

        Args:
            discord_manager: An initialized DiscordManager instance.
        """
        self.discord_manager = discord_manager
    
    def log(self, message: str, domain: str = "General", level: str = "INFO") -> None:
        """Logs a message to Discord via DiscordManager."""
        formatted_message = f"**[{level.upper()}]** *({domain})*\\n{message}"
        self.discord_manager.send_message(prompt_type=domain, message=formatted_message)
        
    def log_error(self, message: str, domain: str = "General") -> None:
        """Logs an error message to Discord."""
        formatted_message = f"**[ERROR]** *({domain})*\\n🚨 {message}"
        self.discord_manager.send_message(prompt_type=domain, message=formatted_message)
        
    def log_debug(self, message: str, domain: str = "General") -> None:
        """Logs a debug message to Discord."""
        formatted_message = f"**[DEBUG]** *({domain})*\\n🐛 {message}"
        self.discord_manager.send_message(prompt_type=domain, message=formatted_message)
        
    def log_event(self, event_name: str, payload: dict, domain: str = "General") -> None:
        """Logs an event to Discord."""
        payload_str = "\\n".join([f"- `{k}`: `{v}`" for k, v in payload.items()])
        formatted_message = f"**[EVENT: {event_name.upper()}]** *({domain})*\\n{payload_str}"
        self.discord_manager.send_message(prompt_type=domain, message=formatted_message)
        
    def log_system_event(self, domain: str, event: str, message: str) -> None:
        """Logs a system event to Discord."""
        formatted_message = f"**[SYSTEM: {event.upper()}]** *({domain})*\\n⚙️ {message}"
        self.discord_manager.send_message(prompt_type=domain, message=formatted_message)
