import asyncio
from datetime import datetime
from typing import Optional, Dict
from app.schemas.discord_schema import BotConfig, BotStatus
from app.core.discord_bot import DreamscapeBot  # Your existing Discord bot

class DiscordService:
    def __init__(self):
        self.bot: Optional[DreamscapeBot] = None
        self.start_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def launch_bot(self, config: BotConfig) -> None:
        async with self._lock:
            if self.bot is not None:
                await self.stop_bot()
            
            self.bot = DreamscapeBot(
                token=config.token,
                channel_id=config.channel_id,
                prefix=config.prefix,
                allowed_roles=config.allowed_roles,
                auto_responses=config.auto_responses
            )
            
            self.start_time = datetime.utcnow()
            await self.bot.start()

    async def stop_bot(self) -> None:
        async with self._lock:
            if self.bot is not None:
                await self.bot.close()
                self.bot = None
                self.start_time = None

    async def get_status(self) -> BotStatus:
        if self.bot is None:
            return BotStatus(
                status="stopped",
                message="Bot is not running"
            )

        uptime = None
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return BotStatus(
            status="running" if self.bot.is_ready() else "connecting",
            message="Bot is operational" if self.bot.is_ready() else "Bot is connecting",
            uptime=uptime,
            last_heartbeat=self.bot.last_heartbeat,
            connected_servers=len(self.bot.guilds) if self.bot.is_ready() else 0,
            active_channels=list(self.bot.active_channels) if hasattr(self.bot, 'active_channels') else None
        )

# Create a singleton instance
discord_service = DiscordService() 