import discord
from discord.ext import commands
import asyncio
import logging
import threading
import json
import os
from typing import Union, Dict, Any, Optional, List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("UnifiedDiscordService")
logger.setLevel(logging.INFO)

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
                 default_channel_id: Union[int, str] = None,
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
        self.start_time: Optional[datetime] = None
        self._lock = threading.Lock()
        
        # Configuration
        self.config: Dict[str, Any] = {
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
        
        # Set up Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Register event handlers
        self._register_events()
        
        # External logging callback
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
            if message.author == self.bot.user:
                return
                
            # Handle auto-responses if configured
            if str(message.channel.id) in self.config["auto_responses"]:
                response = self.config["auto_responses"][str(message.channel.id)]
                await message.channel.send(response)

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
                json.dump(self.config, file=f, indent=4)
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
            # Stop the bot
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
            content: The message content to send
            channel_id: Optional channel ID (uses default if not specified)
        """
        if not self.is_running:
            self._log("⚠️ Bot is not running", level=logging.WARNING)
            return
            
        msg_data = {
            "channel_id": channel_id or self.config["default_channel_id"],
            "content": content
        }
        
        asyncio.run_coroutine_threadsafe(
            self.message_queue.put(msg_data), 
            self.bot.loop
        )

    def send_file(self, 
                  file_path: str, 
                  content: str = "", 
                  channel_id: int = None) -> None:
        """
        Queue a file to be sent to Discord.
        
        Args:
            file_path: Path to the file to send
            content: Optional message content to send with the file
            channel_id: Optional channel ID (uses default if not specified)
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
        
        asyncio.run_coroutine_threadsafe(
            self.message_queue.put(msg_data), 
            self.bot.loop
        )

    # ----------------------------------------
    # Template Management
    # ----------------------------------------
    
    def send_template(self, 
                     template_name: str, 
                     context: dict, 
                     channel_id: int = None) -> None:
        """
        Render and send a templated message.
        
        Args:
            template_name: Name of the template file (without extension)
            context: Dictionary of context variables for the template
            channel_id: Optional channel ID (uses default if not specified)
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
    
    def get_status(self) -> Dict[str, Any]:
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
        """Set external logging callback."""
        self.log_callback = callback

    def _log(self, message: str, level: int = logging.INFO) -> None:
        """Internal logging with optional callback."""
        logger.log(level, message)
        if self.log_callback:
            self.log_callback(message) 