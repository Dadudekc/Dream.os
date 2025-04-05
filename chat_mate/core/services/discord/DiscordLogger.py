from typing import Optional, Dict, Any
from chat_mate.core.config.ConfigManager import ConfigManager
from chat_mate.core.interfaces.ILoggingAgent import ILoggingAgent
import logging

logger = logging.getLogger(__name__)

class DiscordLogger(ILoggingAgent):
    """Discord-based logging implementation that sends log messages to Discord channels."""
    
    def __init__(self, discord_manager):
        """
        Initialize the Discord logger with a discord manager.
        
        Args:
            discord_manager: The Discord manager instance used to send messages to Discord
        """
        self.discord_manager = discord_manager
        self.enabled = True
        self.log_levels = {
            "DEBUG": "debug",
            "INFO": "info",
            "WARNING": "warning", 
            "ERROR": "error",
            "CRITICAL": "critical"
        }
        logger.info("DiscordLogger initialized")
        
    def _format_message(self, message: str, domain: str = "General", level: str = "INFO") -> str:
        """Format a message with appropriate emoji and structure for Discord."""
        level_emoji = {
            "DEBUG": "🔍",
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🚨"
        }
        
        emoji = level_emoji.get(level, "ℹ️")
        return f"{emoji} **[{domain}]** [{level}]: {message}"
        
    def log(self, message: str, domain: str = "General", level: str = "INFO") -> None:
        """
        Log a message to Discord.
        
        Args:
            message: The message to log
            domain: The domain/category of the log
            level: Log level (INFO, ERROR, etc.)
        """
        if not self.enabled:
            return
            
        formatted_message = self._format_message(message, domain, level)
        prompt_type = f"log_{self.log_levels.get(level, 'info')}"
        try:
            self.discord_manager.send_message(prompt_type, formatted_message)
            logger.debug(f"Discord log sent: {formatted_message}")
        except Exception as e:
            logger.error(f"Error sending Discord log: {e}")
        
    def log_error(self, message: str, domain: str = "General") -> None:
        """
        Log an error message to Discord.
        
        Args:
            message: The error message
            domain: The domain/category of the log
        """
        self.log(message, domain, "ERROR")
        
    def log_debug(self, message: str, domain: str = "General") -> None:
        """
        Log a debug message to Discord.
        
        Args:
            message: The debug message
            domain: The domain/category of the log
        """
        self.log(message, domain, "DEBUG")
        
    def log_event(self, event_name: str, payload: dict, domain: str = "General") -> None:
        """
        Log an event to Discord with structured payload data.
        
        Args:
            event_name: Name of the event
            payload: Event data dictionary
            domain: The domain/category of the log
        """
        if not self.enabled:
            return
            
        try:
            # Format payload as a Discord code block
            formatted_payload = "\n".join([f"- **{k}**: {v}" for k, v in payload.items()])
            message = f"🎭 **Event: {event_name}** [Domain: {domain}]\n```\n{formatted_payload}\n```"
            
            self.discord_manager.send_event_notification(event_name, {
                "domain": domain,
                "payload": payload,
                "formatted_message": message
            })
        except Exception as e:
            logger.error(f"Error sending Discord event log: {e}")
        
    def log_system_event(self, domain: str, event: str, message: str) -> None:
        """
        Log a system event to Discord.
        
        Args:
            domain: The system domain
            event: The event type/name
            message: The event message
        """
        if not self.enabled:
            return
            
        try:
            formatted_message = f"🔧 **System Event** [Domain: {domain}]\n**Event**: {event}\n**Message**: {message}"
            self.discord_manager.send_message("log_system", formatted_message)
        except Exception as e:
            logger.error(f"Error sending Discord system event log: {e}")
            
    def enable(self) -> None:
        """Enable Discord logging."""
        self.enabled = True
        logger.info("Discord logging enabled")
        
    def disable(self) -> None:
        """Disable Discord logging."""
        self.enabled = False
        logger.info("Discord logging disabled")
