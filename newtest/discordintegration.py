# discord_integration.py

import os
import json
import asyncio
import logging
import threading
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

import discord
from discord.ext import commands

# PyQt5 imports for the Qt wrapper
from PyQt5.QtCore import QObject, pyqtSignal

# Configure logger
logger = logging.getLogger("UnifiedDiscordService")
logger.setLevel(logging.INFO)

###########################################################################
# Unified Discord Service
###########################################################################

class UnifiedDiscordService:
    """
    UnifiedDiscordService - Centralized Discord integration service.
    Handles all Discord-related functionality including:
      - Bot lifecycle management
      - Message dispatching
      - Template rendering
      - Channel management
      - Status monitoring
      - Event notifications
    """

    CONFIG_FILE = "discord_service_config.json"

    def __init__(self, 
                 bot_token: str = None, 
                 default_channel_id=None,
                 template_dir: str = "templates/discord"):
        """
        Initialize UnifiedDiscordService.
        
        Args:
            bot_token: Discord Bot Token (optional, loaded from config if not provided)
            default_channel_id: Default Channel ID (optional, loaded from config if not provided)
            template_dir: Directory containing Discord message templates
        """
        # Core state
        self.is_running: bool = False
        self.start_time = None
        self._lock = threading.Lock()
        
        # Configuration (with defaults)
        self.config = {
            "bot_token": bot_token or "",
            "default_channel_id": int(default_channel_id) if default_channel_id else 0,
            "channel_mappings": {},
            "allowed_roles": [],
            "auto_responses": {}
        }
        
        # Load existing config if available
        self.load_config()
        
        # Initialize template engine
        self.template_env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Message queue for async dispatch
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Set up Discord bot with necessary intents
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Register event handlers
        self._register_events()
        
        # External logging callback (can be set by a wrapper)
        self.log_callback = None
        
        logger.info("UnifiedDiscordService initialized")

    def _register_events(self) -> None:
        """Register Discord bot event handlers."""
        @self.bot.event
        async def on_ready():
            self._log(f"✅ Discord Bot connected as {self.bot.user}")
            self.is_running = True
            self.start_time = datetime.utcnow()

        @self.bot.event
        async def on_message(message):
            # Avoid self-response
            if message.author == self.bot.user:
                return
                
            # Handle auto-responses if configured for the channel
            channel_id = str(message.channel.id)
            if channel_id in self.config.get("auto_responses", {}):
                response = self.config["auto_responses"][channel_id]
                await message.channel.send(response)
                
            # Process commands if any
            await self.bot.process_commands(message)

    # ----------------------------------------
    # Configuration Management
    # ----------------------------------------
    def load_config(self) -> None:
        """Load configuration from file."""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
                self._log("✅ Loaded configuration from file")
            except Exception as e:
                self._log(f"❌ Failed to load config: {e}", level=logging.ERROR)

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            self._log("💾 Saved configuration to file")
        except Exception as e:
            self._log(f"❌ Failed to save config: {e}", level=logging.ERROR)

    # ----------------------------------------
    # Bot Lifecycle Management
    # ----------------------------------------
    def run(self) -> None:
        """Start the Discord bot in a separate thread."""
        if self.is_running:
            self._log("⚠️ Bot is already running", level=logging.WARNING)
            return
            
        if not self.config["bot_token"]:
            self._log("❌ Bot token not configured", level=logging.ERROR)
            return
            
        def run_bot():
            try:
                asyncio.run(self._start_bot())
            except Exception as e:
                self._log(f"❌ Bot error: {e}", level=logging.ERROR)
                self.is_running = False
                
        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()
        self._log("🚀 Bot started in background thread")

    async def _start_bot(self) -> None:
        """Internal coroutine to start the bot and message dispatcher."""
        try:
            # Start message dispatcher
            self.bot.loop.create_task(self._process_message_queue())
            # Start bot
            await self.bot.start(self.config["bot_token"])
        except Exception as e:
            self._log(f"❌ Failed to start bot: {e}", level=logging.ERROR)
            raise

    def stop(self) -> None:
        """Stop the Discord bot."""
        if not self.is_running:
            self._log("⚠️ Bot is not running", level=logging.WARNING)
            return
            
        try:
            if self.bot.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self.bot.close(), self.bot.loop)
                future.result(timeout=10)
            self.is_running = False
            self.start_time = None
            self._log("✅ Bot stopped successfully")
        except Exception as e:
            self._log(f"❌ Failed to stop bot: {e}", level=logging.ERROR)

    # ----------------------------------------
    # Message Handling
    # ----------------------------------------
    async def _process_message_queue(self) -> None:
        """Process messages from the queue and send them to Discord."""
        while True:
            try:
                msg_data = await self.message_queue.get()
                channel_id = msg_data.get("channel_id", self.config["default_channel_id"])
                content = msg_data.get("content", "")
                file_path = msg_data.get("file_path")
                
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    self._log(f"❌ Channel {channel_id} not found", level=logging.ERROR)
                    continue
                    
                if file_path:
                    if os.path.exists(file_path):
                        await channel.send(content=content, file=discord.File(file_path))
                        self._log(f"📤 Sent file to channel {channel_id}")
                    else:
                        self._log(f"❌ File not found: {file_path}", level=logging.ERROR)
                else:
                    await channel.send(content)
                    self._log(f"📤 Sent message to channel {channel_id}")
                    
            except Exception as e:
                self._log(f"❌ Error processing message: {e}", level=logging.ERROR)

    def send_message(self, content: str, channel_id: int = None) -> None:
        """
        Queue a message to be sent to Discord.
        
        Args:
            content: The message content to send.
            channel_id: Optional channel ID (uses default if not specified).
        """
        if not self.is_running:
            self._log("⚠️ Bot is not running", level=logging.WARNING)
            return
            
        msg_data = {
            "channel_id": channel_id or self.config["default_channel_id"],
            "content": content
        }
        asyncio.run_coroutine_threadsafe(self.message_queue.put(msg_data), self.bot.loop)

    def send_file(self, file_path: str, content: str = "", channel_id: int = None) -> None:
        """
        Queue a file to be sent to Discord.
        
        Args:
            file_path: Path to the file.
            content: Optional message to send with the file.
            channel_id: Optional channel ID (uses default if not specified).
        """
        if not self.is_running:
            self._log("⚠️ Bot is not running", level=logging.WARNING)
            return
            
        if not os.path.exists(file_path):
            self._log(f"❌ File not found: {file_path}", level=logging.ERROR)
            return
            
        msg_data = {
            "channel_id": channel_id or self.config["default_channel_id"],
            "content": content,
            "file_path": file_path
        }
        asyncio.run_coroutine_threadsafe(self.message_queue.put(msg_data), self.bot.loop)

    # ----------------------------------------
    # Template Management
    # ----------------------------------------
    def send_template(self, template_name: str, context: dict, channel_id: int = None) -> None:
        """
        Render and send a templated message.
        
        Args:
            template_name: Template file name (without extension).
            context: Context variables for rendering.
            channel_id: Optional channel ID.
        """
        try:
            template = self.template_env.get_template(f"{template_name}.j2")
            content = template.render(context)
            self.send_message(content, channel_id)
            self._log(f"✅ Sent templated message using '{template_name}'")
        except Exception as e:
            self._log(f"❌ Template error: {e}", level=logging.ERROR)

    # ----------------------------------------
    # Status & Monitoring
    # ----------------------------------------
    def get_status(self) -> dict:
        """Get current bot status information."""
        status = {
            "is_running": self.is_running,
            "uptime": None,
            "connected_servers": 0,
            "active_channels": []
        }
        if self.is_running and self.start_time:
            status["uptime"] = (datetime.utcnow() - self.start_time).total_seconds()
            if self.bot.is_ready():
                status["connected_servers"] = len(self.bot.guilds)
                status["active_channels"] = [
                    {"id": c.id, "name": c.name} 
                    for g in self.bot.guilds 
                    for c in g.channels
                ]
        return status

    # ----------------------------------------
    # Utility Methods
    # ----------------------------------------
    def set_log_callback(self, callback) -> None:
        """Set an external logging callback."""
        self.log_callback = callback

    def _log(self, message: str, level: int = logging.INFO) -> None:
        """Internal logging with optional external callback."""
        logger.log(level, message)
        if self.log_callback:
            self.log_callback(message)


