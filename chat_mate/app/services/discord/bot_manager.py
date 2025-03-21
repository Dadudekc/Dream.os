import asyncio
from datetime import datetime
from typing import Optional
from app.schemas.discord_schema import BotConfig
from app.core.discord_bot import DreamscapeBot

class BotManager:
    def __init__(self):
        self.bot: Optional[DreamscapeBot] = None
        self.start_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def launch(self, config: BotConfig) -> None:
        async with self._lock:
            if self.bot is not None:
                await self.stop()
            
            self.bot = DreamscapeBot(
                token=config.token,
                channel_id=config.channel_id,
                prefix=config.prefix,
                allowed_roles=config.allowed_roles,
                auto_responses=config.auto_responses
            )
            
            self.start_time = datetime.utcnow()
            await self.bot.start()

    async def stop(self) -> None:
        async with self._lock:
            if self.bot is not None:
                await self.bot.close()
                self.bot = None
                self.start_time = None

    @property
    def is_running(self) -> bool:
        return self.bot is not None

    @property
    def uptime(self) -> Optional[float]:
        if self.start_time:
            return (datetime.utcnow() - self.start_time).total_seconds()
        return None 