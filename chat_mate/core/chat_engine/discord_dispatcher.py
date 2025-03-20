import discord
import logging
import asyncio
from discord.ext import commands

logger = logging.getLogger("DiscordDispatcher")
logger.setLevel(logging.INFO)

class DiscordDispatcher:
    """
    DiscordDispatcher - Manages communication to a Discord server.
    Sends updates on system events, memory updates, and AI output.
    """

    def __init__(self, token: str, default_channel_id: int):
        self.bot_token = token
        self.default_channel_id = default_channel_id

        # Main bot loop + initialization
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True

        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self._setup_events()

        self.ready = False

        logger.info("⚡ DiscordDispatcher initialized.")

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            self.ready = True
            logger.info(f"✅ Discord Bot connected as {self.bot.user}")

    # ---------------------------------------------------
    # PUBLIC SEND METHODS
    # ---------------------------------------------------

    def send_message(self, message: str, channel_id: int = None):
        """
        Public method to send message to Discord from external scripts.
        Runs in bot loop thread-safe.
        """
        channel_id = channel_id or self.default_channel_id

        if not self.ready:
            logger.warning("🚨 Discord bot not ready! Message not sent.")
            return

        asyncio.run_coroutine_threadsafe(self._send_message(channel_id, message), self.bot.loop)

    async def _send_message(self, channel_id: int, message: str):
        """
        Core send message coroutine.
        """
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"❌ Channel {channel_id} not found.")
                return
            await channel.send(message)
            logger.info(f"📤 Sent message to Discord channel {channel_id}")
        except Exception as e:
            logger.exception(f"❌ Failed to send Discord message: {e}")

    # ---------------------------------------------------
    # DISPATCHERS / UTILITY METHODS
    # ---------------------------------------------------

    def dispatch_memory_update(self, updates: dict):
        """
        Auto-format memory update notification.
        """
        if not updates:
            logger.info("⚠️ No memory updates to dispatch.")
            return

        update_message = "**✅ Memory Update**\n"
        for key, val in updates.items():
            update_message += f"**{key.capitalize()}**: {val}\n"

        self.send_message(update_message)

    def dispatch_dreamscape_episode(self, title: str, content: str):
        """
        Dispatches a Dreamscape episode to Discord.
        """
        message = f"🛡️ **New Dreamscape Episode Released!**\n**Title**: {title}\n\n{content}"
        self.send_message(message)

    def dispatch_feedback_loop(self, feedback_entry: dict):
        """
        Sends feedback learning loop insights.
        """
        score = feedback_entry.get("score", "N/A")
        hallucination = "❗ Yes" if feedback_entry.get("hallucination") else "✅ No"
        notes = feedback_entry.get("notes", "None")

        message = (
            f"🔄 **Feedback Loop Update**\n"
            f"Prompt: {feedback_entry.get('prompt_name', 'Unknown')}\n"
            f"Score: {score}\n"
            f"Hallucination: {hallucination}\n"
            f"Notes: {notes}"
        )
        self.send_message(message)

    # ---------------------------------------------------
    # RUN / STOP METHODS
    # ---------------------------------------------------

    def run_bot(self):
        """
        Launch the Discord bot.
        Blocking call—run in thread or separate process.
        """
        try:
            logger.info("🚀 Launching Discord bot...")
            self.bot.run(self.bot_token)
        except Exception as e:
            logger.exception(f"❌ Discord bot encountered an error: {e}")

    def shutdown(self):
        """
        Optional: Method to handle bot shutdown cleanly.
        """
        try:
            logger.info("🛑 Shutting down Discord bot...")
            loop = self.bot.loop
            loop.call_soon_threadsafe(loop.stop)
        except Exception as e:
            logger.exception(f"❌ Failed to shutdown Discord bot cleanly: {e}")