###########################################################################
# PyQt5 Discord Service Wrapper
###########################################################################

class DiscordService(QObject):
    """
    DiscordService provides a Qt-friendly interface to the UnifiedDiscordService.
    It exposes signals for logging and status changes and wraps the backend service methods.
    """
    
    log_message = pyqtSignal(str)
    status_changed = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.discord = None
        
    def launch_bot(self, token: str, channel_id: str) -> None:
        """
        Launch the Discord bot with the provided credentials.
        
        Args:
            token: Discord bot token.
            channel_id: Default channel ID.
        """
        if self.discord and self.discord.is_running:
            self.log_message.emit("Discord bot is already running.")
            return
            
        try:
            self.discord = UnifiedDiscordService(
                bot_token=token,
                default_channel_id=channel_id
            )
            # Set up logging callback to forward logs to Qt signals.
            self.discord.set_log_callback(self.log_message.emit)
            
            # Start the bot
            self.discord.run()
            
            self.status_changed.emit(True)
            self.log_message.emit("Discord bot launched successfully.")
            
        except Exception as e:
            self.log_message.emit(f"Error launching bot: {str(e)}")
            self.status_changed.emit(False)
            
    def stop_bot(self) -> None:
        """Stop the Discord bot if it is running."""
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
        Send a message via Discord.
        
        Args:
            channel_id: Target channel ID.
            message: Content of the message.
        
        Returns:
            True if the message was queued successfully.
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
        Send a file via Discord.
        
        Args:
            channel_id: Target channel ID.
            file_path: Path to the file.
            content: Optional accompanying message.
        
        Returns:
            True if the file was queued successfully.
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
        Send a templated message via Discord.
        
        Args:
            template_name: Name of the template.
            context: Context for rendering the template.
            channel_id: Optional target channel ID.
        
        Returns:
            True if the message was queued successfully.
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
        """Retrieve the current status of the Discord bot."""
        if not self.discord:
            return {"is_running": False, "message": "Bot not initialized"}
        return self.discord.get_status()
            
    def is_running(self) -> bool:
        """Check if the Discord bot is currently running."""
        return bool(self.discord and self.discord.is_running)