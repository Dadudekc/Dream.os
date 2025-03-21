from PyQt5.QtCore import QObject, pyqtSignal
from core.UnifiedDiscordService import UnifiedDiscordService

class DiscordService(QObject):
    """
    Service layer for Discord integration.
    Provides a Qt-friendly interface to the UnifiedDiscordService.
    """
    
    log_message = pyqtSignal(str)
    status_changed = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.discord = None
        
    def launch_bot(self, token: str, channel_id: str) -> None:
        """
        Launch the Discord bot with the given credentials.
        
        Args:
            token: Discord bot token
            channel_id: Default channel ID
        """
        if self.discord and self.discord.is_running:
            self.log_message.emit("Discord bot is already running.")
            return
            
        try:
            self.discord = UnifiedDiscordService(
                bot_token=token,
                default_channel_id=channel_id
            )
            
            # Set up logging callback
            self.discord.set_log_callback(self.log_message.emit)
            
            # Start the bot
            self.discord.run()
            
            self.status_changed.emit(True)
            self.log_message.emit("Discord bot launched successfully.")
            
        except Exception as e:
            self.log_message.emit(f"Error launching bot: {str(e)}")
            self.status_changed.emit(False)
            
    def stop_bot(self) -> None:
        """Stop the Discord bot if it's running."""
        if not self.discord or not self.discord.is_running:
            self.log_message.emit("Discord bot is not running.")
            return
            
        try:
            self.discord.stop()
            self.status_changed.emit(False)
            self.log_message.emit("Discord bot stopped successfully.")
        except Exception as e:
            self.log_message.emit(f"Error stopping bot: {str(e)}")
            
    def send_message(self, channel_id: str, message: str) -> bool:
        """
        Send a message through Discord.
        
        Args:
            channel_id: Target channel ID
            message: Message content to send
            
        Returns:
            bool: True if message was queued successfully
        """
        if not self.discord or not self.discord.is_running:
            self.log_message.emit("Discord bot is not running.")
            return False
            
        try:
            self.discord.send_message(message, int(channel_id))
            return True
        except Exception as e:
            self.log_message.emit(f"Error sending message: {str(e)}")
            return False
            
    def send_file(self, channel_id: str, file_path: str, content: str = "") -> bool:
        """
        Send a file through Discord.
        
        Args:
            channel_id: Target channel ID
            file_path: Path to the file to send
            content: Optional message to send with the file
            
        Returns:
            bool: True if file was queued successfully
        """
        if not self.discord or not self.discord.is_running:
            self.log_message.emit("Discord bot is not running.")
            return False
            
        try:
            self.discord.send_file(file_path, content, int(channel_id))
            return True
        except Exception as e:
            self.log_message.emit(f"Error sending file: {str(e)}")
            return False
            
    def send_template(self, template_name: str, context: dict, channel_id: str = None) -> bool:
        """
        Send a templated message through Discord.
        
        Args:
            template_name: Name of the template to use
            context: Dictionary of context variables for the template
            channel_id: Optional target channel ID
            
        Returns:
            bool: True if message was queued successfully
        """
        if not self.discord or not self.discord.is_running:
            self.log_message.emit("Discord bot is not running.")
            return False
            
        try:
            self.discord.send_template(
                template_name, 
                context, 
                int(channel_id) if channel_id else None
            )
            return True
        except Exception as e:
            self.log_message.emit(f"Error sending template: {str(e)}")
            return False
            
    def get_status(self) -> dict:
        """Get current bot status information."""
        if not self.discord:
            return {
                "is_running": False,
                "message": "Bot not initialized"
            }
            
        return self.discord.get_status()
            
    def is_running(self) -> bool:
        """Check if the Discord bot is running."""
        return bool(self.discord and self.discord.is_running) 